# Block Signal Bot - Deployment Guide

🤖 Real-time crypto scorecards powered by CoinGecko API + PostgreSQL

## 📋 Prerequisites

1. **Telegram Bot Token**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` and follow instructions
   - Save your bot token (looks like `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

2. **CoinGecko API Key** (Recommended)
   - Sign up at [CoinGecko](https://www.coingecko.com/en/api)
   - Get **Demo Plan** (FREE): 30 calls/min, 10K calls/month
   - Or use public API (no key needed, but less reliable)

3. **Render Account**
   - Sign up at [Render](https://render.com)
   - Free tier available for testing

## 🚀 Quick Deploy to Render

### Option 1: Blueprint Deploy (Easiest)

1. **Fork this repository** to your GitHub account

2. **Connect to Render**:
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New" → "Blueprint"
   - Connect your GitHub repo
   - Render will automatically detect `render.yaml`

3. **Set Environment Variables**:
   - `BOT_TOKEN`: Your Telegram bot token
   - `COINGECKO_API_KEY`: (Optional) Your CoinGecko API key
   - `ADMIN_USER_IDS`: Your Telegram user ID (get from @userinfobot)
   
4. **Deploy**: Click "Apply" and wait ~2-3 minutes

### Option 2: Manual Setup

#### Step 1: Create PostgreSQL Database

1. Go to Render Dashboard → "New" → "PostgreSQL"
2. Settings:
   - Name: `block-signal-db`
   - Plan: **Starter ($7/mo)** or Free (limited)
   - Region: Choose closest to you
3. Click "Create Database"
4. Copy the **Internal Database URL** (starts with `postgresql://`)

#### Step 2: Deploy Bot Service

1. Go to Render Dashboard → "New" → "Background Worker"
2. Connect your GitHub repo
3. Settings:
   - Name: `block-signal-bot`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`
   - Plan: **Starter** or **Free**

4. **Add Environment Variables**:
   ```
   BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   DATABASE_URL=postgresql://user:pass@host/db
   COINGECKO_API_KEY=CG-your-api-key (optional)
   RATE_LIMIT_SECONDS=10
   CACHE_TTL_MINUTES=30
   ADMIN_USER_IDS=123456789
   ```

5. Click "Create Background Worker"

## 🧪 Local Testing

```bash
# 1. Clone repository
git clone <your-repo>
cd block-signal-bot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up local PostgreSQL (or use Render's database)
# macOS: brew install postgresql
# Ubuntu: sudo apt install postgresql

# 4. Create .env file
cp .env.example .env
# Edit .env with your credentials

# 5. Run bot
python bot.py
```

## 📊 Features

✅ **Real-time Market Data**
- Live prices, market cap, volume from CoinGecko
- 24h, 7d, 30d price changes
- Market cap rankings

✅ **Intelligent Scoring System**
- Adoption & Partnerships (market rank, social following)
- On-Chain Activity (volume/mcap ratio)
- Decentralization (network maturity)
- Governance (GitHub activity, community)
- Market Positioning (rankings, social metrics)
- Token Economics (supply analysis)

✅ **Performance Optimizations**
- PostgreSQL caching (30-min TTL)
- Rate limiting (10s per user)
- Automatic cleanup tasks

✅ **Admin Features**
- `/stats` - Bot usage statistics
- `/trending` - Most requested coins
- User analytics tracking

## 💬 Bot Commands

### User Commands
- `/start` - Welcome message
- `/score BTC` - Get Bitcoin scorecard
- `/trending` - See popular coins
- Just type: `ETH`, `SOL`, etc.

### Admin Commands
- `/stats` - Detailed bot statistics

## 🔧 Configuration

Edit environment variables in Render dashboard:

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | Required | Telegram bot token |
| `DATABASE_URL` | Required | PostgreSQL connection string |
| `COINGECKO_API_KEY` | Optional | API key for higher rate limits |
| `RATE_LIMIT_SECONDS` | 10 | Cooldown between requests |
| `CACHE_TTL_MINUTES` | 30 | How long to cache scorecards |
| `ADMIN_USER_IDS` | Empty | Comma-separated admin IDs |

## 📈 CoinGecko API Limits

| Plan | Calls/Min | Calls/Month | Cost |
|------|-----------|-------------|------|
| Public | 5-15 | Unlimited | Free |
| Demo | 30 | 10,000 | Free |
| Analyst | 500 | 500,000 | $129/mo |

**Recommendation**: Start with **Demo plan** (free signup required)

## 🐛 Troubleshooting

### Bot not responding
1. Check logs in Render dashboard
2. Verify `BOT_TOKEN` is correct
3. Ensure database is running

### API rate limit errors
1. Sign up for CoinGecko Demo API key
2. Increase `CACHE_TTL_MINUTES` to 60
3. Check your API usage on CoinGecko dashboard

### Database connection errors
1. Verify `DATABASE_URL` is set correctly
2. Check if database service is running
3. Try restarting the bot service

## 🔐 Security Notes

- Never commit `.env` file or expose tokens
- Use Render's environment variables (encrypted)
- Regularly rotate API keys
- Keep `ADMIN_USER_IDS` private

## 📊 Monitoring

**View Logs**:
- Render Dashboard → Your Service → "Logs" tab
- Watch for errors, API calls, cache hits

**Database Stats**:
- Use `/stats` command (admin only)
- Check PostgreSQL dashboard in Render

## 🚀 Scaling

**If bot gets popular:**

1. **Upgrade CoinGecko Plan** ($129/mo for 500 calls/min)
2. **Upgrade Database** to higher tier
3. **Add Redis** for faster caching
4. **Enable Auto-scaling** in Render

## 💰 Cost Estimate

**Minimum Setup (Testing)**:
- Render Free Tier: $0
- PostgreSQL Free: $0 (limited)
- CoinGecko Demo: $0
- **Total: $0/month**

**Recommended Production**:
- Render Starter Worker: $7/mo
- PostgreSQL Starter: $7/mo
- CoinGecko Demo: $0
- **Total: $14/month**

## 📝 Project Structure

```
block-signal-bot/
├── bot.py              # Main application (Parts 1 & 2 combined)
├── requirements.txt    # Python dependencies
├── Dockerfile         # Optional Docker config
├── render.yaml        # Render blueprint
├── .env.example       # Environment template
├── README.md          # This file
└── .gitignore         # Ignore sensitive files
```

## 🤝 Contributing

Found a bug or have a feature request? Open an issue!

## 📜 License

MIT License - feel free to modify and use commercially

## 🆘 Support

Need help? Contact me or check:
- [Render Docs](https://render.com/docs)
- [python-telegram-bot Docs](https://docs.python-telegram-bot.org)
- [CoinGecko API Docs](https://www.coingecko.com/en/api/documentation)
