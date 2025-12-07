services:
  # PostgreSQL Database
  - type: pserv
    name: block-signal-db
    env: docker
    plan: starter  # $7/month, can use free tier but limited
    region: oregon
    databases:
      - name: blocksignal
        user: blocksignal_user

  # Telegram Bot Service  
  - type: worker
    name: block-signal-bot
    env: python
    plan: starter  # Free tier available
    region: oregon
    buildCommand: pip install -r requirements.txt
    startCommand: python bot.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: BOT_TOKEN
        sync: false  # Set manually in Render dashboard
      - key: DATABASE_URL
        fromDatabase:
          name: block-signal-db
          property: connectionString
      - key: COINGECKO_API_KEY
        sync: false  # Set manually (optional)
      - key: RATE_LIMIT_SECONDS
        value: 10
      - key: CACHE_TTL_MINUTES
        value: 30
      - key: ADMIN_USER_IDS
        sync: false  # Comma-separated: 123456,789012
    autoDeploy: true
    
# Alternative: Deploy as web service (if you add health endpoint)
# - type: web
#   name: block-signal-bot-web
#   env: python
#   buildCommand: pip install -r requirements.txt
#   startCommand: python bot.py
#   healthCheckPath: /health
