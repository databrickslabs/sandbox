#!/bin/bash
set -e

echo "🚀 Judge Builder Setup"
echo "====================="

# Check for uv or install it
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "✅ uv found: $(uv --version)"

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required. Please install Node.js 18+ and try again."
    exit 1
fi

# Check for Databricks CLI
if ! command -v databricks &> /dev/null; then
    echo "❌ Databricks CLI is required. Please install it and try again."
    exit 1
fi

# Create virtual environment with correct Python version
echo "🐍 Creating Python virtual environment..."
uv venv --python 3.11

# Generate requirements files
echo "📦 Generating requirements files..."
uv run python scripts/generate_semver_requirements.py

# Install Python dependencies (production only)
echo "📦 Installing Python dependencies..."
uv pip install -r requirements.txt

# Install frontend dependencies  
echo "📦 Installing frontend dependencies..."
cd client
npm install
cd ..

# Environment setup
echo ""
echo "🔐 Databricks Configuration"
echo "============================"

UPDATE_CONFIG=false

if [ -f ".env.local" ]; then
    echo "✅ Found existing .env.local"
    source .env.local
    echo ""
    echo "Current configuration:"
    echo "  Profile: ${DATABRICKS_CONFIG_PROFILE:-default}"
    echo "  App Name: ${DATABRICKS_APP_NAME:-judge-builder}"
    echo ""
    read -p "Do you want to update these values? (y/N): " update_choice
    if [[ "$update_choice" =~ ^[Yy]$ ]]; then
        UPDATE_CONFIG=true
    fi
else
    echo "Creating .env.local file..."
    echo "# Databricks Configuration" > .env.local
    UPDATE_CONFIG=true
fi

if [ "$UPDATE_CONFIG" = true ]; then
    # Check for Databricks profiles
    echo ""
    echo "🔧 Databricks CLI Profile Setup"
    echo "================================"
    
    # List available profiles
    PROFILES=$(databricks auth profiles 2>/dev/null)
    
    if [ -z "$PROFILES" ]; then
        echo "❌ No Databricks profiles found."
        echo ""
        echo "Please set up a profile first using:"
        echo "  databricks configure"
        echo ""
        echo "For more info: https://docs.databricks.com/aws/en/dev-tools/cli/profiles"
        exit 1
    fi
    
    echo "Available profiles:"
    echo "$PROFILES" | nl -w2 -s'. '
    echo ""
    
    if [ -n "$DATABRICKS_CONFIG_PROFILE" ]; then
        read -p "Profile name (current: $DATABRICKS_CONFIG_PROFILE): " profile
        profile=${profile:-$DATABRICKS_CONFIG_PROFILE}
    else
        read -p "Profile name (default: DEFAULT): " profile
        profile=${profile:-DEFAULT}
    fi
    
    if [ "$profile" != "$DATABRICKS_CONFIG_PROFILE" ]; then
        # Remove existing line and add new one
        if [ -f .env.local ]; then
            sed -i.bak '/^DATABRICKS_CONFIG_PROFILE=/d' .env.local && rm .env.local.bak
        fi
        echo "DATABRICKS_CONFIG_PROFILE=$profile" >> .env.local
        export DATABRICKS_CONFIG_PROFILE="$profile"
    fi

    
    # App configuration
    echo ""
    echo "🚀 App Configuration"
    echo "===================="
    
    if [ -n "$DATABRICKS_APP_NAME" ]; then
        read -p "App Name (current: $DATABRICKS_APP_NAME): " app_name
        app_name=${app_name:-$DATABRICKS_APP_NAME}
    else
        read -p "App Name (default: judge-builder): " app_name
        app_name=${app_name:-judge-builder}
    fi
    
    if [ "$app_name" != "$DATABRICKS_APP_NAME" ]; then
        # Remove existing line and add new one
        if [ -f .env.local ]; then
            sed -i.bak '/^DATABRICKS_APP_NAME=/d' .env.local && rm .env.local.bak
        fi
        echo "DATABRICKS_APP_NAME=$app_name" >> .env.local
        export DATABRICKS_APP_NAME="$app_name"
    fi
    
fi

# Test connection
echo ""
echo "🔍 Testing connection..."
if uv run python -c "
import os
from dotenv import load_dotenv
from databricks.sdk import WorkspaceClient

# Load environment variables from .env.local
load_dotenv('.env.local')

try:
    profile = os.environ.get('DATABRICKS_CONFIG_PROFILE', 'DEFAULT')
    w = WorkspaceClient(profile=profile)
    user = w.current_user.me()
    print(f'✅ Connected as {user.user_name}')
except Exception as e:
    print(f'❌ Connection failed: {e}')
    exit(1)
"; then
    echo "✅ Setup complete!"
    echo ""
    echo "🎯 Virtual environment created at: .venv/"
    echo ""
    echo "Next step: run './deploy.sh' when ready to deploy"
else
    echo "❌ Setup failed. Please check your credentials."
    exit 1
fi
