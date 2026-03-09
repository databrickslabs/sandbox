/**
 * Express proxy server for Multi-Agent Registry Webapp
 *
 * This server:
 * 1. Serves the built React app from /dist
 * 2. Proxies /api/* requests to the registry-api with authentication
 * 3. Handles /supervisor/* requests if configured
 */

import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = process.env.PORT || 8000;

// Registry API URL (from environment or default)
const REGISTRY_API_URL = process.env.REGISTRY_API_URL || 'https://registry-api-7474660127789418.aws.databricksapps.com';

console.log(`[CONFIG] Registry API URL: ${REGISTRY_API_URL}`);
console.log(`[CONFIG] Port: ${PORT}`);

// OAuth token cache
let cachedToken = null;
let tokenExpiry = 0;

// Get OAuth access token using service principal credentials
async function getAccessToken() {
  // Return cached token if still valid (with 5-minute buffer)
  if (cachedToken && Date.now() < tokenExpiry - 300000) {
    return cachedToken;
  }

  const clientId = process.env.DATABRICKS_CLIENT_ID;
  const clientSecret = process.env.DATABRICKS_CLIENT_SECRET;
  const host = process.env.DATABRICKS_HOST;

  if (!clientId || !clientSecret || !host) {
    console.error('[AUTH] Missing OAuth credentials');
    return null;
  }

  try {
    const tokenUrl = `https://${host}/oidc/v1/token`;
    const response = await fetch(tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        grant_type: 'client_credentials',
        client_id: clientId,
        client_secret: clientSecret,
        scope: 'all-apis'
      })
    });

    if (!response.ok) {
      console.error(`[AUTH] Token request failed: ${response.status}`);
      return null;
    }

    const data = await response.json();
    cachedToken = data.access_token;
    tokenExpiry = Date.now() + (data.expires_in * 1000);
    console.log(`[AUTH] Got access token, expires in ${data.expires_in} seconds`);
    return cachedToken;
  } catch (error) {
    console.error(`[AUTH] Error getting token: ${error.message}`);
    return null;
  }
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'multi-agent-registry-webapp',
    timestamp: new Date().toISOString()
  });
});

// Debug endpoint to check available env vars
app.get('/debug/env', (req, res) => {
  const envVars = {
    DATABRICKS_HOST: process.env.DATABRICKS_HOST || 'not set',
    DATABRICKS_CLIENT_ID: process.env.DATABRICKS_CLIENT_ID ? 'present' : 'not set',
    DATABRICKS_CLIENT_SECRET: process.env.DATABRICKS_CLIENT_SECRET ? 'present' : 'not set',
    DATABRICKS_TOKEN: process.env.DATABRICKS_TOKEN ? 'present' : 'not set',
    PORT: process.env.PORT,
    REGISTRY_API_URL: process.env.REGISTRY_API_URL
  };
  res.json(envVars);
});

// Middleware to add OAuth token to requests before proxying
app.use('/api', async (req, res, next) => {
  try {
    const token = await getAccessToken();
    if (token) {
      req.headers['x-databricks-token'] = token;
      console.log('[AUTH] Added OAuth token to request');
    } else {
      console.error('[AUTH] Failed to get OAuth token');
    }
  } catch (error) {
    console.error(`[AUTH] Error getting token: ${error.message}`);
  }
  next();
});

// Proxy /api requests to registry-api
// This forwards all /api/* requests to the registry-api with proper headers
app.use('/api', createProxyMiddleware({
  target: REGISTRY_API_URL,
  changeOrigin: true,
  secure: true,
  logLevel: 'info',
  onProxyReq: (proxyReq, req, res) => {
    console.log(`[PROXY] ${req.method} ${req.url} -> ${REGISTRY_API_URL}${req.url}`);

    // Use the token added by the middleware
    const token = req.headers['x-databricks-token'];
    if (token) {
      proxyReq.setHeader('Authorization', `Bearer ${token}`);
      console.log('[PROXY] Added OAuth token to proxy request');
    } else {
      console.error('[PROXY] No auth token available');
    }
  },
  onProxyRes: (proxyRes, req, res) => {
    console.log(`[PROXY] Response: ${proxyRes.statusCode} for ${req.url}`);
  },
  onError: (err, req, res) => {
    console.error(`[PROXY ERROR] ${err.message}`);
    res.status(500).json({
      error: 'Proxy error',
      message: 'Failed to connect to registry API',
      details: err.message
    });
  }
}));

// Serve static files from dist directory
const distPath = join(__dirname, 'dist');
app.use(express.static(distPath));

// SPA fallback - serve index.html for all other routes not handled above
// Using a catch-all pattern that works with newer Express/path-to-regexp
app.use((req, res) => {
  res.sendFile(join(distPath, 'index.html'));
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`[SERVER] Multi-Agent Registry Webapp running on http://0.0.0.0:${PORT}`);
  console.log(`[SERVER] Proxying /api/* to ${REGISTRY_API_URL}`);
  console.log(`[SERVER] Serving static files from ${distPath}`);
});
