# 🚀 Block Signal Bot - Deployment Checklist

## ✅ Pre-Deployment Steps

### 1. Get Telegram Bot Token
- [ ] Open Telegram and message [@BotFather](https://t.me/BotFather)
- [ ] Send `/newbot`
- [ ] Choose a name: `Block Signal Bot`
- [ ] Choose a username: `YourBlockSignalBot` (must end in 'bot')
- [ ] Copy and save your token: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
- [ ] Send `/setdescription` to add bot description
- [ ] Send `/setabouttext` to add "About" section

### 2. Get CoinGecko API Key (Recommended)
- [ ] Go to [CoinGecko API](https://www.coingecko.com/en/api)
- [ ] Click "Get Your API Key Now"
- [ ] Sign up for Demo plan (FREE)
- [ ] Verify your email
- [ ] Copy your API key: `CG-xxxxxxxxxxxxx`
- [ ] Note: You get 30 calls/min, 10,000 calls/month

### 3. Get Your Telegram User ID (For Admin Commands)
- [ ] Open Telegram and message [@userinfobot](https://t.me/userinfobot)
- [ ] Copy your user ID (e.g., `123456789`)

### 4. Prepare GitHub Repository
- [ ] Create new GitHub repository
- [ ] Name it: `block-signal-bot`
- [ ] Set to Public or Private
- [ ] Clone to your local machine:
  ```bash
  git clone https://github.com/yourusername/block-signal-bot.git
  cd block-signal-bot
  ```

### 5. Add Files to Repository
- [ ] Copy `bot.py` (complete file from artifacts)
- [ ] Copy `requirements.txt`
- [ ] Copy `render.yaml`
- [ ] Copy `.gitignore`
- [ ] Copy `README.md`
- [ ] Copy `.env.example`
- [ ] DO NOT add `.env` file with real credentials!

### 6. Push to GitHub
```bash
git add .
git commit -m "Initial commit - Block Signal Bot"
git push origin main
```

---

## 🔧 Render Deployment

### Step 1: Create Render Account
- [ ] Go to [render.com](https://render.com)
- [ ] Sign up with GitHub
- [ ] Authorize Render to access your repositories

### Step 2: Create PostgreSQL Database
- [ ] In Render Dashboard, click "New +" → "PostgreSQL"
- [ ] Settings:
  - **Name**: `block-signal-db`
  - **Database**: `blocksignal`
  - **User**: `blocksignal_user`
  - **Region**: Choose closest to you (Oregon, Frankfurt, Singapore, Ohio)
  - **Plan**: **Starter ($7/month)** or Free (90 days, then deleted)
- [ ] Click "Create Database"
- [ ] Wait 2-3 minutes for provisioning
- [ ] Copy the **Internal Database URL** (starts with `postgresql://`)

### Step 3: Deploy Bot Service

#### Option A: Blueprint Deploy (Recommended)
- [ ] In Render Dashboard, click "New +" → "Blueprint"
- [ ] Connect your GitHub repository
- [ ] Render detects `render.yaml` automatically
- [ ] Configure environment variables:
  - `BOT_TOKEN`: Your Telegram bot token
  - `COINGECKO_API_KEY`: Your CoinGecko key (or leave empty)
  - `ADMIN_USER_IDS`: Your Telegram user ID
- [ ] Click "Apply"
- [ ] Wait 3-5 minutes for deployment

#### Option B: Manual Deploy
- [ ] In Render Dashboard, click "New +" → "Background Worker"
- [ ] Connect your GitHub repository
- [ ] Settings:
  - **Name**: `block-signal-bot`
  - **Environment**: `Python 3`
  - **Build Command**: `pip install -r requirements.txt`
  - **Start Command**: `python bot.py`
  - **Plan**: Starter (Free tier available)
  
- [ ] Add Environment Variables (click "Environment" tab):
  ```
  BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
  DATABASE_URL=postgresql://user:pass@host:5432/db
  COINGECKO_API_KEY=CG-your-api-key
  RATE_LIMIT_SECONDS=10
  CACHE_TTL_MINUTES=30
  ADMIN_USER_IDS=123456789
  ```
  
- [ ] Click "Create Background Worker"

### Step 4: Monitor Deployment
- [ ] Go to your service → "Logs" tab
- [ ] Look for:
  ```
  🚀 Block_Signal_Bot Production
  📊 Database: ✓
  🔑 CoinGecko: Demo API
  ⏱️  Rate limit: 10s
  💾 Cache TTL: 30min
  ```
- [ ] If you see errors, check environment variables

---

## 🧪 Testing Your Bot

### Basic Tests
- [ ] Open Telegram and search for your bot username
- [ ] Send `/start` - should get welcome message
- [ ] Send `/score BTC` - should get Bitcoin scorecard
- [ ] Type `ETH` - should get Ethereum scorecard
- [ ] Send `/trending` - should show "No data yet"
- [ ] Wait 30 seconds and send another `/score` - should use cache

### Admin Tests (if configured)
- [ ] Send `/stats` - should show bot statistics

### Performance Tests
- [ ] Request same coin twice quickly - should hit rate limit
- [ ] Request 5 different coins - check logs for API calls
- [ ] Request same coin after 30+ minutes - should fetch fresh data

---

## 📊 Monitoring & Maintenance

### Daily Checks
- [ ] Check bot is responding in Telegram
- [ ] Review Render logs for errors
- [ ] Monitor database size (Render dashboard)

### Weekly Checks
- [ ] Review `/stats` command output
- [ ] Check CoinGecko API usage (coingecko.com dashboard)
- [ ] Review top requested coins with `/trending`

### Monthly Checks
- [ ] Review Render billing
- [ ] Check database storage usage
- [ ] Update dependencies if needed:
  ```bash
  pip install --upgrade python-telegram-bot
  ```

---

## 🐛 Troubleshooting

### Bot Not Responding
**Problem**: Bot doesn't reply in Telegram

**Solutions**:
- [ ] Check Render logs for errors
- [ ] Verify `BOT_TOKEN` is correct
- [ ] Restart the service in Render dashboard
- [ ] Check if service is running (Render dashboard shows status)

### Database Connection Errors
**Problem**: `sqlalchemy.exc.OperationalError`

**Solutions**:
- [ ] Verify database is running in Render
- [ ] Check `DATABASE_URL` is correct
- [ ] Ensure URL uses `postgresql://` not `postgres://`
- [ ] Try restarting both database and bot service

### CoinGecko Rate Limits
**Problem**: `CoinGecko rate limit hit` in logs

**Solutions**:
- [ ] Add `COINGECKO_API_KEY` if using public API
- [ ] Increase `CACHE_TTL_MINUTES` to 60
- [ ] Check your API usage on CoinGecko dashboard
- [ ] Upgrade to paid plan if needed

### "Could not find ticker" Errors
**Problem**: Bot can't find certain coins

**Solutions**:
- [ ] Verify ticker symbol on CoinGecko website
- [ ] Some coins use different symbols (e.g., WBTC vs BTC)
- [ ] Check CoinGecko API is accessible (not blocked)

### Memory Issues
**Problem**: Bot crashes due to memory

**Solutions**:
- [ ] Upgrade Render plan to higher memory tier
- [ ] Reduce `CACHE_TTL_MINUTES`
- [ ] Add database cleanup task (delete old records)

---

## 🔒 Security Best Practices

### Environment Variables
- [ ] Never commit `.env` file to GitHub
- [ ] Use Render's encrypted environment variables
- [ ] Rotate API keys every 90 days

### Database
- [ ] Regularly backup database (Render does this automatically)
- [ ] Don't expose database URL publicly
- [ ] Monitor for suspicious activity in logs

### Bot Access
- [ ] Keep `ADMIN_USER_IDS` private
- [ ] Don't share your bot token
- [ ] If token is compromised, use @BotFather to generate new one

---

## 📈 Scaling Your Bot

### When to Upgrade

**Upgrade Database** when:
- Database size > 1GB (Free tier limit)
- Slow query performance
- Connection timeout errors

**Upgrade Bot Service** when:
- Memory usage consistently high
- CPU throttling in logs
- Need 24/7 uptime without sleep

**Upgrade CoinGecko Plan** when:
- Hitting 10K calls/month consistently
- Need faster response times
- Want real-time data (Pro/Enterprise plans)

### Cost Scaling Guide

**Hobbyist (Free)**:
- Render Free: $0
- PostgreSQL Free: $0 (90 days)
- CoinGecko Demo: $0
- **Total: $0/month** (temporary)

**Small Bot (Recommended)**:
- Render Starter: $7/month
- PostgreSQL Starter: $7/month
- CoinGecko Demo: $0
- **Total: $14/month**

**Growing Bot**:
- Render Standard: $25/month
- PostgreSQL Standard: $25/month
- CoinGecko Analyst: $129/month
- **Total: $179/month**

---

## 🎯 Next Steps After Deployment

### Enhancements to Consider

1. **Add More Commands**
   - [ ] `/compare BTC ETH` - Compare two coins
   - [ ] `/alert BTC 50000` - Price alerts
   - [ ] `/watchlist` - Save favorite coins

2. **Add Analytics Dashboard**
   - [ ] Web dashboard showing usage stats
   - [ ] Historical scorecard trends
   - [ ] Popular coins over time

3. **Add More Data Sources**
   - [ ] DefiLlama for DeFi metrics
   - [ ] Dune Analytics for on-chain data
   - [ ] Twitter sentiment analysis

4. **Improve Scoring**
   - [ ] Chain-specific validator data
   - [ ] Real DAO governance metrics
   - [ ] Token unlock schedules

5. **Add Notifications**
   - [ ] Daily top movers
   - [ ] New coin listings
   - [ ] Significant score changes

---

## ✅ Final Checklist

Before going live:
- [ ] Bot responds to all commands
- [ ] Database is saving scorecards
- [ ] Cache is working (check logs)
- [ ] Rate limiting is active
- [ ] Admin commands work
- [ ] Error handling tested
- [ ] Logs are clean (no warnings)
- [ ] CoinGecko API is working
- [ ] README.md is updated with your bot username
- [ ] Added bot description in @BotFather

---

## 🎉 Launch Checklist

- [ ] Share bot with friends for testing
- [ ] Post in crypto Telegram groups
- [ ] Create Twitter announcement
- [ ] Monitor first 100 users closely
- [ ] Collect feedback and iterate
- [ ] Add bot to bot listing sites

---

## 📞 Support Resources

- **Render Docs**: https://render.com/docs
- **python-telegram-bot**: https://docs.python-telegram-bot.org
- **CoinGecko API**: https://www.coingecko.com/en/api/documentation
- **PostgreSQL**: https://www.postgresql.org/docs/

---

## 🐛 Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `BOT_TOKEN environment variable required` | Missing token | Add `BOT_TOKEN` in Render |
| `DATABASE_URL environment variable required` | Missing DB URL | Add `DATABASE_URL` in Render |
| `Could not find coin ID for X` | Invalid ticker | User entered wrong symbol |
| `CoinGecko rate limit hit` | Too many API calls | Add API key or increase cache |
| `Connection refused` | Database down | Check database status |
| `Timeout fetching data` | Network issue | Transient, will auto-retry |

---

**Deployment Complete!** 🎉

Your bot is now live and ready to serve crypto scorecards to users worldwide.
