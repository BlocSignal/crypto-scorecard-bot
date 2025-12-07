#!/bin/bash
# Block Signal Bot - Local Development Setup Script
# Run this to set up your development environment

set -e  # Exit on error

echo "🤖 Block Signal Bot - Development Setup"
echo "========================================"
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
    echo "❌ Python 3.8+ required. Please upgrade Python."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "🔧 Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet
echo "✓ pip upgraded"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet
    echo "✓ Dependencies installed"
else
    echo "❌ requirements.txt not found!"
    exit 1
fi

# Check for .env file
echo ""
echo "🔐 Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo ""
    echo "Creating .env from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and add your credentials:"
    echo "   1. BOT_TOKEN (from @BotFather)"
    echo "   2. DATABASE_URL (PostgreSQL connection string)"
    echo "   3. COINGECKO_API_KEY (optional, from coingecko.com)"
    echo "   4. ADMIN_USER_IDS (your Telegram user ID from @userinfobot)"
    echo ""
    echo "After editing, run: source venv/bin/activate && python bot.py"
else
    echo "✓ .env file exists"
    
    # Check if required variables are set
    if ! grep -q "BOT_TOKEN=.*[^=]$" .env 2>/dev/null; then
        echo "⚠️  BOT_TOKEN not set in .env"
    fi
    
    if ! grep -q "DATABASE_URL=.*[^=]$" .env 2>/dev/null; then
        echo "⚠️  DATABASE_URL not set in .env"
    fi
fi

# Check PostgreSQL (optional local setup)
echo ""
echo "🗄️  Checking PostgreSQL..."
if command -v psql &> /dev/null; then
    echo "✓ PostgreSQL client installed"
    
    # Check if PostgreSQL server is running
    if pg_isready &> /dev/null; then
        echo "✓ PostgreSQL server is running"
        
        # Offer to create local database
        read -p "Create local test database? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            DB_NAME="blocksignal_dev"
            DB_USER="blocksignal_user"
            DB_PASS="dev_password_123"
            
            echo "Creating database: $DB_NAME"
            
            # Create user and database
            psql -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || echo "User already exists"
            psql -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || echo "Database already exists"
            psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null
            
            echo "✓ Database created"
            echo ""
            echo "Add this to your .env file:"
            echo "DATABASE_URL=postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME"
        fi
    else
        echo "⚠️  PostgreSQL server not running"
        echo "   Start with: brew services start postgresql (macOS)"
        echo "   Or: sudo systemctl start postgresql (Linux)"
    fi
else
    echo "ℹ️  PostgreSQL not installed locally"
    echo "   Install: brew install postgresql (macOS)"
    echo "   Or use Render's database (recommended for production)"
fi

# Check bot.py exists
echo ""
echo "📝 Checking bot files..."
if [ -f "bot.py" ]; then
    echo "✓ bot.py found"
else
    echo "❌ bot.py not found! Make sure you're in the correct directory."
    exit 1
fi

# Summary
echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your credentials"
echo "2. Activate environment: source venv/bin/activate"
echo "3. Run bot: python bot.py"
echo ""
echo "Development tips:"
echo "• Use .env for local secrets (never commit this file)"
echo "• Test commands: /start, /score BTC, /trending"
echo "• Check logs for errors"
echo "• Use Ctrl+C to stop the bot"
echo ""
echo "Production deployment:"
echo "• Push code to GitHub"
echo "• Deploy to Render (see DEPLOYMENT_CHECKLIST.md)"
echo "• Use Render's environment variables"
echo ""
echo "Happy coding! 🚀"
