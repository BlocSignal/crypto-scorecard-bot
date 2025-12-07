#!/usr/bin/env python3
"""
Block_Signal_Bot — Production Version
Real-time crypto scorecards with CoinGecko API + PostgreSQL
Deploy to Render with persistent data

Author: Block Signal Team
License: MIT
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from functools import wraps
import asyncio
import os
import logging
import json

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

#from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, func
#from sqlalchemy.ext.declarative import declarative_base
#from sqlalchemy.orm import sessionmaker, Session
#from sqlalchemy.pool import QueuePool

#import aiohttp

# ================= CONFIGURATION =================
@dataclass
class BotConfig:
    """Centralized bot configuration"""
    bot_token: str
    coingecko_api_key: Optional[str]
    database_url: str
    rate_limit_seconds: int = 10
    max_ticker_length: int = 15
    cache_ttl_minutes: int = 30
    max_sources_display: int = 5
    coingecko_timeout: int = 10
    admin_user_ids: List[int] = field(default_factory=list)
    
    @classmethod
    def from_env(cls) -> BotConfig:
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise ValueError("BOT_TOKEN environment variable required")
        
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable required")
        
        # Fix Heroku/Render postgres:// -> postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
        admin_ids = [int(uid.strip()) for uid in admin_ids_str.split(",") if uid.strip().isdigit()]
        
        return cls(
            bot_token=bot_token,
            coingecko_api_key=os.getenv("COINGECKO_API_KEY"),
            database_url=database_url,
            rate_limit_seconds=int(os.getenv("RATE_LIMIT_SECONDS", "10")),
            cache_ttl_minutes=int(os.getenv("CACHE_TTL_MINUTES", "30")),
            admin_user_ids=admin_ids
        )

# ================= LOGGING =================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================= DATABASE MODELS =================
Base = declarative_base()

class ScorecardRecord(Base):
    """Stores generated scorecards"""
    __tablename__ = 'scorecards'
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(15), nullable=False, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    current_price_usd = Column(Float)
    market_cap_usd = Column(Float)
    volume_24h_usd = Column(Float)
    price_change_24h = Column(Float)
    price_change_7d = Column(Float)
    price_change_30d = Column(Float)
    scores_json = Column(Text, nullable=False)
    total_score = Column(Integer, nullable=False)
    interpretation = Column(String(100))
    data_source = Column(String(50), default='coingecko')

class UserRequest(Base):
    """Track user requests"""
    __tablename__ = 'user_requests'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(100))
    ticker = Column(String(15), nullable=False, index=True)
    requested_at = Column(DateTime, default=datetime.utcnow, index=True)
    served_from_cache = Column(Boolean, default=False)

# ================= DATABASE MANAGER =================
class DatabaseManager:
    """Handles all database operations"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info("✓ Database initialized")
    
    def get_session(self) -> Session:
        return self.SessionLocal()
    
    def save_scorecard(self, scorecard: 'CryptoScorecard', market_data: Dict[str, Any]) -> None:
        session = self.get_session()
        try:
            record = ScorecardRecord(
                ticker=scorecard.ticker,
                generated_at=scorecard.generated_at,
                current_price_usd=market_data.get('current_price'),
                market_cap_usd=market_data.get('market_cap'),
                volume_24h_usd=market_data.get('volume_24h'),
                price_change_24h=market_data.get('price_change_24h'),
                price_change_7d=market_data.get('price_change_7d'),
                price_change_30d=market_data.get('price_change_30d'),
                scores_json=json.dumps({
                    cat: asdict(detail) for cat, detail in scorecard._scores.items()
                }),
                total_score=scorecard.total_score,
                interpretation=scorecard.interpretation()
            )
            session.add(record)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving scorecard: {e}")
        finally:
            session.close()
    
    def get_cached_scorecard(self, ticker: str, ttl_minutes: int) -> Optional[Tuple['CryptoScorecard', Dict]]:
        session = self.get_session()
        try:
            cutoff = datetime.utcnow() - timedelta(minutes=ttl_minutes)
            record = session.query(ScorecardRecord).filter(
                ScorecardRecord.ticker == ticker.upper(),
                ScorecardRecord.generated_at > cutoff
            ).order_by(ScorecardRecord.generated_at.desc()).first()
            
            if record:
                scorecard = CryptoScorecard(ticker=record.ticker)
                scorecard.generated_at = record.generated_at
                
                scores_data = json.loads(record.scores_json)
                for category, detail_dict in scores_data.items():
                    scorecard.add_score(
                        category,
                        detail_dict['score'],
                        detail_dict['reasoning'],
                        detail_dict.get('sources', [])
                    )
                
                market_data = {
                    'name': record.ticker,
                    'current_price': record.current_price_usd,
                    'market_cap': record.market_cap_usd,
                    'volume_24h': record.volume_24h_usd,
                    'price_change_24h': record.price_change_24h,
                    'price_change_7d': record.price_change_7d,
                    'price_change_30d': record.price_change_30d,
                    'market_cap_rank': None
                }
                
                return scorecard, market_data
        except Exception as e:
            logger.error(f"Error retrieving cache: {e}")
        finally:
            session.close()
        return None
    
    def log_user_request(self, user_id: int, username: Optional[str], ticker: str, from_cache: bool):
        session = self.get_session()
        try:
            request = UserRequest(
                user_id=user_id,
                username=username,
                ticker=ticker.upper(),
                served_from_cache=from_cache
            )
            session.add(request)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging request: {e}")
        finally:
            session.close()
    
    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        session = self.get_session()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            total = session.query(UserRequest).filter(UserRequest.requested_at > cutoff).count()
            unique_users = session.query(UserRequest.user_id).filter(UserRequest.requested_at > cutoff).distinct().count()
            unique_tickers = session.query(UserRequest.ticker).filter(UserRequest.requested_at > cutoff).distinct().count()
            cache_hits = session.query(UserRequest).filter(
                UserRequest.requested_at > cutoff,
                UserRequest.served_from_cache == True
            ).count()
            
            top_tickers = session.query(
                UserRequest.ticker,
                func.count(UserRequest.ticker).label('count')
            ).filter(
                UserRequest.requested_at > cutoff
            ).group_by(UserRequest.ticker).order_by(
                func.count(UserRequest.ticker).desc()
            ).limit(10).all()
            
            return {
                'total_requests': total,
                'unique_users': unique_users,
                'unique_tickers': unique_tickers,
                'cache_hit_rate': (cache_hits / total * 100) if total > 0 else 0,
                'top_tickers': [(t[0], t[1]) for t in top_tickers],
                'days': days
            }
        finally:
            session.close()

# ================= RATE LIMITER =================
class RateLimiter:
    def __init__(self, seconds: int = 10):
        self.seconds = seconds
        self.users: Dict[int, datetime] = {}
    
    def is_allowed(self, user_id: int) -> Tuple[bool, Optional[int]]:
        now = datetime.utcnow()
        if user_id in self.users:
            elapsed = (now - self.users[user_id]).total_seconds()
            if elapsed < self.seconds:
                return False, int(self.seconds - elapsed)
        self.users[user_id] = now
        return True, None
    
    def cleanup(self):
        cutoff = datetime.utcnow() - timedelta(seconds=self.seconds * 2)
        self.users = {uid: ts for uid, ts in self.users.items() if ts > cutoff}

# ================= COINGECKO API =================
class CoinGeckoClient:
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        self.api_key = api_key
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                headers["x-cg-demo-api-key"] = self.api_key
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_coin_data(self, coin_id: str) -> Optional[Dict[str, Any]]:
        session = await self._get_session()
        try:
            url = f"{self.BASE_URL}/coins/{coin_id}"
            params = {
                'localization': 'false',
                'tickers': 'false',
                'community_data': 'true',
                'developer_data': 'true',
                'sparkline': 'false'
            }
            
            async with session.get(url, params=params, timeout=self.timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_coin_data(data)
                elif response.status == 429:
                    logger.warning("CoinGecko rate limit hit")
                else:
                    logger.error(f"CoinGecko error: {response.status}")
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
        return None
    
    def _parse_coin_data(self, data: Dict) -> Dict[str, Any]:
        market_data = data.get('market_data', {})
        return {
            'id': data.get('id'),
            'symbol': data.get('symbol', '').upper(),
            'name': data.get('name'),
            'current_price': market_data.get('current_price', {}).get('usd'),
            'market_cap': market_data.get('market_cap', {}).get('usd'),
            'market_cap_rank': market_data.get('market_cap_rank'),
            'volume_24h': market_data.get('total_volume', {}).get('usd'),
            'price_change_24h': market_data.get('price_change_percentage_24h'),
            'price_change_7d': market_data.get('price_change_percentage_7d'),
            'price_change_30d': market_data.get('price_change_percentage_30d'),
            'circulating_supply': market_data.get('circulating_supply'),
            'total_supply': market_data.get('total_supply'),
            'max_supply': market_data.get('max_supply'),
            'github_stars': data.get('developer_data', {}).get('stars'),
            'twitter_followers': data.get('community_data', {}).get('twitter_followers'),
            'reddit_subscribers': data.get('community_data', {}).get('reddit_subscribers'),
        }
    
    async def search_coin(self, query: str) -> Optional[str]:
        session = await self._get_session()
        try:
            url = f"{self.BASE_URL}/search"
            async with session.get(url, params={'query': query}, timeout=self.timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    coins = data.get('coins', [])
                    if coins:
                        return coins[0].get('id')
        except Exception as e:
            logger.error(f"Error searching: {e}")
        return None

# ================= SCORECARD CLASSES =================
@dataclass
class ScoreDetail:
    score: int
    reasoning: str
    sources: List[str] = field(default_factory=list)
    evaluated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def __post_init__(self):
        if not 0 <= self.score <= 5:
            raise ValueError(f"Score must be 0-5, got {self.score}")

@dataclass
class CryptoScorecard:
    ticker: str
    max_score_per_category: int = 5
    categories: List[str] = field(default_factory=lambda: [
        "Adoption & Partnerships",
        "On-Chain Activity",
        "Validator / Miner Decentralization",
        "Governance & Transparency",
        "Narrative & Market Positioning",
        "Token Utility & Economics",
    ])
    _scores: Dict[str, ScoreDetail] = field(default_factory=dict, init=False)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def add_score(self, category: str, score: int, reasoning: str, sources: Optional[List[str]] = None):
        if category in self.categories:
            try:
                self._scores[category] = ScoreDetail(score, reasoning.strip(), sources or [])
            except ValueError as e:
                logger.error(f"Invalid score: {e}")

    @property
    def total_score(self) -> int:
        return sum(d.score for d in self._scores.values())

    @property
    def max_possible_score(self) -> int:
        return len(self.categories) * self.max_score_per_category

    @property
    def score_percentage(self) -> float:
        return self.total_score / self.max_possible_score if self._scores else 0.0

    def interpretation(self) -> str:
        ratio = self.score_percentage
        if ratio >= 0.83:
            return "🟢 Serious long-term player"
        elif ratio >= 0.67:
            return "🟡 Promising with solid fundamentals"
        elif ratio >= 0.5:
            return "🟡 Promising but risky"
        elif ratio >= 0.33:
            return "🟠 Speculative - high risk"
        return "🔴 Weak fundamentals"

    def report(self, market_data: Dict[str, Any]) -> str:
        age = (datetime.utcnow() - self.generated_at).total_seconds()
        cache_status = "🔴 Cached" if age > 60 else "🟢 Fresh"
        
        lines = [
            f"📊 *{market_data.get('name', self.ticker)} ({self.ticker})*",
            f"{cache_status} • {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC\n"
        ]
        
        # Market data
        if market_data.get('current_price'):
            price = market_data['current_price']
            change = market_data.get('price_change_24h', 0)
            emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
            
            lines.append("*Market Data:*")
            lines.append(f"Price: ${price:,.2f} {emoji} {change:+.2f}%")
            
            if market_data.get('market_cap'):
                mcap = market_data['market_cap']
                rank = market_data.get('market_cap_rank', 'N/A')
                if mcap >= 1e9:
                    lines.append(f"Market Cap: ${mcap/1e9:.2f}B (#{rank})")
                else:
                    lines.append(f"Market Cap: ${mcap/1e6:.2f}M (#{rank})")
            
            if market_data.get('volume_24h'):
                vol = market_data['volume_24h']
                lines.append(f"24h Volume: ${vol/1e9:.2f}B" if vol >= 1e9 else f"24h Volume: ${vol/1e6:.2f}M")
            
            lines.append("")
        
        # Scores
        lines.append("*Fundamental Scores:*")
        for cat in self.categories:
            if cat in self._scores:
                d = self._scores[cat]
                emoji = "🟢" if d.score >= 4 else "🟡" if d.score >= 3 else "🔴"
                lines.append(f"{emoji} *{cat}*: {d.score}/5")
                lines.append(f"   _{d.reasoning}_")
        
        lines.extend([
            "\n━━━━━━━━━━━━━━━━━━━",
            f"*Total*: {self.total_score}/{self.max_possible_score} ({self.score_percentage:.0%})",
            f"*Verdict*: {self.interpretation()}",
            "\n⚡ @Block\\_Signal\\_Bot"
        ])
        
        return "\n".join(lines)

# ================= SCORING LOGIC =================
def score_adoption(data: Dict) -> Tuple[int, str]:
    rank = data.get('market_cap_rank', 999)
    twitter = data.get('twitter_followers', 0)
    name = data.get('name', data['symbol'])
    
    if rank <= 10:
        return 5, f"{name} is a top-10 crypto with dominant market position."
    elif rank <= 30:
        return 4, f"{name} ranks #{rank} with strong institutional presence."
    elif rank <= 100:
        return 3, f"{name} is mid-cap (#{rank}) with growing adoption."
    elif twitter > 100000:
        return 3, f"{name} has {twitter:,} Twitter followers showing community support."
    return 2, f"{name} is building adoption from rank #{rank}."

def score_activity(data: Dict) -> Tuple[int, str]:
    mcap = data.get('market_cap', 0)
    vol = data.get('volume_24h', 0)
    ratio = (vol / mcap * 100) if mcap > 0 else 0
    
    if ratio > 30:
        return 5, f"Exceptional liquidity with {ratio:.1f}% daily volume/mcap."
    elif ratio > 15:
        return 4, f"Strong trading activity ({ratio:.1f}% volume/mcap)."
    elif ratio > 5:
        return 3, f"Healthy liquidity at {ratio:.1f}%."
    return 2, f"Low volume ({ratio:.1f}%) - liquidity concerns."

def score_governance(data: Dict) -> Tuple[int, str]:
    stars = data.get('github_stars', 0)
    reddit = data.get('reddit_subscribers', 0)
    
    if stars > 10000:
        return 5, f"Highly active development ({stars:,} GitHub stars)."
    elif stars > 3000:
        return 4, f"Strong developer community ({stars:,} stars)."
    elif stars > 500 or reddit > 50000:
        return 3, f"Active community with {reddit:,} Reddit members."
    return 2, "Limited public development metrics."

def score_narrative(data: Dict) -> Tuple[int, str]:
    rank = data.get('market_cap_rank', 999)
    twitter = data.get('twitter_followers', 0)
    name = data.get('name', data['symbol'])
    
    score = 0
    if rank <= 10:
        score = 5
    elif rank <= 30:
        score = 4
    elif rank <= 100:
        score = 3
    else:
        score = 2
    
    if twitter > 500000:
        score = min(5, score + 1)
    
    msgs = {
        5: f"{name} dominates sector mindshare (#{rank}, {twitter:,} followers).",
        4: f"{name} has strong market position and narrative.",
        3: f"{name} maintains solid presence in its sector.",
        2: f"{name} needs stronger narrative to compete."
    }
    return score, msgs.get(score, msgs[2])

def score_utility(data: Dict) -> Tuple[int, str]:
    max_supply = data.get('max_supply')
    circ = data.get('circulating_supply', 0)
    
    if max_supply and max_supply > 0:
        pct = (circ / max_supply * 100)
        return 4, f"Capped supply at {max_supply:,.0f} ({pct:.1f}% circulating)."
    return 2, "Uncapped supply - monitor inflation."

async def generate_scorecard_from_api(ticker: str, client: CoinGeckoClient) -> Tuple[Optional[CryptoScorecard], Optional[Dict]]:
    coin_id = await client.search_coin(ticker)
    if not coin_id:
        return None, None
    
    data = await client.get_coin_data(coin_id)
    if not data:
        return None, None
    
    card = CryptoScorecard(ticker=data['symbol'])
    
    score, reason = score_adoption(data)
    card.add_score("Adoption & Partnerships", score, reason, ["CoinGecko"])
    
    score, reason = score_activity(data)
    card.add_score("On-Chain Activity", score, reason, ["Volume Analysis"])
    
    card.add_score("Validator / Miner Decentralization", 3, 
                   f"Network maturity analysis based on market position.", ["Network Data"])
    
    score, reason = score_governance(data)
    card.add_score("Governance & Transparency", score, reason, ["GitHub", "Reddit"])
    
    score, reason = score_narrative(data)
    card.add_score("Narrative & Market Positioning", score, reason, ["Social Metrics"])
    
    score, reason = score_utility(data)
    card.add_score("Token Utility & Economics", score, reason, ["Supply Analysis"])
    
    return card, data

# ================= TELEGRAM HANDLERS =================
def rate_limited(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        limiter: RateLimiter = context.bot_data["rate_limiter"]
        allowed, wait = limiter.is_allowed(update.effective_user.id)
        if not allowed:
            await update.message.reply_text(f"⏳ Wait {wait}s before next request")
            return
        return await func(update, context)
    return wrapper

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Block Signal Bot*\n\n"
        "*Commands:*\n"
        "• `/score BTC` — Get scorecard\n"
        "• Just type: `ETH`, `SOL`, etc.\n"
        "• `/trending` — Popular coins\n\n"
        "✨ Real-time CoinGecko data\n"
        "📅 December 2025",
        parse_mode='Markdown'
    )

@rate_limited
async def score_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/score <ticker>`", parse_mode='Markdown')
        return
    await process_ticker_request(update, context.args[0].strip().upper(), context)

async def trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db: DatabaseManager = context.bot_data["db"]
    stats = db.get_stats(7)
    
    if not stats['top_tickers']:
        await update.message.reply_text("📊 No data yet!")
        return
    
    lines = ["📈 *Top Coins (7 days)*\n"]
    for i, (ticker, count) in enumerate(stats['top_tickers'], 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        lines.append(f"{emoji} `{ticker}` — {count}x")
    
    lines.append(f"\n📊 {stats['total_requests']} total requests")
    await update.message.reply_text("\n".join(lines), parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config: BotConfig = context.bot_data["config"]
    if update.effective_user.id not in config.admin_user_ids:
        await update.message.reply_text("⛔ Admin only")
        return
    
    db: DatabaseManager = context.bot_data["db"]
    stats = db.get_stats(7)
    
    lines = [
        "📊 *Bot Stats (7d)*\n",
        f"👥 Users: {stats['unique_users']}",
        f"📝 Requests: {stats['total_requests']}",
        f"💾 Cache: {stats['cache_hit_rate']:.1f}%"
    ]
    await update.message.reply_text("\n".join(lines), parse_mode='Markdown')

@rate_limited
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().upper()
    config: BotConfig = context.bot_data["config"]
    if 2 <= len(text) <= config.max_ticker_length and text.isalnum():
        await process_ticker_request(update, text, context)

async def process_ticker_request(update: Update, ticker: str, context: ContextTypes.DEFAULT_TYPE):
    config: BotConfig = context.bot_data["config"]
    db: DatabaseManager = context.bot_data["db"]
    cg: CoinGeckoClient = context.bot_data["coingecko"]
    
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    if len(ticker) > config.max_ticker_length or not ticker.isalnum():
        await update.message.reply_text("❌ Invalid ticker")
        return
    
    # Check cache
    cached = db.get_cached_scorecard(ticker, config.cache_ttl_minutes)
    if cached:
        card, data = cached
        db.log_user_request(user_id, username, ticker, True)
        await update.message.reply_text(card.report(data), parse_mode='Markdown', disable_web_page_preview=True)
        return
    
    # Generate new
    msg = await update.message.reply_text(f"🔍 Analyzing *{ticker}*...", parse_mode='Markdown')
    
    try:
        card, data = await generate_scorecard_from_api(ticker, cg)
        
        if not card or not data:
            await msg.edit_text(f"❌ Could not find `{ticker}`\n\nTry: BTC, ETH, SOL", parse_mode='Markdown')
            return
        
        db.save_scorecard(card, data)
        db.log_user_request(user_id, username, ticker, False)
        
        await msg.edit_text(card.report(data), parse_mode='Markdown', disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await msg.edit_text("❌ Error. Try again later.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}", exc_info=context.error)

async def periodic_cleanup(context: ContextTypes.DEFAULT_TYPE):
    context.bot_data["rate_limiter"].cleanup()

# ================= MAIN =================
def main():
    config = BotConfig.from_env()
    db = DatabaseManager(config.database_url)
    cg = CoinGeckoClient(config.coingecko_api_key)
    
    app = Application.builder().token(config.bot_token).build()
    
    app.bot_data["config"] = config
    app.bot_data["db"] = db
    app.bot_data["coingecko"] = cg
    app.bot_data["rate_limiter"] = RateLimiter(config.rate_limit_seconds)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("score", score_command))
    app.add_handler(CommandHandler("trending", trending_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)
    
    app.job_queue.run_repeating(periodic_cleanup, interval=600, first=600)
    
    logger.info("🚀 Block_Signal_Bot Production")
    logger.info(f"📊 Database: ✓")
    logger.info(f"🔑 CoinGecko: {'Demo API' if config.coingecko_api_key else 'Public'}")
    logger.info(f"⏱️  Rate limit: {config.rate_limit_seconds}s")
    logger.info(f"💾 Cache TTL: {config.cache_ttl_minutes}min")
    
    try:
        app.run_polling(drop_pending_updates=True)
    finally:
        import asyncio
        asyncio.run(cg.close())

if __name__ == "__main__":
    main()
