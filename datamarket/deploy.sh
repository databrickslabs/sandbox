#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# DataMarket deploy.sh
# Deploys DataMarket to your Databricks workspace from scratch.
# Usage: ./deploy.sh [options]
#
# Options:
#   --profile        PROFILE        Databricks CLI profile (default: DEFAULT)
#   --admin-email    EMAIL          Your email — gets admin role on first login (required)
#   --lakebase-project NAME         Lakebase autoscaling project name (default: datamarket)
#   --app-name       NAME           Databricks App name (default: datamarket)
#   --warehouse-id   ID             SQL Warehouse ID — auto-grants SP 'Can use' permission
#   --grant-catalogs true|false     Auto-grant SP USE CATALOG/SCHEMA on all UC catalogs (default: true)
#   --demo-mode      true|false     Enable persona switcher (default: false)
#   --seed           true|false     Apply schema/seed.sql after schema init — loads demo data products,
#                                   users, and requests (default: true when --demo-mode true, else false)
#   --use-bundle     true|false     Use Databricks Asset Bundle (DAB) for Lakebase+app deploy (default: false)
#   --bundle-target  TARGET         DAB target to deploy: dev or prod (default: prod)
#   --help                          Show this help
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
info() { echo -e "${BLUE}▸${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
fail() { echo -e "${RED}✗ ERROR:${NC} $*"; exit 1; }
step() { echo -e "\n${BOLD}${BLUE}[$1/$TOTAL_STEPS]${NC} ${BOLD}$2${NC}"; }

TOTAL_STEPS=10

# ── Defaults ─────────────────────────────────────────────────────────────────
PROFILE="DEFAULT"
ADMIN_EMAIL=""
LAKEBASE_PROJECT="datamarket"
APP_NAME="datamarket"
DEMO_MODE="false"
SEED_DATA=""          # empty = auto (true when demo-mode, false otherwise)
WAREHOUSE_ID=""
GRANT_CATALOGS="true"
USE_BUNDLE="false"
BUNDLE_TARGET="prod"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Parse args ────────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --profile)          PROFILE="$2";          shift 2 ;;
    --admin-email)      ADMIN_EMAIL="$2";      shift 2 ;;
    --lakebase-project) LAKEBASE_PROJECT="$2"; shift 2 ;;
    --app-name)         APP_NAME="$2";         shift 2 ;;
    --demo-mode)        DEMO_MODE="$2";        shift 2 ;;
    --seed)             SEED_DATA="$2";        shift 2 ;;
    --warehouse-id)     WAREHOUSE_ID="$2";     shift 2 ;;
    --grant-catalogs)   GRANT_CATALOGS="$2";   shift 2 ;;
    --use-bundle)       USE_BUNDLE="$2";       shift 2 ;;
    --bundle-target)    BUNDLE_TARGET="$2";    shift 2 ;;
    --help|-h)
      sed -n '/^# /p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) fail "Unknown option: $1. Run with --help for usage." ;;
  esac
done

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}DataMarket — Automated Deploy${NC}"
echo "────────────────────────────────"
echo ""

# ── Prerequisites ─────────────────────────────────────────────────────────────
step 1 "Checking prerequisites"

command -v databricks >/dev/null 2>&1 || fail "Databricks CLI not found. Install: brew tap databricks/tap && brew install databricks"
command -v node        >/dev/null 2>&1 || fail "Node.js not found. Install: brew install node"
command -v npm         >/dev/null 2>&1 || fail "npm not found."
command -v python3     >/dev/null 2>&1 || fail "python3 not found."
PSQL_BIN=$(command -v psql 2>/dev/null || true)
if [[ -z "$PSQL_BIN" ]]; then
  warn "psql not found — schema init and SP grants will be skipped."
  warn "Install with: brew install postgresql@16"
  warn "The app will auto-create tables on first start, but you must grant schema access manually."
fi
ok "All prerequisites met"

# ── Validate CLI auth ─────────────────────────────────────────────────────────
step 2 "Reading Databricks profile"

AUTH_JSON=$(databricks auth describe --profile "$PROFILE" --output json 2>/dev/null) \
  || fail "Cannot authenticate with profile '${PROFILE}'. Run: databricks configure --profile ${PROFILE}"

DATABRICKS_HOST=$(echo "$AUTH_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('details',{}).get('host','') or d.get('host',''))" 2>/dev/null || true)
DATABRICKS_USER=$(echo "$AUTH_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('details',{}).get('user','') or d.get('user',''))" 2>/dev/null || true)

# Fallback: parse from profile config
if [[ -z "$DATABRICKS_HOST" ]]; then
  DATABRICKS_HOST=$(databricks auth describe --profile "$PROFILE" 2>&1 | grep -i "Host:" | head -1 | awk '{print $2}' || true)
fi
if [[ -z "$DATABRICKS_USER" ]]; then
  DATABRICKS_USER=$(databricks auth describe --profile "$PROFILE" 2>&1 | grep -i "User:" | head -1 | awk '{print $2}' || true)
fi

[[ -z "$DATABRICKS_HOST" ]] && fail "Could not detect DATABRICKS_HOST from profile. Set it manually in the generated app.yaml after this script runs."
DATABRICKS_HOST="${DATABRICKS_HOST%/}"  # strip trailing slash
ok "Host:  $DATABRICKS_HOST"
ok "User:  ${DATABRICKS_USER:-<service-principal>}"

# ── Prompt for required values ────────────────────────────────────────────────
if [[ -z "$ADMIN_EMAIL" ]]; then
  # Auto-detect from profile first
  ADMIN_EMAIL="${DATABRICKS_USER:-}"
  if [[ -z "$ADMIN_EMAIL" ]]; then
    echo ""
    read -rp "  Your email address (becomes the first admin): " ADMIN_EMAIL
    [[ -z "$ADMIN_EMAIL" ]] && fail "ADMIN_EMAIL is required."
  else
    info "Admin email auto-detected from profile: ${ADMIN_EMAIL}"
  fi
fi
ok "Admin: $ADMIN_EMAIL"

# Workspace path — derive from user email or use default
WS_USER="${DATABRICKS_USER:-$ADMIN_EMAIL}"
WS_USER_PATH="${WS_USER//@/%40}"  # URL-encode @ for workspace path display
WORKSPACE_PATH="/Workspace/Users/${WS_USER}/${APP_NAME}"
info "Workspace path: ${WORKSPACE_PATH}"

# ── Bundle path ───────────────────────────────────────────────────────────────
# When --use-bundle true, the DAB handles Lakebase provisioning + app deploy.
# deploy.sh then picks up from Step 7 (Lakebase schema grants) onwards.
if [[ "$USE_BUNDLE" == "true" ]]; then
  BUNDLE_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"  # repo root (3 levels up from src/app)
  if [[ ! -f "${BUNDLE_ROOT}/databricks.yml" ]]; then
    fail "databricks.yml not found at ${BUNDLE_ROOT}. Run from the repo root or check --use-bundle."
  fi

  info "─── Bundle mode (DAB) — steps 3–6 handled by databricks bundle deploy ───"
  info "Bundle root: ${BUNDLE_ROOT}"
  info "Target: ${BUNDLE_TARGET}"

  # Validate CLI version (postgres_projects needs >= 0.287.0)
  CLI_VERSION=$(databricks -v 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)
  info "Databricks CLI version: ${CLI_VERSION:-unknown}"

  # Build frontend first (DAB doesn't know how to build Node apps)
  step 3 "Building frontend"
  (cd "$SCRIPT_DIR" && npm install --silent 2>/dev/null && npm run build:local 2>&1 | tail -4)
  ok "Build complete"

  # Ensure app.yaml exists (required in source dir before bundle deploy)
  step 4 "Checking app.yaml"
  if [[ ! -f "${SCRIPT_DIR}/app.yaml" ]]; then
    info "app.yaml not found — generating from values provided..."
    # Discover Lakebase hostname for app.yaml (needed even in bundle mode)
    LAKEBASE_HOST=""
    LAKEBASE_CACHE_FILE="${SCRIPT_DIR}/.lakebase-${APP_NAME}.cache"
    BRANCH_NAME=$(databricks api get "2.0/postgres/autoscaling/projects/${LAKEBASE_PROJECT}/branches" \
      --profile "$PROFILE" 2>/dev/null \
      | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    branches = d.get('branches', d.get('items', []))
    prod = next((b.get('name','') for b in branches if b.get('name','') == 'production'), '')
    first = branches[0].get('name','') if branches else ''
    print(prod or first)
except: print('')
" 2>/dev/null || true)
    if [[ -n "$BRANCH_NAME" ]]; then
      LAKEBASE_ENDPOINT_PATH="projects/${LAKEBASE_PROJECT}/branches/${BRANCH_NAME}/endpoints/primary"
      LAKEBASE_HOST=$(databricks api get "2.0/postgres/endpoints/${LAKEBASE_ENDPOINT_PATH}" \
        --profile "$PROFILE" 2>/dev/null \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('read_write_dns','') or d.get('dns','') or '')" 2>/dev/null || true)
    fi
    if [[ -z "$LAKEBASE_HOST" && -f "$LAKEBASE_CACHE_FILE" ]]; then
      LAKEBASE_HOST=$(cat "$LAKEBASE_CACHE_FILE" 2>/dev/null || true)
    fi
    if [[ -z "$LAKEBASE_HOST" ]]; then
      warn "Lakebase hostname not yet discoverable (project may not exist yet)."
      warn "The DAB will provision Lakebase. After 'databricks bundle deploy' completes, re-run this script to finalize app.yaml."
      info "Proceeding with bundle deploy — app.yaml will be created after Lakebase is up."
    fi
    LAKEBASE_ENDPOINT="${LAKEBASE_ENDPOINT_PATH:-projects/${LAKEBASE_PROJECT}/branches/production/endpoints/primary}"
    cat > "${SCRIPT_DIR}/app.yaml" << YAML
command:
  - "node"
  - "app.js"
env:
  - name: DATABRICKS_HOST
    value: "${DATABRICKS_HOST}"
  - name: ADMIN_EMAIL
    value: "${ADMIN_EMAIL}"
  - name: LAKEBASE_HOST
    value: "${LAKEBASE_HOST}"
  - name: LAKEBASE_DB
    value: "databricks_postgres"
  - name: LAKEBASE_SCHEMA
    value: "${APP_NAME}"
  - name: LAKEBASE_ENDPOINT
    value: "${LAKEBASE_ENDPOINT}"
  - name: DEMO_MODE
    value: "${DEMO_MODE}"
YAML
    ok "app.yaml written"
  else
    ok "app.yaml already exists — using as-is"
  fi

  step 5 "Running databricks bundle deploy (Lakebase + App)"
  cd "$BUNDLE_ROOT"
  databricks bundle deploy -t "$BUNDLE_TARGET" \
    --var "admin_email=${ADMIN_EMAIL}" \
    --var "demo_mode=${DEMO_MODE}" \
    --var "lakebase_project=${LAKEBASE_PROJECT}" \
    --var "app_name=${APP_NAME}" \
    --profile "$PROFILE" 2>&1 | tail -10
  ok "Bundle deployed"
  cd "$SCRIPT_DIR"

  # After bundle deploy, update app.yaml with discovered Lakebase hostname if missing
  step 6 "Refreshing app.yaml with Lakebase hostname"
  LAKEBASE_CACHE_FILE="${SCRIPT_DIR}/.lakebase-${APP_NAME}.cache"
  BRANCH_NAME=$(databricks api get "2.0/postgres/autoscaling/projects/${LAKEBASE_PROJECT}/branches" \
    --profile "$PROFILE" 2>/dev/null \
    | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    branches = d.get('branches', d.get('items', []))
    prod = next((b.get('name','') for b in branches if b.get('name','') == 'production'), '')
    first = branches[0].get('name','') if branches else ''
    print(prod or first)
except: print('')
" 2>/dev/null || true)
  if [[ -n "$BRANCH_NAME" ]]; then
    LAKEBASE_ENDPOINT="projects/${LAKEBASE_PROJECT}/branches/${BRANCH_NAME}/endpoints/primary"
    LAKEBASE_HOST=$(databricks api get "2.0/postgres/endpoints/${LAKEBASE_ENDPOINT}" \
      --profile "$PROFILE" 2>/dev/null \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('read_write_dns','') or d.get('dns','') or '')" 2>/dev/null || true)
    if [[ -n "$LAKEBASE_HOST" ]]; then
      echo "$LAKEBASE_HOST" > "$LAKEBASE_CACHE_FILE"
      # Patch app.yaml with real hostname
      python3 -c "
import re, sys
with open('${SCRIPT_DIR}/app.yaml', 'r') as f: content = f.read()
content = re.sub(r'(name: LAKEBASE_HOST\n\s+value: \")[^\"]*\"', r'\1${LAKEBASE_HOST}\"', content)
with open('${SCRIPT_DIR}/app.yaml', 'w') as f: f.write(content)
print('app.yaml patched with real Lakebase hostname')
"
      # Redeploy app with correct Lakebase host
      info "Redeploying app with correct Lakebase hostname..."
      databricks apps deploy "$APP_NAME" \
        --source-code-path "${WORKSPACE_PATH}" \
        --profile "$PROFILE" 2>&1 | tail -3 || true
      ok "app.yaml updated: ${LAKEBASE_HOST}"
    fi
  fi

  # Skip to grants — app is already deployed via bundle
  TOTAL_STEPS=10
  SP_UUID=$(databricks apps get "$APP_NAME" --profile "$PROFILE" --output json 2>/dev/null \
    | python3 -c "
import sys, json
d = json.load(sys.stdin)
candidates = [
  d.get('service_principal_client_id'),
  d.get('service_principal', {}).get('client_id'),
]
print(next((c for c in candidates if c), ''))
" 2>/dev/null || true)

  # Jump straight to step 7 (grants)
  # shellcheck disable=SC2034
  BUNDLE_DEPLOY_DONE=true
fi

# ── Standard path: Lakebase detection, app.yaml gen, build, upload, deploy ───
if [[ "${BUNDLE_DEPLOY_DONE:-false}" != "true" ]]; then

step 3 "Detecting Lakebase configuration"

# ── Pre-flight: verify token is fresh before the long Lakebase operation ──────
# Lakebase creation takes 2–3 min. An expired token mid-way leaves the project
# in a broken state. Fail fast here rather than halfway through provisioning.
TOKEN_CHECK=$(databricks auth token --profile "$PROFILE" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)
if [[ -z "$TOKEN_CHECK" ]]; then
  fail "$(cat <<MSG
CLI auth token is expired or invalid for profile '${PROFILE}'.
Re-authenticate first, then re-run deploy:

  databricks auth login --host ${DATABRICKS_HOST} --profile ${PROFILE}
  ./deploy.sh --profile ${PROFILE}
MSG
)"
fi
ok "Auth token is valid"

LAKEBASE_HOST=""
LAKEBASE_ENDPOINT=""
LAKEBASE_CACHE_FILE="${SCRIPT_DIR}/.lakebase-${APP_NAME}.cache"

# ── Helper: get the first/production branch name for a project ────────────────
_get_branch() {
  databricks postgres list-branches "projects/${LAKEBASE_PROJECT}" \
    --profile "$PROFILE" -o json 2>/dev/null \
  | python3 -c "
import sys, json
try:
    items = json.load(sys.stdin)
    if not isinstance(items, list): items = []
    # resource names look like 'projects/foo/branches/bar' — extract short name
    names = [b.get('name','').split('/')[-1] for b in items if b.get('name','')]
    prod = next((n for n in names if n == 'production'), '')
    print(prod or (names[0] if names else ''))
except: print('')
" 2>/dev/null || true
}

# ── Helper: get endpoint hostname for a branch ────────────────────────────────
_get_host() {
  local branch="$1"
  databricks postgres list-endpoints "projects/${LAKEBASE_PROJECT}/branches/${branch}" \
    --profile "$PROFILE" -o json 2>/dev/null \
  | python3 -c "
import sys, json
try:
    items = json.load(sys.stdin)
    if not isinstance(items, list): items = []
    for ep in items:
        host = ep.get('status', {}).get('hosts', {}).get('host', '')
        if host:
            print(host)
            break
except: print('')
" 2>/dev/null || true
}

info "Looking up Lakebase project: ${LAKEBASE_PROJECT}"
BRANCH_NAME=$(_get_branch)

# ── Project doesn't exist yet — create it ─────────────────────────────────────
if [[ -z "$BRANCH_NAME" ]]; then
  info "Project '${LAKEBASE_PROJECT}' not found — creating Lakebase Autoscaling project..."
  info "(This takes ~2–3 minutes on first deploy — the CLI will wait automatically)"

  CREATE_OUT=$(databricks postgres create-project "$LAKEBASE_PROJECT" \
    --profile "$PROFILE" -o json 2>&1 || true)

  if echo "$CREATE_OUT" | python3 -c "import sys,json; json.load(sys.stdin)" &>/dev/null; then
    ok "Project '${LAKEBASE_PROJECT}' created"
  else
    # May already exist or be in progress — not fatal
    warn "create-project output: ${CREATE_OUT:0:200}"
  fi

  # Poll for branch (provisioned after project creation)
  info "Waiting for Lakebase branch to be ready..."
  for i in $(seq 1 36); do
    BRANCH_NAME=$(_get_branch)
    [[ -n "$BRANCH_NAME" ]] && { ok "Branch ready: ${BRANCH_NAME}"; break; }
    echo -n "."; sleep 5
  done
  echo ""
  if [[ -z "$BRANCH_NAME" ]]; then
    warn "Lakebase branch not ready after 3 min — project '${LAKEBASE_PROJECT}' is stuck."
    warn "This usually means a previous deploy was interrupted (e.g. auth token expired)."
    info "Auto-recovering: deleting stuck project and recreating..."

    DEL_OUT=$(databricks postgres delete-project "projects/${LAKEBASE_PROJECT}" \
      --profile "$PROFILE" 2>&1 || true)
    if echo "$DEL_OUT" | grep -qi "error\|INTERNAL\|not found"; then
      warn "Could not auto-delete stuck project: ${DEL_OUT:0:150}"
      warn "Delete manually: Compute → Lakebase → ${LAKEBASE_PROJECT} → Settings → Delete project"
      warn "Then re-run: ./deploy.sh --profile ${PROFILE}"
      fail "Lakebase branch unavailable and auto-recovery failed. See above."
    fi
    ok "Stuck project deleted — recreating..."
    sleep 5

    databricks postgres create-project "$LAKEBASE_PROJECT" \
      --profile "$PROFILE" -o json 2>&1 | head -3 || true

    info "Waiting for Lakebase branch to be ready (attempt 2)..."
    for i in $(seq 1 36); do
      BRANCH_NAME=$(_get_branch)
      [[ -n "$BRANCH_NAME" ]] && { ok "Branch ready: ${BRANCH_NAME}"; break; }
      echo -n "."; sleep 5
    done
    echo ""
    [[ -z "$BRANCH_NAME" ]] && fail "Lakebase branch still unavailable after recreation. Check Compute → Lakebase in the UI."
  fi
fi

# ── Resolve endpoint hostname ─────────────────────────────────────────────────
LAKEBASE_ENDPOINT="projects/${LAKEBASE_PROJECT}/branches/${BRANCH_NAME}/endpoints/primary"
LAKEBASE_HOST=$(_get_host "$BRANCH_NAME")

# Fall back to cache if API doesn't return a hostname yet (endpoint still provisioning)
if [[ -z "$LAKEBASE_HOST" && -f "$LAKEBASE_CACHE_FILE" ]]; then
  LAKEBASE_HOST=$(cat "$LAKEBASE_CACHE_FILE" 2>/dev/null || true)
  [[ -n "$LAKEBASE_HOST" ]] && ok "Lakebase hostname loaded from cache."
fi

# Last resort — ask once, cache the answer
if [[ -z "$LAKEBASE_HOST" ]]; then
  warn "Could not resolve Lakebase hostname from API (endpoint may still be provisioning)."
  warn "Go to: Compute → Lakebase → ${LAKEBASE_PROJECT} → Overview → Connection details"
  echo ""
  read -rp "  Paste your Lakebase hostname (ep-...): " LAKEBASE_HOST
  [[ -z "$LAKEBASE_HOST" ]] && fail "Lakebase hostname is required."
fi

# Always cache the resolved hostname for future runs
echo "$LAKEBASE_HOST" > "$LAKEBASE_CACHE_FILE"

ok "Lakebase host:     ${LAKEBASE_HOST}"
ok "Lakebase endpoint: ${LAKEBASE_ENDPOINT}"

# ── Generate app.yaml ─────────────────────────────────────────────────────────
step 4 "Generating app.yaml"

APP_YAML_PATH="${SCRIPT_DIR}/app.yaml"

cat > "$APP_YAML_PATH" << YAML
command:
  - "node"
  - "app.js"
env:
  # ── Databricks Identity ────────────────────────────────────────────────────
  - name: DATABRICKS_HOST
    value: "${DATABRICKS_HOST}"

  # ── Admin bootstrap ────────────────────────────────────────────────────────
  # On first SSO login the app auto-promotes this email to admin.
  - name: ADMIN_EMAIL
    value: "${ADMIN_EMAIL}"

  # ── Lakebase Connection ────────────────────────────────────────────────────
  - name: LAKEBASE_HOST
    value: "${LAKEBASE_HOST}"
  - name: LAKEBASE_DB
    value: "databricks_postgres"
  - name: LAKEBASE_SCHEMA
    value: "${APP_NAME}"
  - name: LAKEBASE_ENDPOINT
    value: "${LAKEBASE_ENDPOINT}"

  # ── Mode ──────────────────────────────────────────────────────────────────
  # false = real SSO identity + UC grants. true = persona switcher (demos only)
  - name: DEMO_MODE
    value: "${DEMO_MODE}"
YAML

ok "app.yaml written to ${APP_YAML_PATH}"

# ── Build frontend ────────────────────────────────────────────────────────────
step 5 "Building frontend"

(cd "$SCRIPT_DIR" && npm install --silent 2>/dev/null && npm run build:local 2>&1 | tail -4)
ok "Build complete"

# ── Build frontend ────────────────────────────────────────────────────────────
step 6 "Building frontend and uploading to Databricks"

if command -v node >/dev/null 2>&1 && [[ -f "${SCRIPT_DIR}/vite.config.js" ]]; then
  info "Running Vite build..."
  (cd "${SCRIPT_DIR}" && npm run build:local 2>&1 | tail -5) \
    && ok "Frontend built" \
    || warn "Vite build failed — uploading existing dist/"
else
  info "Node/Vite not found — uploading existing dist/"
fi

info "Uploading dist/..."
databricks workspace import-dir "${SCRIPT_DIR}/dist" "${WORKSPACE_PATH}/dist" \
  --overwrite --profile "$PROFILE" 2>&1 | tail -2

info "Uploading backend modules..."
for f in app.js db.js auth.js databricks.js; do
  databricks workspace import "${WORKSPACE_PATH}/${f}" \
    --file "${SCRIPT_DIR}/${f}" --format AUTO --overwrite \
    --profile "$PROFILE" 2>/dev/null
done

if [[ -d "${SCRIPT_DIR}/routes" ]]; then
  databricks workspace import-dir "${SCRIPT_DIR}/routes" "${WORKSPACE_PATH}/routes" \
    --overwrite --profile "$PROFILE" 2>&1 | tail -2
fi

if [[ -d "${SCRIPT_DIR}/lib" ]]; then
  databricks workspace import-dir "${SCRIPT_DIR}/lib" "${WORKSPACE_PATH}/lib" \
    --overwrite --profile "$PROFILE" 2>&1 | tail -2
fi

# Upload remaining config files
for f in package.json manifest.yaml app.yaml; do
  [[ -f "${SCRIPT_DIR}/${f}" ]] && \
    databricks workspace import "${WORKSPACE_PATH}/${f}" \
      --file "${SCRIPT_DIR}/${f}" --format AUTO --overwrite \
      --profile "$PROFILE" 2>/dev/null || true
done

info "Deploying app (this takes ~2 minutes)..."

# Create the app first if it doesn't exist yet
if ! databricks apps get "$APP_NAME" --profile "$PROFILE" --output json >/dev/null 2>&1; then
  info "App does not exist yet — creating..."
  databricks apps create "$APP_NAME" --profile "$PROFILE" 2>&1 | tail -3
fi

DEPLOY_OUT=$(databricks apps deploy "$APP_NAME" \
  --source-code-path "$WORKSPACE_PATH" \
  --profile "$PROFILE" 2>&1)

if echo "$DEPLOY_OUT" | grep -q '"state":"SUCCEEDED"'; then
  ok "App deployed successfully"
else
  warn "Deploy output:"
  echo "$DEPLOY_OUT" | tail -10
  fail "Deploy did not reach SUCCEEDED state. Check the output above."
fi

fi  # end standard path (not bundle mode)

# ── Lakebase schema grants ────────────────────────────────────────────────────
step 7 "Granting Lakebase schema permissions to the app service principal"

# Get the SP UUID from the running app
SP_UUID=$(databricks apps get "$APP_NAME" --profile "$PROFILE" --output json 2>/dev/null \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
# Try several paths where the SP UUID might live
candidates = [
  d.get('service_principal_client_id'),
  d.get('service_principal', {}).get('client_id'),
  d.get('pending_deployment', {}).get('creator', {}).get('client_id'),
]
print(next((c for c in candidates if c), ''))
" 2>/dev/null || true)

# Fallback: scrape from app logs
if [[ -z "$SP_UUID" ]]; then
  SP_UUID=$(databricks apps logs "$APP_NAME" --profile "$PROFILE" 2>&1 \
    | grep -oE "Apps SP [0-9a-f-]{8}" | head -1 | awk '{print $3}' || true)
  # Logs show truncated UUID — try to get full UUID via SCIM if we have a prefix
fi

if [[ -z "$SP_UUID" ]]; then
  warn "Could not auto-detect the app service principal UUID."
  warn "Find it in: Apps → ${APP_NAME} → Service Principal"
  echo ""
  read -rp "  Paste the SP client UUID (or press Enter to skip): " SP_UUID
fi

if [[ -z "$SP_UUID" ]]; then
  warn "Skipping Lakebase grants — you will need to run these manually:"
  echo ""
  echo "  GRANT USAGE  ON SCHEMA ${APP_NAME} TO \"<your-sp-uuid>\";"
  echo "  GRANT CREATE ON SCHEMA ${APP_NAME} TO \"<your-sp-uuid>\";"
  echo ""
  warn "Until this is done, the app will start but data will not persist."
else
  info "Granting schema access to SP: ${SP_UUID}"

  # Generate a short-lived Lakebase token
  PG_TOKEN=$(databricks auth token --profile "$PROFILE" \
    | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)

  if [[ -z "$PSQL_BIN" ]]; then
    warn "psql not available — skipping schema init and grants. Run deploy again after installing psql."
    warn "  brew install postgresql@16"
  elif [[ -z "$PG_TOKEN" ]]; then
    warn "Could not generate a Lakebase token. Grants skipped — run manually."
  else
    # Step 1: Create schema + apply schema.sql (creates all core tables)
    SCHEMA_SQL="${SCRIPT_DIR}/../../schema/schema.sql"
    PG_CONN="host=${LAKEBASE_HOST} port=5432 dbname=databricks_postgres sslmode=require user=${DATABRICKS_USER:-${ADMIN_EMAIL}}"

    SCHEMA_OUT=$(PGPASSWORD="$PG_TOKEN" psql "$PG_CONN" \
      -c "CREATE SCHEMA IF NOT EXISTS ${APP_NAME}; SET search_path TO ${APP_NAME};" \
      2>&1 || true)
    if echo "$SCHEMA_OUT" | grep -qi "FATAL\|error:"; then
      warn "Lakebase connection failed during schema create:"
      echo "$SCHEMA_OUT" | grep -i "FATAL\|error:" | head -3
      warn "The app will try to auto-create tables on first start."
      warn "If this persists, ensure your CLI profile uses OAuth (not PAT):"
      warn "  databricks auth login --profile ${PROFILE} --host ${DATABRICKS_HOST}"
    fi

    if [[ -f "$SCHEMA_SQL" ]]; then
      SQL_OUT=$(PGPASSWORD="$PG_TOKEN" psql "$PG_CONN" \
        -v ON_ERROR_STOP=0 \
        -c "SET search_path TO ${APP_NAME};" \
        -f "$SCHEMA_SQL" \
        2>&1 || true)
      if echo "$SQL_OUT" | grep -qi "FATAL\|error:"; then
        warn "schema.sql could not be applied — connection issue (see above)"
      else
        echo "$SQL_OUT" | grep -v "^$" | grep -v "^NOTICE" | grep -v "already exists" || true
        ok "schema.sql applied"
      fi
    else
      warn "schema.sql not found at ${SCHEMA_SQL} — tables will be auto-created by the app on first start"
    fi

    # ── Seed data ────────────────────────────────────────────────────────────
    # Auto-seed when demo-mode is on; can be forced with --seed true|false
    if [[ -z "$SEED_DATA" ]]; then
      [[ "$DEMO_MODE" == "true" ]] && SEED_DATA="true" || SEED_DATA="false"
    fi

    SEED_SQL="${SCRIPT_DIR}/../../schema/seed.sql"
    if [[ "$SEED_DATA" == "true" ]]; then
      if [[ -f "$SEED_SQL" ]]; then
        info "Applying seed data (schema/seed.sql)..."
        PGPASSWORD="$PG_TOKEN" psql "$PG_CONN" \
          -v ON_ERROR_STOP=0 \
          -c "SET search_path TO ${APP_NAME};" \
          -f "$SEED_SQL" \
          2>&1 | grep -v "^$" | grep -v "^NOTICE" | grep -v "already exists" || true
        ok "Seed data applied — demo products + users loaded"
      else
        warn "seed.sql not found at ${SEED_SQL} — skipping seed"
      fi
    else
      info "Seed data skipped (production mode). Pass --seed true to load demo data."
    fi

    # Step 2: Create the SP OAuth role in Lakebase (required before app can authenticate)
    # Lakebase uses LAKEBASE_OAUTH_V1 auth — the SP role must be pre-registered via the API,
    # not via psql CREATE ROLE (which creates a native password role that won't accept OAuth tokens).
    info "Registering SP as OAuth role in Lakebase..."
    EXISTING_LAKEBASE_ROLE=$(databricks postgres list-roles \
      "projects/${LAKEBASE_PROJECT}/branches/${BRANCH_NAME}" \
      --profile "$PROFILE" -o json 2>/dev/null \
      | python3 -c "
import sys, json
try:
    roles = json.load(sys.stdin)
    match = next((r for r in roles if r.get('status',{}).get('postgres_role','') == '${SP_UUID}'), None)
    if match:
        method = match.get('status',{}).get('auth_method','')
        print(method)
    else:
        print('')
except: print('')
" 2>/dev/null || true)

    if [[ "$EXISTING_LAKEBASE_ROLE" == "LAKEBASE_OAUTH_V1" ]]; then
      ok "SP OAuth role already registered in Lakebase."
    else
      if [[ -n "$EXISTING_LAKEBASE_ROLE" ]]; then
        # Wrong auth method — find and delete the existing role first
        WRONG_ROLE_NAME=$(databricks postgres list-roles \
          "projects/${LAKEBASE_PROJECT}/branches/${BRANCH_NAME}" \
          --profile "$PROFILE" -o json 2>/dev/null \
          | python3 -c "
import sys, json
try:
    roles = json.load(sys.stdin)
    match = next((r for r in roles if r.get('status',{}).get('postgres_role','') == '${SP_UUID}'), None)
    print(match.get('name','') if match else '')
except: print('')
" 2>/dev/null || true)
        [[ -n "$WRONG_ROLE_NAME" ]] && \
          databricks postgres delete-role "$WRONG_ROLE_NAME" --profile "$PROFILE" 2>/dev/null || true
        # Also clean up the manually-created postgres role if it exists
        PGPASSWORD="$PG_TOKEN" psql "$PG_CONN" \
          -c "REVOKE ALL ON ALL TABLES IN SCHEMA ${APP_NAME} FROM \"${SP_UUID}\"; \
              REVOKE ALL ON ALL SEQUENCES IN SCHEMA ${APP_NAME} FROM \"${SP_UUID}\"; \
              REVOKE ALL ON SCHEMA ${APP_NAME} FROM \"${SP_UUID}\"; \
              DROP ROLE IF EXISTS \"${SP_UUID}\";" \
          2>/dev/null || true
      fi

      CREATE_ROLE_OUT=$(databricks postgres create-role \
        "projects/${LAKEBASE_PROJECT}/branches/${BRANCH_NAME}" \
        --json "{\"spec\": {\"identity_type\": \"SERVICE_PRINCIPAL\", \"postgres_role\": \"${SP_UUID}\"}}" \
        --profile "$PROFILE" -o json 2>&1 || true)

      if echo "$CREATE_ROLE_OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',{}).get('auth_method',''))" 2>/dev/null | grep -q "LAKEBASE_OAUTH_V1"; then
        ok "SP OAuth role created in Lakebase"
      else
        warn "Could not create SP OAuth role: ${CREATE_ROLE_OUT:0:150}"
        warn "App may fall back to demo mode. Re-run deploy to retry."
      fi
    fi

    # Step 3: Grant the SP schema access
    GRANT_OUT=$(PGPASSWORD="$PG_TOKEN" psql \
      "host=${LAKEBASE_HOST} port=5432 dbname=databricks_postgres sslmode=require user=${DATABRICKS_USER:-${ADMIN_EMAIL}}" \
      -c "
        GRANT CONNECT ON DATABASE databricks_postgres TO \"${SP_UUID}\";
        GRANT USAGE  ON SCHEMA ${APP_NAME} TO \"${SP_UUID}\";
        GRANT CREATE ON SCHEMA ${APP_NAME} TO \"${SP_UUID}\";
        GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA ${APP_NAME} TO \"${SP_UUID}\";
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ${APP_NAME} TO \"${SP_UUID}\";
        ALTER DEFAULT PRIVILEGES IN SCHEMA ${APP_NAME} GRANT ALL ON TABLES    TO \"${SP_UUID}\";
        ALTER DEFAULT PRIVILEGES IN SCHEMA ${APP_NAME} GRANT ALL ON SEQUENCES TO \"${SP_UUID}\";
      " 2>&1 || true)

    if echo "$GRANT_OUT" | grep -qi "FATAL\|error:"; then
      warn "SP grants failed:"
      echo "$GRANT_OUT" | grep -i "FATAL\|error:" | head -3
    else
      ok "Schema grants applied to SP"
    fi

    # Step 4: Restart app with role + grants in place
    info "Restarting app..."
    databricks apps deploy "$APP_NAME" \
      --source-code-path "$WORKSPACE_PATH" \
      --profile "$PROFILE" 2>&1 | tail -3
    ok "App restarted"
  fi
fi

# ── Warehouse SP permission ───────────────────────────────────────────────────
step 8 "Granting SQL Warehouse 'Can use' to app service principal"

# Auto-detect warehouse if not provided
if [[ -z "$WAREHOUSE_ID" ]]; then
  info "No --warehouse-id provided — auto-detecting..."
  WAREHOUSE_ID=$(databricks warehouses list --profile "$PROFILE" -o json 2>/dev/null \
    | python3 -c "
import sys, json

data = json.load(sys.stdin)
warehouses = data if isinstance(data, list) else data.get('warehouses', data.get('items', []))

def score(w):
    name  = (w.get('name') or '').lower()
    state = (w.get('state') or '').upper()
    wtype = (w.get('warehouse_type') or '').upper()
    s = 0
    if state == 'RUNNING':   s += 10
    if 'starter' in name:    s += 4
    if 'serverless' in name: s += 3
    if wtype == 'PRO':       s += 2
    return s

best = sorted(warehouses, key=score, reverse=True)
if best:
    w = best[0]
    print(w.get('id',''))
    import sys
    print(f'  Selected: {w.get(\"name\")} ({w.get(\"warehouse_type\")}, {w.get(\"state\")})', file=sys.stderr)
" 2>/tmp/wh_detect_log.txt || true)
  [[ -f /tmp/wh_detect_log.txt ]] && cat /tmp/wh_detect_log.txt >&2 || true
  if [[ -n "$WAREHOUSE_ID" ]]; then
    ok "Auto-detected warehouse: ${WAREHOUSE_ID}"
    info "Pass --warehouse-id ${WAREHOUSE_ID} to skip detection on future runs."
  else
    warn "Could not auto-detect a SQL Warehouse. UC GRANTs won't execute until one is set."
    warn "After deploy: Manage → Settings → SQL Warehouse ID"
  fi
fi

if [[ -z "$WAREHOUSE_ID" ]]; then
  : # skip silently — warned above
elif [[ -z "$SP_UUID" ]]; then
  warn "SP UUID not detected — skipping warehouse grant. Grant manually in the UI."
else
  WAREHOUSE_PERM_PAYLOAD="{\"access_control_list\":[{\"service_principal_name\":\"${SP_UUID}\",\"permission_level\":\"CAN_USE\"}]}"
  WAREHOUSE_PERM_RESULT=$(databricks api patch "/api/2.0/permissions/warehouses/${WAREHOUSE_ID}" \
    --profile "$PROFILE" \
    --json "$WAREHOUSE_PERM_PAYLOAD" 2>&1 || echo "error")

  if echo "$WAREHOUSE_PERM_RESULT" | grep -qi "error\|Error\|INTERNAL"; then
    warn "Warehouse permission grant returned a warning (may already be set or partial):"
    echo "$WAREHOUSE_PERM_RESULT" | head -3
  else
    ok "SP '${SP_UUID}' granted CAN_USE on warehouse ${WAREHOUSE_ID}"
  fi
fi

# ── UC Catalog / Schema grants ────────────────────────────────────────────────
step 9 "Granting SP USE CATALOG + USE SCHEMA on all Unity Catalog catalogs"

if [[ "$GRANT_CATALOGS" != "true" ]]; then
  warn "UC catalog grants skipped (--grant-catalogs false)."
elif [[ -z "$SP_UUID" ]]; then
  warn "SP UUID not detected — skipping UC grants. Run the SQL below manually:"
  echo "  GRANT USE CATALOG ON CATALOG <catalog> TO \`<sp-uuid>\`;"
elif [[ -z "$WAREHOUSE_ID" ]]; then
  warn "No warehouse ID available — cannot execute UC GRANTs. Pass --warehouse-id to automate."
else
  info "Listing UC catalogs visible to this profile..."

  CATALOGS=$(databricks api get "/api/2.1/unity-catalog/catalogs" \
    --profile "$PROFILE" 2>/dev/null \
    | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    cats = [c.get('name','') for c in d.get('catalogs',[])
            if c.get('name','') not in ('system','__databricks_internal','hive_metastore')]
    print(' '.join(cats))
except: print('')
" 2>/dev/null || true)

  if [[ -z "$CATALOGS" ]]; then
    warn "No catalogs found or insufficient permissions to list catalogs."
  else
    info "Found catalogs: ${CATALOGS}"
    GRANT_ERRORS=0
    for CATALOG in $CATALOGS; do
      # USE CATALOG — required to enter the catalog
      GRANT_RESULT=$(databricks api post "/api/2.0/sql/statements" \
        --profile "$PROFILE" \
        --json "{\"warehouse_id\":\"${WAREHOUSE_ID}\",\"statement\":\"GRANT USE CATALOG ON CATALOG \`${CATALOG}\` TO \`${SP_UUID}\`\",\"wait_timeout\":\"10s\"}" \
        2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',{}).get('state','UNKNOWN'))" 2>/dev/null || echo "ERROR")

      # USE SCHEMA ON CATALOG — cascades USE SCHEMA to all current and future schemas.
      # Required for the SP to enumerate schemas and tables via the UC REST API.
      databricks api post "/api/2.0/sql/statements" \
        --profile "$PROFILE" \
        --json "{\"warehouse_id\":\"${WAREHOUSE_ID}\",\"statement\":\"GRANT USE SCHEMA ON CATALOG \`${CATALOG}\` TO \`${SP_UUID}\`\",\"wait_timeout\":\"10s\"}" \
        2>/dev/null >/dev/null || true

      # SELECT ON CATALOG — cascades read access to all current and future schemas/tables.
      SELECT_RESULT=$(databricks api post "/api/2.0/sql/statements" \
        --profile "$PROFILE" \
        --json "{\"warehouse_id\":\"${WAREHOUSE_ID}\",\"statement\":\"GRANT SELECT ON CATALOG \`${CATALOG}\` TO \`${SP_UUID}\`\",\"wait_timeout\":\"10s\"}" \
        2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',{}).get('state','UNKNOWN'))" 2>/dev/null || echo "ERROR")

      if [[ "$GRANT_RESULT" == "SUCCEEDED" && "$SELECT_RESULT" == "SUCCEEDED" ]]; then
        ok "  ✓ ${CATALOG} — USE CATALOG + USE SCHEMA + SELECT granted (covers all schemas, now and future)"
      elif [[ "$GRANT_RESULT" == "SUCCEEDED" ]]; then
        ok "  ✓ ${CATALOG} — USE CATALOG granted"
        warn "  ⚠ ${CATALOG} — SELECT grant failed (catalog may be owned by another user — run manually)"
      else
        warn "  ⚠ ${CATALOG} — grant failed. Use the onboarding wizard to generate the correct SQL."
        GRANT_ERRORS=$((GRANT_ERRORS + 1))
      fi
    done
    [[ $GRANT_ERRORS -eq 0 ]] && ok "UC catalog grants complete" || warn "${GRANT_ERRORS} catalog(s) could not be granted — the onboarding wizard will show the exact SQL to run."
  fi
fi

# ── Resource tagging for spend/consumption observability ─────────────────────
step 10 "Tagging Databricks resources for spend observability"

TAGS_JSON="{\"app\":\"datamarket\",\"purpose\":\"data_marketplace\",\"environment\":\"${DEMO_MODE_FLAG:-production}\"}"

# Tag the Databricks App
APP_TAG_RESULT=$(databricks api patch "/api/2.0/apps/${APP_NAME}" \
  --profile "$PROFILE" \
  --json "{\"custom_tags\":${TAGS_JSON}}" 2>&1 || echo "error")
if echo "$APP_TAG_RESULT" | grep -qi "error\|INTERNAL"; then
  warn "App tagging skipped (API may not support PATCH custom_tags in this workspace version)"
else
  ok "App tagged: app=datamarket, purpose=data_marketplace"
fi

# Tag the SQL Warehouse
if [[ -n "$WAREHOUSE_ID" ]]; then
  WH_TAGS_PAYLOAD="{\"tags\":{\"custom_tags\":[{\"key\":\"app\",\"value\":\"datamarket\"},{\"key\":\"purpose\",\"value\":\"data_marketplace\"},{\"key\":\"environment\",\"value\":\"${DEMO_MODE_FLAG:-production}\"}]}}"
  WH_TAG_RESULT=$(databricks api post "/api/2.0/sql/warehouses/${WAREHOUSE_ID}/edit" \
    --profile "$PROFILE" \
    --json "$WH_TAGS_PAYLOAD" 2>&1 || echo "error")
  if echo "$WH_TAG_RESULT" | grep -qi "error\|INTERNAL"; then
    warn "Warehouse tagging skipped — apply manually in SQL Warehouse settings"
    info "  Tag key: app, value: datamarket"
  else
    ok "Warehouse ${WAREHOUSE_ID} tagged: app=datamarket"
  fi
else
  info "No warehouse ID — warehouse tagging skipped"
fi

info "Tags flow into system.billing.usage under the custom_tags column."
info "Note: Lakebase custom_tags are UI-only (CLI API does not expose the field yet)."
info "  → Workspace → Lakebase → ${APP_NAME} → Settings → Custom tags → add app=datamarket"
info "Note: FMAPI (Ask AI) usage has no taggable resource — filter by sku_name instead."
info "Full DataMarket spend query:"
cat <<'QUERY'

  -- Full DataMarket spend across all resource types
  SELECT usage_date,
         usage_type,
         CASE
           WHEN custom_tags['app'] = 'datamarket'           THEN 'App / Warehouse'
           WHEN sku_name LIKE '%LAKEBASE%'                  THEN 'Lakebase (Postgres)'
           WHEN sku_name LIKE '%FOUNDATION_MODEL%'
             OR sku_name LIKE '%LLAMA%'
             OR sku_name LIKE '%PREMIUM_SERVING%'           THEN 'Ask AI (FMAPI)'
           ELSE 'Other'
         END AS resource,
         SUM(usage_quantity) AS dbus
  FROM system.billing.usage
  WHERE (custom_tags['app'] = 'datamarket'
      OR sku_name LIKE '%LAKEBASE%'
      OR sku_name LIKE '%FOUNDATION_MODEL%'
      OR sku_name LIKE '%PREMIUM_SERVING%')
  GROUP BY 1, 2, 3
  ORDER BY 1 DESC, dbus DESC;

QUERY


APP_URL=$(databricks apps get "$APP_NAME" --profile "$PROFILE" --output json 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('url',''))" 2>/dev/null || true)

echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  DataMarket is live!${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
if [[ -n "$APP_URL" ]]; then
  echo -e "  ${BOLD}URL:${NC}   $APP_URL"
fi
echo -e "  ${BOLD}Admin:${NC} $ADMIN_EMAIL"
echo ""
echo -e "  ${YELLOW}Next steps in the app (2 minutes):${NC}"
echo -e "  1. Open the URL and log in"
echo -e "  2. Click Manage → Data Products → Import from UC"
if [[ -z "$WAREHOUSE_ID" ]]; then
  echo -e "  3. Click Manage → Settings → set your SQL Warehouse ID"
  echo -e "     Then: SQL Warehouses → your warehouse → Permissions → add app SP with 'Can use'"
else
  echo -e "  3. Warehouse permission already granted ✓"
fi
echo ""
