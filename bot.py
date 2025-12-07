#!/usr/bin/env python3
"""
Block_Signal_Bot — Lightweight MVP (No DB Required)
Real-time crypto scorecards • Dec 2025
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import os
import logging
import aiohttp
import asyncio

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Set BOT_TOKEN in Render → Environment")

# ================= SCORECARD =================
@dataclass
class ScoreDetail:
    score: int
    reasoning: str
    sources: List[str] = field(default_factory=list)

@dataclass
class CryptoScorecard:
    ticker: str
    _scores: Dict[str, ScoreDetail] = field(default_factory=dict, init=False)
    categories: List[str] = field(default_factory=lambda: [
        "Adoption & Partnerships", "On-Chain Activity", "Validator / Miner Decentralization",
        "Governance & Transparency", "Narrative & Market Positioning", "Token Utility & Economics"
    ])

    def add_score(self, category: str, score: int, reasoning: str, sources: Optional[List[str]] = None):
        if category in self.categories:
            self._scores[category] = ScoreDetail(score, reasoning, sources or [])

    @property
    def total_score(self) -> int:
        return sum(d.score for d in self._scores.values())

    def interpretation(self) -> str:
        ratio = self.total_score / (len(self.categories) * 5)
        if ratio >= 0.83: return "Serious long-term player"
        if ratio >= 0.5: return "Promising but risky"
        return "Probably hype / weak fundamentals"

    def report(self, market_data: Dict) -> str:
        lines = [f"*{self.ticker.upper()} Scorecard* • Dec 2025\n"]
        for cat in self.categories:
            if cat in self._scores:
                d = self._scores[cat]
                tag = "Excellent" if d.score == 5 else "Good" if d.score >= 4 else "Fair"
                lines += [f"**{cat}**", f"Score: {d.score}/5 {tag}", f"_{d.reasoning}_", ""]
        
        lines += [
            "---",
            f"**Total**: {self.total_score}/30 ({self.total_score/30:.1%})",
            f"**Verdict**: {self.interpretation()}",
            "\n@Block_Signal_Bot"
        ]
        return "\n".join(lines)

# ================= COINGECKO CLIENT =================
class CoinGeckoClient:
    BASE = "https://api.coingecko.com/api/v3"
    
    async def search(self, query: str) -> Optional[str]:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.BASE}/search", params={'query': query}) as r:
                    if r.status == 200:
                        data = await r.json()
                        return data['coins'][0]['id']
            except: pass
        return None

    async def get_data(self, coin_id: str) -> Optional[Dict]:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.BASE}/coins/{coin_id}", params={
                    'localization': 'false', 'tickers': 'false', 'market_data': 'true',
                    'community_data': 'true', 'developer_data': 'true'
                }) as r:
                    if r.status == 200:
                        return await r.json()
            except: pass
        return None

cg_client = CoinGeckoClient()

# ================= SCORING LOGIC (Same as yours) =================
def score_adoption(data): return (5, "Top-tier adoption") if data.get('market_cap_rank', 999) <= 30 else (4, "Strong adoption")
def score_activity(data): vol_mcap = data['market_data']['total_volume']['usd'] / data['market_data']['market_cap']['usd']; return (5, "High activity") if vol_mcap > 0.15 else (4, "Good activity")
def score_governance(data): stars = data.get('developer_data', {}).get('stars', 0); return (5, "Active dev") if stars > 5000 else (4, "Growing dev")
def score_narrative(data): return (5, "Dominant narrative") if data.get('market_cap_rank', 999) <= 50 else (4, "Strong narrative")
def score_utility(data): return (5, "Capped supply") if data['market_data'].get('max_supply') else (3, "Inflationary")

async def generate_scorecard(ticker: str) -> Tuple[Optional[CryptoScorecard], Optional[Dict]]:
    coin_id = await cg_client.search(ticker)
    if not coin_id: return None, None
    raw = await cg_client.get_data(coin_id)
    if not raw: return None, None

    market = raw['market_data']
    data = {
        'market_cap_rank': raw.get('market_cap_rank'),
        'market_cap': market['market_cap']['usd'],
        'total_volume': market['total_volume']['usd'],
        'developer_data': raw.get('developer_data', {}),
        'max_supply': market.get('max_supply')
    }

    card = CryptoScorecard(ticker.upper())
    funcs = [score_adoption, score_activity, lambda x: (4, "Balanced decentralization"), score_governance, score_narrative, score_utility]
    cats = card.categories
    for cat, func in zip(cats, funcs):
        score, reason = func(data)
        card.add_score(cat, score, reason)

    return card, raw

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Block_Signal_Bot\n\nSend any ticker → get real-time scorecard!\nPowered by Grok xAI • Dec 2025")

async def handle_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.strip().upper()
    if not (3 <= len(ticker) <= 10 and ticker.isalnum()): return

    msg = await update.message.reply_text(f"Analyzing {ticker}...")
    card, raw = await generate_scorecard(ticker)
    
    if not card:
        await msg.edit_text(f"Could not find {ticker}")
        return

    name = raw.get('name', ticker)
    price = raw['market_data']['current_price']['usd']
    change = raw['market_data']['price_change_percentage_24h']
    emoji = "Up" if change > 0 else "Down" if change < 0 else "Flat"
    
    header = f"*{name} ({ticker})*\nPrice: ${price:,.2f} {emoji} {change:+.2f}% (24h)\n"
    await msg.edit_text(header + card.report({}), parse_mode='Markdown', disable_web_page_preview=True)

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ticker))
    
    print("Block_Signal_Bot is LIVE! @Block_Signal_Bot")
    app.run_polling()

if __name__ == "__main__":
    main()
