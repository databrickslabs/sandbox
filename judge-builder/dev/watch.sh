#!/bin/bash

set -e

# Configuration
LOG_FILE="/tmp/databricks-app-watch.log"
PID_FILE="/tmp/databricks-app-watch.pid"

# Parse command line arguments
DEPLOYMENT_MODE="dev"
if [[ "$1" == "--prod" ]]; then
  DEPLOYMENT_MODE="prod"
  echo "🚀 Production mode enabled"
fi
export DEPLOYMENT_MODE

# Kill any existing processes from previous watch.sh runs
echo "🧹 Cleaning up any existing watch.sh processes..."
if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if ps -p $OLD_PID > /dev/null 2>&1; then
    echo "Found old watch.sh process (PID: $OLD_PID), killing it..."
    kill $OLD_PID 2>/dev/null || true
    pkill -P $OLD_PID 2>/dev/null || true
    sleep 2
  fi
fi

# Create a new process group so killing this script kills all children
set -m

# Store this script's PID for cleanup
echo $$ > "$PID_FILE"

# Redirect all output to log file while still showing on terminal
exec > >(tee "$LOG_FILE") 2>&1

echo "Starting Databricks App development servers..."
echo "=============================================="
echo "Log file: $LOG_FILE"
echo "PID file: $PID_FILE"

# source .env and .env.local if they exist
if [ -f ".env" ]; then
  echo "Loading .env"
  export $(grep -v '^#' .env | xargs)
fi
if [ -f ".env.local" ]; then
  echo "Loading .env.local"
  export $(grep -v '^#' .env.local | xargs)
  # Explicitly export Databricks variables for CLI
  export DATABRICKS_HOST
  export DATABRICKS_TOKEN
fi

# Check if already authenticated to avoid opening browser every time
check_auth() {
  if [ ! -z "$DATABRICKS_CONFIG_PROFILE" ]; then
    databricks auth describe --profile $DATABRICKS_CONFIG_PROFILE > /dev/null 2>&1
  elif [ ! -z "$DATABRICKS_HOST" ]; then
    databricks auth describe --host $DATABRICKS_HOST > /dev/null 2>&1
  else
    databricks auth describe > /dev/null 2>&1
  fi
}

if command -v databricks >/dev/null 2>&1; then
  if ! check_auth; then
    echo "🔐 Not authenticated, logging in..."
    if [ ! -z "$DATABRICKS_CONFIG_PROFILE" ]; then
      databricks auth login --profile $DATABRICKS_CONFIG_PROFILE
    elif [ ! -z "$DATABRICKS_HOST" ]; then
      databricks auth login --host $DATABRICKS_HOST
    else
      databricks auth login
    fi
  else
    echo "✅ Already authenticated"
  fi
else
  echo "⚠️  Databricks CLI not found, skipping authentication"
fi

# Generate TypeScript client
echo "🔧 Generating TypeScript client..."
uv run python -m scripts.make_fastapi_client || echo "⚠️ Could not generate client (server may not be running yet)"

if [ "$DEPLOYMENT_MODE" = "prod" ]; then
  echo "Building frontend for production..."
  pushd client && npm run build && popd
  echo "✅ Frontend built successfully"

  # In production mode, only start backend (frontend served by FastAPI)
  uv run uvicorn server.app:app --reload --reload-dir server --host 0.0.0.0 --port 8000 &
  BACKEND_PID=$!
  echo "Backend PID: $BACKEND_PID"

  echo "Production mode: Frontend will be served by FastAPI at http://localhost:8000"
else
  # Development mode: start both frontend and backend
  echo "🌐 Starting frontend development server..."
  (cd client && BROWSER=none npm run dev) &
  FRONTEND_PID=$!
  echo "Frontend PID: $FRONTEND_PID"

  echo "🖥️ Starting backend development server..."
  uv run uvicorn server.app:app --reload --reload-dir server --host 0.0.0.0 --port 8000 &
  BACKEND_PID=$!
  echo "Backend PID: $BACKEND_PID"
fi

# Auto-regenerate client when server code changes
echo "🔄 Setting up auto-client generation..."
uv run watchmedo auto-restart \
  --patterns="*.py" \
  --debounce-interval=1 \
  --no-restart-on-command-exit \
  --recursive \
  --directory=server \
  uv -- run python -m scripts.make_fastapi_client &
WATCHER_PID=$!
echo "Watcher PID: $WATCHER_PID"

# Give everything time to start
sleep 3

echo ""
echo "✅ Development servers started!"
echo ""
echo "📊 Process Information:"
echo "  Watch script PID: $$"
if [ "$DEPLOYMENT_MODE" = "prod" ]; then
  echo "  Backend PID: $BACKEND_PID"
  echo "  Watcher PID: $WATCHER_PID"
  echo ""
  echo "App: http://localhost:8000"
else
  echo "  Frontend PID: $FRONTEND_PID"
  echo "  Backend PID: $BACKEND_PID"
  echo "  Watcher PID: $WATCHER_PID"
  echo ""
  # Detect the actual frontend port (default 5173, or next available)
  FRONTEND_PORT=$(netstat -an | grep LISTEN | grep ':517[3-9]' | head -1 | sed 's/.*:\([0-9]*\).*/\1/' || echo "5173")
  echo "Frontend: http://localhost:$FRONTEND_PORT"
  echo "Backend:  http://localhost:8000"
fi
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "📄 Logs: tail -f $LOG_FILE"
echo "🛑 Stop: kill \$(cat $PID_FILE) or pkill -f watch.sh"
echo ""
echo "Press Ctrl+C to stop all servers"

# Function to kill a process tree recursively
kill_tree() {
  local pid=$1
  local children=$(ps -o pid --no-headers --ppid $pid 2>/dev/null || true)
  
  for child in $children; do
    kill_tree $child
  done
  
  if ps -p $pid > /dev/null 2>&1; then
    kill $pid 2>/dev/null || true
  fi
}

# Function to cleanup processes
cleanup() {
  echo ""
  echo "🛑 Stopping servers..."
  
  # Kill each process tree we started
  for pid in $FRONTEND_PID $BACKEND_PID $WATCHER_PID; do
    if [ ! -z "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
      echo "Killing process tree PID: $pid"
      kill_tree "$pid"
    fi
  done
  
  # Kill any remaining processes that are direct children of this script
  pkill -P $$ 2>/dev/null || true
  
  # Wait a moment for graceful shutdown
  sleep 1
  
  # As a final cleanup, kill any processes still using our ports
  # (These should only be processes we started since we're in our own watch script)
  echo "Final cleanup: killing any remaining processes on our ports..."
  lsof -ti:3000 2>/dev/null | xargs -r kill 2>/dev/null || true
  lsof -ti:8000 2>/dev/null | xargs -r kill 2>/dev/null || true
  
  # Clean up PID file
  rm -f "$PID_FILE"
  
  echo "✅ Cleanup complete"
  exit 0
}

# Set trap to cleanup on exit
trap cleanup SIGINT SIGTERM EXIT

# Wait for processes
wait
