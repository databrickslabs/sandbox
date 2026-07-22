import https from 'https';

export function getDatabricksHost() {
  return (process.env.DATABRICKS_HOST || '').replace(/^https?:\/\//, '');
}

export function isPat(token) {
  return typeof token === 'string' && token.startsWith('dapi');
}

export function httpsJsonRequest({ hostname, path, method = 'GET', headers = {}, body = null, timeoutMs = 12000 }) {
  return new Promise((resolve, reject) => {
    const req = https.request({ hostname, path, method, headers }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: data ? JSON.parse(data) : {} });
        } catch (_) {
          reject(new Error(`Bad JSON response from ${path}`));
        }
      });
    });
    req.setTimeout(timeoutMs, () => {
      req.destroy(new Error(`Request to ${path} timed out after ${timeoutMs}ms`));
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

export async function fetchM2MToken() {
  const clientId = process.env.DATABRICKS_CLIENT_ID || '';
  const clientSecret = process.env.DATABRICKS_CLIENT_SECRET || '';
  const host = getDatabricksHost();
  if (!clientId || !clientSecret || !host) {
    throw new Error('DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET, and DATABRICKS_HOST are required');
  }
  const body = 'grant_type=client_credentials&scope=all-apis';
  const { status, data } = await httpsJsonRequest({
    hostname: host,
    path: '/oidc/v1/token',
    method: 'POST',
    headers: {
      Authorization: `Basic ${Buffer.from(`${clientId}:${clientSecret}`).toString('base64')}`,
      'Content-Type': 'application/x-www-form-urlencoded',
      'Content-Length': Buffer.byteLength(body),
    },
    body,
  });
  if (status !== 200 || !data.access_token) {
    throw new Error(`OAuth token request failed (${status}): ${JSON.stringify(data)}`);
  }
  return data.access_token;
}

// Workspace auth for Databricks REST APIs (UC import, SQL, RFA).
export async function getWorkspaceOAuthToken() {
  const envToken = process.env.DATABRICKS_TOKEN || process.env.DATABRICKS_RUNTIME_TOKEN || '';
  if (envToken && !isPat(envToken)) return envToken;

  const apiPat = process.env.DATABRICKS_API_TOKEN || (isPat(envToken) ? envToken : '');
  if (apiPat) return apiPat;

  return fetchM2MToken();
}

export async function generateProvisionedDbCredential(oauthToken) {
  const LAKEBASE_INSTANCE_NAME = process.env.LAKEBASE_INSTANCE_NAME || '';
  const host = getDatabricksHost();
  const payload = JSON.stringify({
    instance_names: [LAKEBASE_INSTANCE_NAME],
    request_id: `dm-${Date.now()}`,
  });
  const { status, data } = await httpsJsonRequest({
    hostname: host,
    path: '/api/2.0/database/credentials',
    method: 'POST',
    headers: {
      Authorization: `Bearer ${oauthToken}`,
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload),
    },
    body: payload,
  });
  if (!data.token) {
    throw new Error(`DB credential generation failed (${status}): ${JSON.stringify(data)}`);
  }
  return data.token;
}

export async function generateAutoscaleDbCredential(oauthToken, endpoint) {
  const host = getDatabricksHost();
  const payload = JSON.stringify({ endpoint });
  const { status, data } = await httpsJsonRequest({
    hostname: host,
    path: '/api/2.0/postgres/credentials',
    method: 'POST',
    headers: {
      Authorization: `Bearer ${oauthToken}`,
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(payload),
    },
    body: payload,
  });
  if (!data.token) {
    throw new Error(`Autoscale DB credential failed (${status}): ${JSON.stringify(data)}`);
  }
  return data.token;
}

export async function resolveAutoscaleLakebaseAuth() {
  const LAKEBASE_ENDPOINT = process.env.LAKEBASE_ENDPOINT || '';
  const userToken = process.env.DATABRICKS_TOKEN || process.env.DATABRICKS_RUNTIME_TOKEN
    || process.env.LAKEBASE_PASSWORD || '';

  // Legacy/user path: OAuth JWT used directly as Postgres password (local deploy + some Apps).
  if (userToken && !isPat(userToken) && !LAKEBASE_ENDPOINT) {
    const pgUser = process.env.LAKEBASE_PGUSER || process.env.DATABRICKS_USER;
    if (!pgUser) throw new Error('DATABRICKS_USER env var is required');
    return { pgPassword: userToken, pgUser, mode: 'Autoscaling (user OAuth token)' };
  }

  if (isPat(userToken)) {
    throw new Error(
      'A PAT cannot be used as the Lakebase Postgres password. ' +
      'Remove DATABRICKS_TOKEN from app.yaml (use DATABRICKS_API_TOKEN for UC Import via --pat).'
    );
  }

  const endpoint = LAKEBASE_ENDPOINT;
  if (!endpoint) {
    throw new Error(
      'LAKEBASE_ENDPOINT is required for Lakebase Autoscaling in Databricks Apps. ' +
      'Find it with: databricks postgres list-endpoints projects/<project>/branches/production ' +
      '— then redeploy with --lakebase-endpoint.'
    );
  }

  const oauthToken = await fetchM2MToken();
  const pgPassword = await generateAutoscaleDbCredential(oauthToken, endpoint);
  // Apps connect as the app service principal (UUID). deploy.sh creates this Postgres role + schema grants.
  const pgUser = process.env.LAKEBASE_PGUSER
    || process.env.DATABRICKS_CLIENT_ID
    || process.env.DATABRICKS_USER;
  if (!pgUser) {
    throw new Error('LAKEBASE_PGUSER, DATABRICKS_CLIENT_ID, or DATABRICKS_USER is required');
  }
  return { pgPassword, pgUser, mode: `Autoscaling (Apps SP ${pgUser.slice(0, 8)}… + credential API)` };
}
