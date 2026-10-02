import {
  query,
  getProductCols,
  resetProductColsCache,
  loadSettings,
  getSetting,
} from '../db.js';
import {
  fetchUcSchema,
  ucApiRequest,
  getUcAuth,
  databricksApi,
} from '../databricks.js';

// ─── Simple TTL cache for schema + preview (avoids hammering UC on every page load) ──
const _cache = new Map();
function cacheGet(key) {
  const entry = _cache.get(key);
  if (!entry) return null;
  if (Date.now() > entry.expiresAt) { _cache.delete(key); return null; }
  return entry.value;
}
function cacheSet(key, value, ttlMs) {
  _cache.set(key, { value, expiresAt: Date.now() + ttlMs });
}
function cacheClear(prefix = '') {
  if (!prefix) { _cache.clear(); return; }
  for (const k of _cache.keys()) { if (k.startsWith(prefix)) _cache.delete(k); }
}

// ─── Background auto-discover (runs once after startup if enabled) ────────────
export async function maybeAutoDiscover() {
  try {
    await loadSettings();
    if (getSetting('auto_discover_enabled', 'false') !== 'true') return;
    const prefix = getSetting('auto_discover_prefix', '');
    if (!prefix) return;
    const parts = prefix.split('.');
    if (parts.length < 2) return;
    const [catalog, schema] = parts;
    const { host, token } = await getUcAuth();
    const listData = await ucApiRequest(host, token,
      `/api/2.0/unity-catalog/tables?catalog_name=${encodeURIComponent(catalog)}&schema_name=${encodeURIComponent(schema)}&max_results=200`);
    const ucTables = (listData?.tables || []).filter(t =>
      parts[2] ? t.name?.toLowerCase().startsWith(parts[2].toLowerCase()) : true);
    const { rows: existing } = await query(`SELECT uc_full_name FROM data_products WHERE uc_full_name IS NOT NULL`);
    const existingSet = new Set(existing.map(r => r.uc_full_name.toLowerCase()));
    const newTables = ucTables.filter(t => !existingSet.has(`${catalog}.${schema}.${t.name}`.toLowerCase()));
    if (!newTables.length) return;
    const { rows: [maxRow] } = await query(`SELECT MAX(CAST(SUBSTRING(product_ref FROM 4) AS INTEGER)) AS max_id FROM data_products`);
    let nextId = (maxRow.max_id || 0) + 1;
    for (const t of newTables) {
      const fullName = `${catalog}.${schema}.${t.name}`;
      const ref = `DP-${String(nextId++).padStart(3, '0')}`;
      const displayName = t.name.replace(/_/g, ' ').replace(/\bgold\b/i, '').trim().replace(/\b\w/g, c => c.toUpperCase());
      await query(
        `INSERT INTO data_products (product_ref, display_name, description, type, domain, tags, source_system, refresh_frequency, owner_email, classification, uc_full_name, is_active, status, last_refreshed)
         VALUES ($1,$2,$3,'Dataset','Other','{}','Unity Catalog','Daily','','Internal',$4,FALSE,'Draft',NOW())
         ON CONFLICT (product_ref) DO NOTHING`,
        [ref, displayName, `Auto-discovered from Unity Catalog: ${fullName}`, fullName]);
    }
    console.log(`[auto-discover] Drafted ${newTables.length} new table(s) from ${prefix}`);
  } catch (e) {
    console.warn('[auto-discover] Non-fatal:', e.message);
  }
}

export function registerRoutes(app) {
  // ─── Data Products ────────────────────────────────────────────────────────────
  app.get('/api/portal/products', async (req, res) => {
    try {
      const { domain, type, q, includeAll } = req.query;
      const cols = await getProductCols();

      // Build SELECT — only include optional columns if they exist in this schema
      const optionalCols = [
        cols.has('source_type')  ? "COALESCE(source_type, source_system, 'Databricks') AS source_type"
                                 : "COALESCE(source_system,'Databricks') AS source_type",
        cols.has('product_url')  ? "COALESCE(product_url,'')  AS product_url"  : "'' AS product_url",
        cols.has('report_url')   ? "COALESCE(report_url,'')   AS report_url"   : "'' AS report_url",
      ].join(', ');

      let sql = `SELECT product_id, product_ref, uc_full_name, display_name, description, type, domain,
                        tags, source_system, refresh_frequency, owner_email, classification, is_active,
                        COALESCE(status,'Published') AS status, created_at, updated_at, last_refreshed,
                        ${optionalCols}
                 FROM data_products WHERE (is_active = TRUE OR COALESCE(status,'Published') = 'Pending')`;

      if (!includeAll) sql = sql.replace(
        "(is_active = TRUE OR COALESCE(status,'Published') = 'Pending')",
        "is_active = TRUE AND COALESCE(status,'Published') = 'Published'"
      );
      // When includeAll=true (admin view), remove all status/active filters — show everything
      if (includeAll) sql = sql.replace(
        "WHERE (is_active = TRUE OR COALESCE(status,'Published') = 'Pending')",
        'WHERE TRUE'
      );
      const params = [];
      if (domain) { params.push(domain); sql += ` AND domain = $${params.length}`; }
      if (type)   { params.push(type);   sql += ` AND type = $${params.length}`; }
      if (q)      { params.push(`%${q}%`); sql += ` AND (display_name ILIKE $${params.length} OR description ILIKE $${params.length})`; }
      sql += ' ORDER BY display_name';

      const { rows } = await query(sql, params);
      res.json(rows);
    } catch (e) {
      console.error('[/api/portal/products]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  // ─── Products debug ────────────────────────────────────────────────────────────
  app.get('/api/portal/products/debug', async (req, res) => {
    try {
      const cols = await getProductCols();
      const { rows: countRows } = await query('SELECT COUNT(*) as total FROM data_products');
      const { rows: sample } = await query(
        `SELECT product_ref, display_name, is_active, status FROM data_products LIMIT 5`
      );
      res.json({
        detected_optional_cols: [...cols],
        total_products: countRows[0]?.total,
        sample,
      });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.post('/api/portal/products', async (req, res) => {
    try {
      const { name, description, type, source, tags, refreshFrequency,
              ownerEmail, classification, ucFullName, domain, hasPII, submittedBy, productUrl } = req.body;
      if (!name || !description) return res.status(400).json({ error: 'name and description are required' });

      // Generate a sequential ref after current max
      const { rows: [maxRow] } = await query(
        `SELECT MAX(CAST(SUBSTRING(product_ref FROM 4) AS INTEGER)) AS max_id FROM data_products`
      );
      const nextId = (maxRow.max_id || 12) + 1;
      const productRef = `DP-${String(nextId).padStart(3, '0')}`;

      const tagsArr = Array.isArray(tags) ? tags : (tags ? tags.split(',').map(t => t.trim()) : []);

      const { rows: [product] } = await query(
        `INSERT INTO data_products
           (product_ref, display_name, description, type, source_system, tags,
            refresh_frequency, owner_email, classification, uc_full_name, domain, is_active, status, product_url)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,FALSE,'Pending',$12)
         RETURNING *`,
        [productRef, name, description, type || 'Dashboard', source || 'Other',
         tagsArr, refreshFrequency || 'Daily',
         ownerEmail || submittedBy || 'unknown@example.org',
         classification || 'Internal', ucFullName || '', domain || source || 'Other',
         productUrl || null]
      );

      // Best-effort audit log (non-fatal if table doesn't exist)
      try {
        await query(
          `INSERT INTO audit_log (event_type, actor_email, target_name, metadata)
           VALUES ('PRODUCT_SUBMITTED', $1, $2, $3)`,
          [submittedBy || ownerEmail || 'unknown', productRef, JSON.stringify({ name, productRef })]
        );
      } catch (_) {}

      res.status(201).json(product);
    } catch (e) {
      console.error('[POST /api/portal/products]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  // ─── Get pending products (for admin review) ──────────────────────────────────
  app.get('/api/portal/products/pending', async (req, res) => {
    try {
      const { rows } = await query(
        `SELECT * FROM data_products WHERE is_active = FALSE AND status = 'Pending' ORDER BY created_at DESC`
      );
      res.json(rows);
    } catch (e) {
      console.error('[/api/portal/products/pending]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  // ─── Publish product (admin approves, makes it live in catalog) ───────────────
  app.put('/api/portal/products/:ref/publish', async (req, res) => {
    try {
      const { ref } = req.params;
      const { reviewerEmail } = req.body;
      const { rows: [product] } = await query(
        `UPDATE data_products SET is_active = TRUE, status = 'Published', updated_at = NOW()
         WHERE product_ref = $1 RETURNING *`,
        [ref]
      );
      if (!product) return res.status(404).json({ error: 'Product not found' });

      try {
        await query(
          `INSERT INTO audit_log (event_type, actor_email, target_name, metadata)
           VALUES ('PRODUCT_PUBLISHED', $1, $2, $3)`,
          [reviewerEmail || 'admin', ref, JSON.stringify({ ref, name: product.display_name })]
        );
      } catch (_) {}
      res.json(product);
    } catch (e) {
      console.error('[PUT /api/portal/products/:ref/publish]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  // ─── Reject product registration ──────────────────────────────────────────────
  app.put('/api/portal/products/:ref/reject', async (req, res) => {
    try {
      const { ref } = req.params;
      const { reviewerEmail, reason } = req.body;
      const { rows: [product] } = await query(
        `UPDATE data_products SET status = 'Rejected', updated_at = NOW()
         WHERE product_ref = $1 RETURNING *`,
        [ref]
      );
      if (!product) return res.status(404).json({ error: 'Product not found' });

      try {
        await query(
          `INSERT INTO audit_log (event_type, actor_email, target_name, metadata)
           VALUES ('PRODUCT_REJECTED', $1, $2, $3)`,
          [reviewerEmail || 'admin', ref, JSON.stringify({ ref, reason })]
        );
      } catch (_) {}
      res.json(product);
    } catch (e) {
      console.error('[PUT /api/portal/products/:ref/reject]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  // ─── UC Schema — live column metadata with synthetic fallback ────────────────
  app.get('/api/portal/products/:ref/schema', async (req, res) => {
    try {
      const { ref } = req.params;

      // Serve from cache if available (5 min TTL)
      const cacheKey = `schema:${ref}`;
      const cached = cacheGet(cacheKey);
      if (cached) return res.json(cached);

      const { rows: [product] } = await query('SELECT uc_full_name, domain FROM data_products WHERE product_ref = $1', [ref]);
      if (!product) return res.status(404).json({ error: 'Product not found' });

      if (product.uc_full_name) {
        // ── Step 1: UC REST API first — fast (~300ms), no warehouse needed ──────
        let restColumns = [];
        let tableComment = '';
        try {
          const result = await databricksApi('GET', `/api/2.1/unity-catalog/tables/${product.uc_full_name}`);
          restColumns = result.data?.columns || [];
          tableComment = result.data?.comment || '';
        } catch (e) {
          console.warn('[schema] UC REST API failed:', e.message);
        }

        if (restColumns.length > 0) {
          const piiPatterns = /^(ssn|social_security|dob|date_of_birth|birth_date|email|phone|address|bank_account|credit_card|salary|compensation|wage)/i;
          const confPatterns = /^(cost_center|approver|budget_code|account_number|internal_id)/i;
          const columns = restColumns.map(col => {
            const name = col.name;
            const type = (col.type_text || col.type_name || 'STRING').toUpperCase();
            const description = col.comment || '';
            let sensitivity = 'INTERNAL';
            if (piiPatterns.test(name)) sensitivity = 'PII';
            else if (confPatterns.test(name)) sensitivity = 'CONFIDENTIAL';
            const masked = sensitivity === 'PII' || sensitivity === 'CONFIDENTIAL';
            const elevatedPII = sensitivity === 'PII' && /ssn|dob|date_of_birth|birth|bank|credit_card/i.test(name);
            return { name, type, description, sensitivity, masked, elevatedPII };
          });

          // ── Step 2: Optionally enrich with UC column tags if warehouse is ready ─
          // Only attempt if warehouse is configured — runs async enrichment, doesn't
          // block the response. For now return REST result immediately; tag enrichment
          // is a future enhancement (requires warehouse to be already warm).
          const warehouseId = getSetting('sql_warehouse_id', process.env.SQL_WAREHOUSE_ID || '');
          if (warehouseId) {
            // Try warehouse enrichment with a short timeout — don't block if cold
            const liveSchema = await Promise.race([
              fetchUcSchema(product.uc_full_name),
              new Promise(resolve => setTimeout(() => resolve(null), 3000)),
            ]);
            if (liveSchema) {
              const payload = { source: 'unity_catalog', uc_full_name: product.uc_full_name, columns: liveSchema, table_comment: tableComment };
              cacheSet(cacheKey, payload, 5 * 60 * 1000);
              return res.json(payload);
            }
          }

          const payload = { source: 'unity_catalog_rest', uc_full_name: product.uc_full_name, columns, table_comment: tableComment };
          cacheSet(cacheKey, payload, 5 * 60 * 1000);
          return res.json(payload);
        }
      }
      // Fall back to signal that frontend should use its synthetic schemas
      res.json({ source: 'synthetic', domain: product.domain, uc_full_name: product.uc_full_name || null });
    } catch (e) {
      console.error('[/api/portal/products/:ref/schema]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  // ─── UC Sample Data — live row preview ────────────────────────────────────────
  app.get('/api/portal/products/:ref/preview', async (req, res) => {
    try {
      const { ref } = req.params;

      // Serve from cache if available (10 min TTL)
      const cacheKey = `preview:${ref}`;
      const cached = cacheGet(cacheKey);
      if (cached) return res.json(cached);

      // Reload settings so a newly configured warehouse ID is picked up without restart
      await loadSettings();
      const warehouseId = getSetting('sql_warehouse_id', process.env.SQL_WAREHOUSE_ID || '');
      const { rows: [product] } = await query('SELECT uc_full_name FROM data_products WHERE product_ref = $1', [ref]);
      if (!product) return res.status(404).json({ error: 'Product not found' });
      if (!product.uc_full_name) return res.json({ source: 'synthetic', rows: [], columns: [] });
      if (!warehouseId) return res.json({ source: 'no_warehouse', rows: [], columns: [] });

      const result = await databricksApi('POST', '/api/2.0/sql/statements', {
        warehouse_id: warehouseId,
        statement: `SELECT * FROM ${product.uc_full_name} LIMIT 5`,
        wait_timeout: '15s'
      });

      if (result.data?.status?.state !== 'SUCCEEDED') {
        return res.json({ source: 'error', rows: [], columns: [], error: result.data?.status?.error?.message });
      }

      const schema = result.data.manifest?.schema?.columns || [];
      const columns = schema.map(c => c.name);
      const rows = result.data.result?.data_array || [];
      const payload = { source: 'unity_catalog', columns, rows };
      cacheSet(cacheKey, payload, 10 * 60 * 1000);
      res.json(payload);
    } catch (e) {
      console.error('[/api/portal/products/:ref/preview]', e.message);
      res.status(500).json({ source: 'error', rows: [], columns: [], error: e.message });
    }
  });

  // ─── Admin: Product inline update ─────────────────────────────────────────────
  app.delete('/api/portal/products/:ref', async (req, res) => {
    try {
      const { ref } = req.params;
      // Delete dependent rows first, then the product
      await query(`DELETE FROM access_requests WHERE product_id IN (SELECT product_id FROM data_products WHERE product_ref = $1)`, [ref]);
      await query(`DELETE FROM audit_log WHERE target_name = $1`, [ref]);
      const { rows: [deleted] } = await query(
        `DELETE FROM data_products WHERE product_ref = $1 RETURNING product_ref, display_name`, [ref]);
      if (!deleted) return res.status(404).json({ error: 'Product not found' });
      cacheClear(`schema:${ref}`);
      cacheClear(`preview:${ref}`);
      res.json({ deleted: true, ref: deleted.product_ref, name: deleted.display_name });
    } catch (e) {
      console.error('[DELETE /api/portal/products/:ref]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  app.put('/api/portal/products/:ref', async (req, res) => {
    try {
      const { ref } = req.params;
      const {
        uc_full_name, source_type, refresh_frequency, report_url, domain,
        description, display_name, owner_email, data_classification, tags
      } = req.body;
      const sets = [];
      const params = [];
      if (uc_full_name !== undefined)        { params.push(uc_full_name);          sets.push(`uc_full_name = $${params.length}`); }
      if (source_type !== undefined)         { params.push(source_type);            sets.push(`source_system = $${params.length}`); }
      if (refresh_frequency !== undefined)   { params.push(refresh_frequency);      sets.push(`refresh_frequency = $${params.length}`); }
      if (report_url !== undefined)          { params.push(report_url);             sets.push(`report_url = $${params.length}`); }
      if (domain !== undefined)              { params.push(domain);                 sets.push(`domain = $${params.length}`); }
      if (description !== undefined)         { params.push(description);            sets.push(`description = $${params.length}`); }
      if (display_name !== undefined)        { params.push(display_name);           sets.push(`display_name = $${params.length}`); }
      if (owner_email !== undefined)         { params.push(owner_email);            sets.push(`owner_email = $${params.length}`); }
      if (data_classification !== undefined) { params.push(data_classification);    sets.push(`data_classification = $${params.length}`); }
      if (tags !== undefined)                { params.push(tags);                  sets.push(`tags = $${params.length}`); }
      if (sets.length === 0) return res.status(400).json({ error: 'Nothing to update' });
      sets.push('updated_at = NOW()');
      params.push(ref);
      const { rows: [product] } = await query(
        `UPDATE data_products SET ${sets.join(', ')} WHERE product_ref = $${params.length} RETURNING *`, params);
      if (!product) return res.status(404).json({ error: 'Product not found' });
      res.json(product);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // ─── Admin: UC Catalog Browser ────────────────────────────────────────────────
  // Returns already-registered UC table names so the frontend can mark them.
  app.get('/api/portal/admin/uc-registered', async (req, res) => {
    try {
      const { rows } = await query(
        `SELECT uc_full_name FROM data_products WHERE uc_full_name IS NOT NULL AND uc_full_name != ''`);
      res.json({ names: rows.map(r => r.uc_full_name) });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // Local-dev proxy: forwards UC API calls as the SP (used when databricksHost isn't
  // available in the browser, e.g. running locally). Not used in Databricks Apps.
  app.get('/api/portal/admin/uc-proxy', async (req, res) => {
    try {
      const path = req.query.path;
      if (!path || !path.startsWith('/api/2.1/unity-catalog/')) {
        return res.status(400).json({ error: 'Invalid path' });
      }
      const { host, token } = await getUcAuth();
      const data = await ucApiRequest(host, token, path);
      res.json(data);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.get('/api/portal/admin/uc-catalogs', async (req, res) => {
    try {
      const { host, token } = await getUcAuth();
      const data = await ucApiRequest(host, token, '/api/2.1/unity-catalog/catalogs');
      const catalogs = (data.catalogs || []).map(c => ({ name: c.name, comment: c.comment }));
      res.json({ catalogs });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.get('/api/portal/admin/uc-schemas', async (req, res) => {
    try {
      const { catalog } = req.query;
      if (!catalog) return res.status(400).json({ error: 'catalog param required' });
      const { host, token } = await getUcAuth();
      const data = await ucApiRequest(host, token,
        `/api/2.1/unity-catalog/schemas?catalog_name=${encodeURIComponent(catalog)}`);
      const schemas = (data.schemas || [])
        .filter(s => s.name !== 'information_schema')
        .map(s => ({ name: s.name, full_name: s.full_name, comment: s.comment }));
      res.json({ schemas });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.get('/api/portal/admin/uc-tables-browse', async (req, res) => {
    try {
      const { catalog, schema } = req.query;
      if (!catalog || !schema) return res.status(400).json({ error: 'catalog and schema params required' });

      const { rows: existing } = await query(
        `SELECT uc_full_name FROM data_products WHERE uc_full_name IS NOT NULL AND uc_full_name != ''`);
      const registered = new Set(existing.map(r => r.uc_full_name));

      // Internal Databricks system table prefixes to exclude from the Import modal
      const INTERNAL_TABLE_PREFIXES = ['__materialization_mat_', '__apply_changes_', 'event_log_', '__dlt_'];
      const isInternalTable = name => INTERNAL_TABLE_PREFIXES.some(p => name.startsWith(p));

      let tables = [];

      const warehouseId = getSetting('sql_warehouse_id', '');
      if (warehouseId) {
        // Primary: query information_schema.tables — works with USE SCHEMA + USE CATALOG only
        try {
          const stmt = await databricksApi('POST', '/api/2.0/sql/statements', {
            warehouse_id: warehouseId,
            statement: `SELECT table_name, table_type FROM \`${catalog}\`.information_schema.tables WHERE table_schema = '${schema}' ORDER BY table_name`,
            wait_timeout: '15s',
          });
          if (stmt.data?.status?.state === 'SUCCEEDED') {
            const rows = stmt.data.result?.data_array || [];
            // rows: [table_name, table_type]
            tables = rows
              .filter(r => !isInternalTable(r[0]))
              .map(r => {
                const tName = r[0];
                const full = `${catalog}.${schema}.${tName}`;
                return { full_name: full, table_name: tName, schema_name: schema, catalog_name: catalog, table_type: r[1], registered: registered.has(full) };
              });
          }
        } catch (e) {
          console.warn('[uc-tables-browse] information_schema query failed:', e.message);
        }

        // Secondary: SHOW TABLES (requires SELECT on tables)
        if (tables.length === 0) {
          try {
            const stmt = await databricksApi('POST', '/api/2.0/sql/statements', {
              warehouse_id: warehouseId,
              statement: `SHOW TABLES IN \`${catalog}\`.\`${schema}\``,
              wait_timeout: '15s',
            });
            if (stmt.data?.status?.state === 'SUCCEEDED') {
              const rows = stmt.data.result?.data_array || [];
              tables = rows
                .filter(r => !isInternalTable(r[1] || r[0]))
                .map(r => {
                  const tName = r[1] || r[0];
                  const full = `${catalog}.${schema}.${tName}`;
                  return { full_name: full, table_name: tName, schema_name: schema, catalog_name: catalog, registered: registered.has(full) };
                });
            }
          } catch (e) {
            console.warn('[uc-tables-browse] SHOW TABLES failed:', e.message);
          }
        }
      }

      // Final fallback: UC REST API
      if (tables.length === 0) {
        try {
          const { host, token } = await getUcAuth();
          const data = await ucApiRequest(host, token,
            `/api/2.1/unity-catalog/tables?catalog_name=${encodeURIComponent(catalog)}&schema_name=${encodeURIComponent(schema)}`);
          tables = (data.tables || [])
            .filter(t => !isInternalTable(t.name))
            .map(t => ({
              full_name: t.full_name, table_name: t.name,
              schema_name: schema, catalog_name: catalog,
              table_type: t.table_type, comment: t.comment,
              registered: registered.has(t.full_name),
            }));
        } catch (_) {}
      }

      // If still empty, guide the user to grant at catalog level — covers all schemas/tables now and future
      let needsGrant = false;
      let grantSql = '';
      let sqlEditorUrl = '';
      if (tables.length === 0) {
        const spId = process.env.DATABRICKS_CLIENT_ID || '';
        if (spId) {
          needsGrant = true;
          const databricksHost = (process.env.DATABRICKS_HOST || '').replace(/\/$/, '');
          grantSql = `GRANT USE CATALOG ON CATALOG \`${catalog}\` TO \`${spId}\`;\nGRANT USE SCHEMA ON CATALOG \`${catalog}\` TO \`${spId}\`;\nGRANT SELECT ON CATALOG \`${catalog}\` TO \`${spId}\`;`;
          sqlEditorUrl = databricksHost ? `${databricksHost}/sql/editor` : '';
        }
      }

      res.json({ tables, needsGrant, grantSql, sqlEditorUrl });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // ─── Admin: UC Table Discovery ────────────────────────────────────────────────
  app.get('/api/portal/admin/uc-tables', async (req, res) => {
    try {
      // Get already-registered UC table names
      const { rows: existing } = await query(
        `SELECT uc_full_name FROM data_products WHERE uc_full_name IS NOT NULL AND uc_full_name != ''`);
      const registered = new Set(existing.map(r => r.uc_full_name));

      // If a warehouse is configured, always query real UC tables (even in demo mode)
      if (SQL_WAREHOUSE_ID) {
        const schema = await fetchUcSchema('information_schema.tables');
        if (schema) return res.json({ source: 'unity_catalog', tables: schema.filter(t => !registered.has(t.full_name)) });
      }

      // No warehouse configured — return generic placeholder tables so the UI isn't empty
      const demoTables = [
        { full_name: 'your_catalog.your_schema.sales_transactions',    table_name: 'sales_transactions',    schema_name: 'your_schema', catalog_name: 'your_catalog' },
        { full_name: 'your_catalog.your_schema.customer_profiles',     table_name: 'customer_profiles',     schema_name: 'your_schema', catalog_name: 'your_catalog' },
        { full_name: 'your_catalog.your_schema.product_inventory',     table_name: 'product_inventory',     schema_name: 'your_schema', catalog_name: 'your_catalog' },
        { full_name: 'your_catalog.your_schema.employee_records',      table_name: 'employee_records',      schema_name: 'your_schema', catalog_name: 'your_catalog' },
        { full_name: 'your_catalog.your_schema.financial_ledger',      table_name: 'financial_ledger',      schema_name: 'your_schema', catalog_name: 'your_catalog' },
      ];
      res.json({ source: 'demo_placeholder', tables: demoTables.filter(t => !registered.has(t.full_name)), registered: existing.map(r => r.uc_full_name) });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.post('/api/portal/admin/import-uc', async (req, res) => {
    try {
      const { tables } = req.body;
      if (!Array.isArray(tables) || tables.length === 0) return res.status(400).json({ error: 'tables array required' });

      const { rows: [maxRow] } = await query(
        `SELECT MAX(CAST(SUBSTRING(product_ref FROM 4) AS INTEGER)) AS max_id FROM data_products`);
      let nextId = (maxRow.max_id || 16) + 1;

      // Domain inference from catalog/schema name — broadens left-nav filter options
      const inferDomain = (catalogName = '', schemaName = '') => {
        const s = `${catalogName} ${schemaName}`.toLowerCase();
        if (/finance|budget|payroll|revenue|billing|accounting|expenditure/.test(s)) return 'Finance';
        if (/hr|human.resource|employee|headcount|workforce|hris/.test(s)) return 'HR';
        if (/health|clinical|patient|medical|pharma/.test(s)) return 'Healthcare';
        if (/fire|police|ems|safety|emergency|incident|911/.test(s)) return 'Public Safety';
        if (/sales|customer|crm|marketing|retail|ecommerce/.test(s)) return 'Sales & Marketing';
        if (/geo|gis|spatial|map|location|address/.test(s)) return 'Geospatial';
        if (/weather|forecast|climate|accuweather/.test(s)) return 'Weather';
        if (/tax|property|assessment|parcel/.test(s)) return 'Property Tax';
        if (/supply|inventory|logistics|warehouse|procurement/.test(s)) return 'Operations';
        if (/nyctaxi|transit|transport|trip|vehicle/.test(s)) return 'Transportation';
        if (/bakehouse|restaurant|food|hospitality|hotel|wander/.test(s)) return 'Hospitality';
        if (/audit|compliance|risk|governance/.test(s)) return 'Compliance';
        return 'Other';
      };

      const { host, token } = await getUcAuth();
      // Clear any cached synthetic schema for tables about to be imported
      cacheClear('schema:');

      const imported = [];

      for (const t of tables) {
        const ref = `DP-${String(nextId++).padStart(3, '0')}`;
        const parts = (t.full_name || '').split('.');
        const catalogName = parts[0] || '';
        const schemaName  = parts[1] || '';
        const tableName   = parts[2] || t.table_name || '';

        const displayName = (tableName || t.full_name.split('.').pop())
          .replace(/_/g, ' ').replace(/\bgold\b/i, '').trim()
          .replace(/\b\w/g, c => c.toUpperCase());

        // ── Enrich from UC REST API ──────────────────────────────────────────
        let ucComment = '';
        let ucTags = [];
        let ucOwner = '';
        let ucUpdatedAt = null;
        let hasPii = false;
        let hasConf = false;
        try {
          const ucMeta = await ucApiRequest(host, token,
            `/api/2.1/unity-catalog/tables/${encodeURIComponent(t.full_name)}`);
          ucComment  = ucMeta?.comment || '';
          ucOwner    = ucMeta?.owner   || '';
          ucUpdatedAt = ucMeta?.updated_at ? new Date(ucMeta.updated_at).toISOString() : null;

          // UC tags are a key-value map — use the keys as tags (values often empty)
          const rawTags = ucMeta?.tags || {};
          ucTags = Object.keys(rawTags).filter(k => k && k.trim());

          // Infer sensitivity from column names using same patterns as schema panel
          const piiPatterns = /^(ssn|social_security|dob|date_of_birth|birth_date|email|phone|address|bank_account|credit_card|salary|compensation|wage)/i;
          const confPatterns = /^(cost_center|approver|budget_code|account_number|internal_id)/i;
          const cols = ucMeta?.columns || [];
          hasPii  = cols.some(c => piiPatterns.test(c.name || ''));
          hasConf = !hasPii && cols.some(c => confPatterns.test(c.name || ''));
        } catch (_) { /* non-fatal — proceed without enrichment */ }

        // Build final tag array: domain + sensitivity + existing UC tags
        // Intentionally excludes catalog/schema names (already structured fields)
        // and 'UC Import' (source method, not a discovery attribute)
        const domain = t.domain || inferDomain(catalogName, schemaName);
        const tagSet = new Set();
        if (domain && domain !== 'Other') tagSet.add(domain);
        if (hasPii)  tagSet.add('Contains PII');
        if (hasConf) tagSet.add('Confidential');
        ucTags.forEach(tag => tagSet.add(tag));
        if (tagSet.size === 0) tagSet.add('Dataset');
        const finalTags = `{${[...tagSet].map(tag => `"${tag.replace(/"/g, '')}"`).join(',')}}`;

        const description = ucComment || t.description || `Imported from Unity Catalog: ${t.full_name}`;
        const ownerEmail  = ucOwner || t.owner_email || 'datasteward@example.org';

        const { rows: [product] } = await query(
          `INSERT INTO data_products
             (product_ref, display_name, description, type, domain, tags, source_system,
              refresh_frequency, owner_email, classification, uc_full_name, is_active, status,
              last_refreshed)
           VALUES ($1, $2, $3, 'Dataset', $4, $5, 'Unity Catalog', 'Daily',
                   $6, 'Internal', $7, TRUE, 'Published', COALESCE($8, NOW()))
           ON CONFLICT (product_ref) DO NOTHING RETURNING *`,
          [ref, t.display_name || displayName, description,
           domain, finalTags,
           ownerEmail, t.full_name, ucUpdatedAt]);
        if (product) imported.push(product);
      }
      res.json({ imported: imported.length, products: imported });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // ─── Sync UC metadata (last_refreshed + mark unavailable) ────────────────────
  // Fetches updated_at from UC for each product that has a uc_full_name.
  // Also marks products whose UC table no longer exists as status='Unavailable'.
  app.post('/api/portal/admin/sync-uc-metadata', async (req, res) => {
    try {
      const { host, token } = await getUcAuth();
      const { rows: products } = await query(
        `SELECT product_id, product_ref, uc_full_name FROM data_products
         WHERE uc_full_name IS NOT NULL AND uc_full_name NOT LIKE 'your_catalog.%'`
      );
      if (!products.length) return res.json({ synced: 0, unavailable: 0 });

      let synced = 0, unavailable = 0;
      for (const p of products) {
        try {
          const ucMeta = await ucApiRequest(host, token,
            `/api/2.0/unity-catalog/tables/${encodeURIComponent(p.uc_full_name)}`);

          if (ucMeta?.error_code === 'TABLE_DOES_NOT_EXIST' || ucMeta?.error_code === 'NOT_FOUND') {
            await query(
              `UPDATE data_products SET status = 'Unavailable', updated_at = NOW() WHERE product_id = $1`,
              [p.product_id]);
            unavailable++;
          } else {
            // updated_at from UC is epoch ms
            const updatedAt = ucMeta?.updated_at
              ? new Date(ucMeta.updated_at).toISOString()
              : new Date().toISOString();
            await query(
              `UPDATE data_products SET last_refreshed = $1, updated_at = NOW() WHERE product_id = $2`,
              [updatedAt, p.product_id]);
            synced++;
          }
        } catch (_) { /* skip individual failures */ }
      }
      // Bust product column cache so next fetch rebuilds
      resetProductColsCache();
      console.log(`[sync-uc] synced=${synced} unavailable=${unavailable}`);
      res.json({ synced, unavailable, total: products.length });
    } catch (e) {
      console.error('[sync-uc-metadata]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  // ─── Auto-discover new UC tables ─────────────────────────────────────────────
  // Scans a catalog/schema prefix from settings (auto_discover_prefix) and imports
  // any tables not yet in data_products as status='Draft' for admin review.
  app.post('/api/portal/admin/discover-uc', async (req, res) => {
    try {
      const prefix = getSetting('auto_discover_prefix', '') || req.body?.prefix || '';
      if (!prefix) return res.status(400).json({ error: 'auto_discover_prefix not configured in Settings' });

      const parts = prefix.split('.');
      if (parts.length < 2) return res.status(400).json({ error: 'prefix must be catalog.schema or catalog.schema.prefix' });
      const [catalog, schema] = parts;

      const { host, token } = await getUcAuth();
      const listData = await ucApiRequest(host, token,
        `/api/2.0/unity-catalog/tables?catalog_name=${encodeURIComponent(catalog)}&schema_name=${encodeURIComponent(schema)}&max_results=200`);

      const ucTables = (listData?.tables || []).filter(t => {
        if (parts[2]) return t.name?.toLowerCase().startsWith(parts[2].toLowerCase());
        return true;
      });

      // Find which uc_full_names are already in data_products
      const { rows: existing } = await query(
        `SELECT uc_full_name FROM data_products WHERE uc_full_name IS NOT NULL`);
      const existingSet = new Set(existing.map(r => r.uc_full_name.toLowerCase()));

      const newTables = ucTables.filter(t =>
        !existingSet.has(`${catalog}.${schema}.${t.name}`.toLowerCase()));

      if (!newTables.length) return res.json({ discovered: 0, message: 'No new tables found' });

      // Get next product_ref
      const { rows: [maxRow] } = await query(
        `SELECT MAX(CAST(SUBSTRING(product_ref FROM 4) AS INTEGER)) AS max_id FROM data_products`);
      let nextId = (maxRow.max_id || 0) + 1;

      const drafted = [];
      for (const t of newTables) {
        const fullName = `${catalog}.${schema}.${t.name}`;
        const ref = `DP-${String(nextId++).padStart(3, '0')}`;
        const displayName = t.name.replace(/_/g, ' ').replace(/\bgold\b/i, '').trim()
          .replace(/\b\w/g, c => c.toUpperCase());
        const { rows: [product] } = await query(
          `INSERT INTO data_products
             (product_ref, display_name, description, type, domain, tags, source_system,
              refresh_frequency, owner_email, classification, uc_full_name, is_active, status, last_refreshed)
           VALUES ($1, $2, $3, 'Dataset', 'Other', '{}', 'Unity Catalog', 'Daily',
                   '', 'Internal', $4, FALSE, 'Draft', NOW())
           ON CONFLICT (product_ref) DO NOTHING RETURNING *`,
          [ref, displayName,
           `Auto-discovered from Unity Catalog: ${fullName}`, fullName]);
        if (product) drafted.push(product);
      }

      console.log(`[discover-uc] ${drafted.length} new tables drafted from ${prefix}`);
      res.json({ discovered: drafted.length, products: drafted });
    } catch (e) {
      console.error('[discover-uc]', e.message);
      res.status(500).json({ error: e.message });
    }
  });
}
