#!/bin/bash
set -e

echo "🚀 Deploying Judge Builder"
echo "=========================="

# Initialize log file
echo "Deploy started at $(date)" > ./tmp-deploy-logs.txt

# Check for uv (should be installed by setup.sh)
if ! command -v uv &> /dev/null; then
    echo "❌ uv not found. Please run ./setup.sh first."
    exit 1
fi

# Load environment
if [ -f ".env.local" ]; then
    source .env.local
else
    echo "❌ .env.local not found. Run ./setup.sh first."
    exit 1
fi

# Check required variables
if [ -z "$DATABRICKS_CONFIG_PROFILE" ]; then
    echo "❌ DATABRICKS_CONFIG_PROFILE not found. Run ./setup.sh first."
    exit 1
fi

# Get app name from environment
if [ -z "$DATABRICKS_APP_NAME" ]; then
    echo "❌ DATABRICKS_APP_NAME not found in .env.local. Run ./setup.sh first."
    exit 1
fi

APP_NAME="$DATABRICKS_APP_NAME"
echo "📱 App name: $APP_NAME"

# Set source code path
if [ -z "$DATABRICKS_SOURCE_CODE_PATH" ]; then
    echo "🔍 Getting current user..."
    CURRENT_USER=$(databricks current-user me --profile "$DATABRICKS_CONFIG_PROFILE" --output json | uv run python -c "
import os
from dotenv import load_dotenv
import json, sys

# Load environment variables from .env.local
load_dotenv('.env.local')

try:
    data = json.load(sys.stdin)
    print(data.get('userName', ''))
except:
    sys.exit(1)
")
    
    if [ -z "$CURRENT_USER" ]; then
        echo "❌ Could not determine current user. Please set DATABRICKS_SOURCE_CODE_PATH in .env.local"
        exit 1
    fi
    
    DATABRICKS_SOURCE_CODE_PATH="/Workspace/Users/$CURRENT_USER/$APP_NAME"
    echo "DATABRICKS_SOURCE_CODE_PATH=$DATABRICKS_SOURCE_CODE_PATH" >> .env.local
fi

echo "📂 Source code path: $DATABRICKS_SOURCE_CODE_PATH"

# Build frontend
echo "🏗️ Building frontend..."
cd client
echo "Building frontend at $(date)" >> ../tmp-deploy-logs.txt

# Clean and reinstall dependencies if build fails
if ! npm run build >> ../tmp-deploy-logs.txt 2>&1; then
    echo "Cleaning node_modules and reinstalling dependencies at $(dat)" >> ../tmp-deploy-logs.txt
    rm -rf node_modules package-lock.json
    npm install >> ../tmp-deploy-logs.txt 2>&1
    if ! npm run build >> ../tmp-deploy-logs.txt 2>&1; then
        cd ..
        exit 1
    fi
fi

cd ..

# Generate requirements.txt
echo "📦 Generating requirements.txt..."
uv run python scripts/generate_semver_requirements.py

# Create/update app.yaml with environment variables
echo "📝 Updating app.yaml with environment variables..."
cat > app.yaml << EOF
command:
  - "uvicorn"
  - "server.app:app"
env:
  - name: "JUDGE_OPTIMIZER"
    value: "${JUDGE_OPTIMIZER:-simba}"
EOF

# Create workspace directory and sync source
echo "📂 Creating workspace directory..."
databricks workspace mkdirs "$DATABRICKS_SOURCE_CODE_PATH" --profile "$DATABRICKS_CONFIG_PROFILE"

echo "📤 Syncing source code to workspace (this can take a few minutes)..."
databricks sync --full . "$DATABRICKS_SOURCE_CODE_PATH" --profile "$DATABRICKS_CONFIG_PROFILE" > /dev/null 2>&1

# Create app if it doesn't exist
echo "🔧 Ensuring app exists..."

# Check if app exists
echo "Checking if app $APP_NAME exists..."
APPS_JSON=$(databricks apps list --profile "$DATABRICKS_CONFIG_PROFILE" --output json)
if echo "$APPS_JSON" | grep -q "\"name\": \"$APP_NAME\""; then
    echo "✅ App $APP_NAME already exists"
else
    echo "🆕 App $APP_NAME not found, creating..."
    
    # Get workspace host for info display
    WORKSPACE_HOST=$(databricks auth env --profile "$DATABRICKS_CONFIG_PROFILE" | grep DATABRICKS_HOST= | cut -d'=' -f2)
    if [ ! -z "$WORKSPACE_HOST" ]; then
        echo ""
        echo "⚠️  Creating app $APP_NAME..."
        echo "   This will take a few minutes."
        echo "   "
        echo "   📊 App management page:"
        echo "   $WORKSPACE_HOST/resources/compute/apps"
        echo ""
    fi
    
    # Create the app
    echo -n "Creating app (this will take a few minutes)..."
    echo "Creating app $APP_NAME at $(date)" >> ./tmp-deploy-logs.txt
    if databricks apps create "$APP_NAME" --profile "$DATABRICKS_CONFIG_PROFILE" >> ./tmp-deploy-logs.txt 2>&1; then
        echo " ✅"
    else
        echo ""
        echo "❌ Could not create app $APP_NAME"
        echo "Check ./tmp-deploy-logs.txt for details"
        exit 1
    fi
fi

# Deploy using Databricks CLI
echo "🚀 Deploying to Databricks..."

# Deploy app
databricks apps deploy "$APP_NAME" --source-code-path "$DATABRICKS_SOURCE_CODE_PATH" --profile "$DATABRICKS_CONFIG_PROFILE"

# Get app URL
echo "🔍 Getting app URL..."
APP_INFO=$(databricks apps list --profile "$DATABRICKS_CONFIG_PROFILE" --output json | uv run python -c "
import os
from dotenv import load_dotenv
import json, sys

# Load environment variables from .env.local
load_dotenv('.env.local')

try:
    data = json.load(sys.stdin)
    apps = data if isinstance(data, list) else data.get('apps', [])
    for app in apps:
        if app.get('name') == os.environ.get('DATABRICKS_APP_NAME'):
            print(f\"✅ Deployed successfully!\")
            print(f\"🌐 App URL: {app.get('url', 'URL not available')}\")
            print(f\"📊 Logs: {app.get('url', '')}/logz\" if app.get('url') else '📊 Logs: Check Databricks console')
            break
    else:
        print('✅ Deploy completed')
except Exception as e:
    print(f'Note: Could not retrieve app URL: {e}')
    print('✅ Deploy completed')
")

echo "$APP_INFO"
