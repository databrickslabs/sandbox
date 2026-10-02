import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import path from 'path';
import { fileURLToPath } from 'url';

import { getPool, runMigrations, closePool, LAKEBASE_HOST, LAKEBASE_DB, LAKEBASE_SCHEMA, DEMO_MODE, RFA_ENABLED, SQL_WAREHOUSE_ID } from './db.js';
import { registerRoutes as registerConfig }          from './routes/config.js';
import { registerRoutes as registerProducts, maybeAutoDiscover } from './routes/products.js';
import { registerRoutes as registerRequests }        from './routes/requests.js';
import { registerRoutes as registerUsers }           from './routes/users.js';
import { registerRoutes as registerFeatureRequests } from './routes/feature-requests.js';
import { registerRoutes as registerAskCatalog }      from './routes/ask-catalog.js';
import { registerRoutes as registerInsights }        from './routes/insights.js';
import { registerRoutes as registerDemo }            from './routes/demo.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = path.dirname(__filename);

const app  = express();
const PORT = process.env.DATABRICKS_APP_PORT || process.env.PORT || 3000;

// ─── Middleware ───────────────────────────────────────────────────────────────
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc:  ["'self'", "'unsafe-inline'"],
      styleSrc:   ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
      fontSrc:    ["'self'", "https://fonts.gstatic.com"],
      connectSrc: ["'self'", "https://*.azuredatabricks.net"],
      imgSrc:     ["'self'", "data:", "https:"],
    },
  },
}));
app.use(compression());
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'dist')));
app.use('/public', express.static(path.join(__dirname, 'public')));

// ─── Routes ───────────────────────────────────────────────────────────────────
registerConfig(app);
registerProducts(app);
registerRequests(app);
registerUsers(app);
registerFeatureRequests(app);
registerAskCatalog(app);
registerInsights(app);
registerDemo(app);

// ─── SPA fallback ─────────────────────────────────────────────────────────────
app.get('*', (req, res) => {
  if (req.path.startsWith('/api/')) return res.status(404).json({ error: 'Not found' });
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

// ─── Startup ──────────────────────────────────────────────────────────────────
const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 DataMarket running on 0.0.0.0:${PORT}`);
  console.log(`🗄️  Lakebase: ${LAKEBASE_HOST}/${LAKEBASE_DB}/${LAKEBASE_SCHEMA}`);
  console.log(`🔧 Mode: ${DEMO_MODE ? 'DEMO (persona switcher, no real grants)' : 'PRODUCTION (SSO identity, UC grants enabled)'}`);
  console.log(`📡 RFA: ${RFA_ENABLED ? 'ENABLED' : 'disabled'} | UC Grants: ${!DEMO_MODE && SQL_WAREHOUSE_ID ? 'ENABLED' : 'disabled'}`);
  console.log(`📊 Health: http://localhost:${PORT}/api/health`);
  getPool()
    .then(() => {
      console.log('✅ Lakebase pool initialized');
      // Retry migrations — Autoscaling Lakebase may need a moment to wake from idle
      const tryMigrate = (attempt) => runMigrations().catch(e => {
        if (attempt < 5) {
          console.warn(`⚠️  Migration attempt ${attempt} failed (${e.message}) — retrying in 8s...`);
          setTimeout(() => tryMigrate(attempt + 1), 8000);
        } else {
          console.warn('⚠️  Migrations skipped after 5 attempts:', e.message);
        }
      });
      tryMigrate(1);
      // Run auto-discover after migrations settle (non-blocking)
      setTimeout(() => maybeAutoDiscover(), 15000);
    })
    .catch(e => console.warn('⚠️  Lakebase init deferred:', e.message));
});

process.on('SIGTERM', () => {
  console.log('Received SIGTERM, shutting down...');
  server.close(async () => {
    await closePool();
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 14000);
});
