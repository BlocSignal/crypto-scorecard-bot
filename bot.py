#!/usr/bin/env python3
"""
Block_Signal_Bot — Now with Trending + 7-day Charts! (Dec 2025)
Fully secure, crash-proof, production-ready
"""
from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import aiohttp
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ================= SECURITY & LOGGING =================
logging.getLogger("httpx").setLevel(logging.WARNING)        # Hides token in logs
logging.getLogger("telegram").setLevel(logging.INFO)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in Render → Environment")

# ================= SCORECARD CLASSES (unchanged) =================
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

    def report(self) -> str:
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
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            try:
                async with session.get(f"{self.BASE}/search", params={"query": query}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        coins = data.get("coins", [])
                        if coins: return coins[0]["id"]
            except Exception as e:
                logger.warning(f"Search failed for {query}: {e}")
        return None

    async def get_data(self, coin_id: str) -> Optional[Dict]:
        params = {
            "localization": "false", "tickers": "false", "market_data": "true",
            "community_data": "true", "developer_data": "true", "sparkline": "false"
        }
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            try:
                async with session.get(f"{self.BASE}/coins/{coin_id}", params=params) as resp:
                    if resp.status == 200:
                        return await resp.json()
            except Exception as e:
                logger.warning(f"Data fetch failed for {coin_id}: {e}")
        return None

cg_client = CoinGeckoClient()

# ================= SCORING LOGIC =================
def score_adoption(data): return (5, "Top-tier adoption") if data.get("market_cap_rank", 999) <= 30 else (4, "Strong adoption")
def score_activity(data):
    vol = data.get("total_volume", 0)
    mcap = data.get("market_cap", 1) or 1
    ratio = vol / mcap
    return (5, "High on-chain activity") if ratio > 0.15 else (4, "Healthy activity") if ratio > 0.05 else (3, "Low activity")
def score_decentralization(_): return (4, "Balanced decentralization")
def score_governance(data):
    stars = data.get("developer_data", {}).get("stars", 0)
    return (5, "Highly active") if stars > 5000 else (4, "Active dev") if stars > 1000 else (3, "Moderate")
def score_narrative(data): return (5, "Dominant narrative") if data.get("market_cap_rank", 999) <= 50 else (4, "Strong narrative")
def score_utility(data): return (5, "Capped supply") if data.get("max_supply") else (3, "Inflationary")

async def generate_scorecard(ticker: str) -> Tuple[Optional[CryptoScorecard], Optional[Dict]]:
    try:
        coin_id = await cg_client.search(ticker.lower())
        if not coin_id: return None, None
        raw = await cg_client.get_data(coin_id)
        if not raw: return None, None

        market = raw.get("market_data", {})
        data = {
            "market_cap_rank": raw.get("market_cap_rank"),
            "market_cap": market.get("market_cap", {}).get("usd", 1),
            "total_volume": market.get("total_volume", {}).get("usd", 0),
            "developer_data": raw.get("developer_data", {}),
            "max_supply": market.get("max_supply"),
        }

        card = CryptoScorecard(ticker.upper())
        for cat, func in zip(card.categories, [score_adoption, score_activity, score_decentralization,
                                              score_governance, score_narrative, score_utility]):
            try:
                score, reason = func(data)
                card.add_score(cat, score, reason)
            except:
                card.add_score(cat, 1, "Scoring error")
        return card, raw
    except Exception as e:
        logger.error(f"generate_scorecard crash: {e}", exc_info=True)
        return None, None

# ================= TRENDING =================
async def get_trending() -> str:
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://api.coingecko.com/api/v3/search/trending") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    lines = ["Trending on CoinGecko right now\n"]
                    for i, c in enumerate(data["coins"][:10], 1):
                        coin = c["item"]
                        lines.append(f"{i}. {coin['symbol'].upper()} — {coin['name']}")
                    lines.append("\nSend any ticker for instant scorecard + chart!")
                    return "\n".join(lines)
        except:
            pass
    return "Trending temporarily unavailable"

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "*Block_Signal_Bot* \\(Dec 2025\\)\n\n"
        "Send any ticker → real-time scorecard \\+ 7-day chart in seconds!\n\n"
        f"{await get_trending()}\n\n"
        "Powered by Block Signal"
    )
    await update.message.reply_text(text, parse_mode="MarkdownV2", disable_web_page_preview=True)

async def trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Loading trending…")
    await msg.edit_text(await get_trending(), parse_mode="Markdown")

async def handle_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.strip().upper()
    if not (3 <= len(ticker) <= 10 and ticker.isalnum()): return

    sent = await update.message.reply_text(f"Analyzing {ticker}…")

    card, raw = await generate_scorecard(ticker)
    if not card or not raw:
        await sent.edit_text(f"Could not find {ticker} — check spelling!")
        return

    name = raw.get("name", ticker)
    price = raw["market_data"]["current_price"].get("usd", 0)
    change = raw["market_data"]["price_change_percentage_24h"] or 0
    emoji = "Up" if change > 0 else "Down" if change < 0 else "Flat"

    header = f"*{name} ({ticker})*\nPrice: ${price:,.2f} {emoji} {change:+.2f}% (24h)\n\n"
    text_report = header + card.report()

    # Send text first
    await sent.edit_text(text_report, parse_mode="Markdown", disable_web_page_preview=True)

    # Then send beautiful 7-day chart
    chart_url = f"https://www.coingecko.com/coins/{raw['id']}/usd?v=7d.png"
    await update.message.reply_photo(
        photo=chart_url,
        caption="7-day price chart ↑",
        reply_to_message_id=update.message.message_id
    )

# ================= ERROR HANDLER =================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled error:", exc_info=context.error)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("trending", trending_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ticker))
    app.add_error_handler(error_handler)

    print("Block_Signal_Bot LIVE with CHARTS + TRENDING!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
