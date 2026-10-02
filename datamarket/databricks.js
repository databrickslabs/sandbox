import https from 'https';
import { getDatabricksHost, getWorkspaceOAuthToken, httpsJsonRequest } from './auth.js';
import { DEMO_MODE, getSetting, loadSettings, RFA_ENABLED } from './db.js';

function getWarehouseId() {
  return getSetting('sql_warehouse_id', process.env.SQL_WAREHOUSE_ID || '');
}

// ─── Databricks REST API helper ──────────────────────────────────────────────
export async function databricksApi(method, apiPath, body = null) {
  const host = getDatabricksHost();
  const token = await getWorkspaceOAuthToken();
  if (!host || !token) throw new Error('DATABRICKS_HOST or workspace credentials not set');

  const payload = body ? JSON.stringify(body) : null;
  const { status, data } = await httpsJsonRequest({
    hostname: host,
    path: apiPath,
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...(payload ? { 'Content-Length': Buffer.byteLength(payload) } : {}),
    },
    body: payload,
  });
  return { status, data };
}

// ─── RFA: Send access request notification to configured destinations ────────
export async function rfaNotify(ucFullName, requesterEmail, comment) {
  if (!RFA_ENABLED || !ucFullName) return null;
  try {
    const parts = ucFullName.split('.');
    if (parts.length < 3) return null;
    const securableType = parts.length === 3 ? 'TABLE' : 'CATALOG';
    const result = await databricksApi('POST', '/api/3.0/rfa/access-requests', {
      requests: [{
        comment: comment || `Access requested via DataMarket`,
        securable_permissions: [{
          permissions: ['SELECT'],
          securable: { full_name: ucFullName, type: securableType }
        }]
      }]
    });
    console.log(`[RFA] Notification sent for ${ucFullName} → status ${result.status}`);
    return result;
  } catch (e) {
    console.warn('[RFA] Notification failed (non-fatal):', e.message);
    return null;
  }
}

// ─── UC: Execute GRANT/REVOKE via SQL Statement Execution API ────────────────
export async function executeUcStatement(sql) {
  if (DEMO_MODE || !getWarehouseId()) return { executed: false, reason: DEMO_MODE ? 'demo_mode' : 'no_warehouse' };
  try {
    const result = await databricksApi('POST', '/api/2.0/sql/statements', {
      warehouse_id: getWarehouseId(),
      statement: sql,
      wait_timeout: '10s'
    });
    const status = result.data?.status?.state || 'UNKNOWN';
    console.log(`[UC] Executed: ${sql.substring(0, 80)}... → ${status}`);
    return { executed: true, status, result: result.data };
  } catch (e) {
    console.warn('[UC] Statement execution failed (non-fatal):', e.message);
    return { executed: false, reason: e.message };
  }
}

// ─── UC: Fetch column schema + tags for a table ─────────────────────────────
export async function fetchUcSchema(ucFullName) {
  const warehouseId = getWarehouseId();
  if (!warehouseId || !ucFullName) return null;
  const parts = ucFullName.split('.');
  if (parts.length !== 3) return null;
  const [catalog, schema, table] = parts;
  try {
    const colResult = await databricksApi('POST', '/api/2.0/sql/statements', {
      warehouse_id: warehouseId,
      // Query the catalog's own information_schema, not system.information_schema
      statement: `SELECT column_name, data_type, comment FROM \`${catalog}\`.information_schema.columns
                  WHERE table_schema = '${schema}' AND table_name = '${table}'
                  ORDER BY ordinal_position`,
      wait_timeout: '10s'
    });
    if (colResult.data?.status?.state !== 'SUCCEEDED') return null;
    const columns = (colResult.data.result?.data_array || []).map(row => ({
      name: row[0], type: (row[1] || 'STRING').toUpperCase(), description: row[2] || ''
    }));

    let tagMap = {};
    try {
      const tagResult = await databricksApi('POST', '/api/2.0/sql/statements', {
        warehouse_id: getWarehouseId(),
        statement: `SELECT column_name, tag_name, tag_value FROM \`${catalog}\`.information_schema.column_tags
                    WHERE table_schema = '${schema}' AND table_name = '${table}'`,
        wait_timeout: '10s'
      });
      if (tagResult.data?.status?.state === 'SUCCEEDED') {
        for (const row of (tagResult.data.result?.data_array || [])) {
          if (!tagMap[row[0]]) tagMap[row[0]] = {};
          tagMap[row[0]][row[1]] = row[2];
        }
      }
    } catch (_) {}

    const piiPatterns = /^(ssn|social_security|dob|date_of_birth|birth_date|email|phone|address|bank_account|credit_card|salary|compensation|wage)/i;
    const confPatterns = /^(cost_center|approver|budget_code|account_number|internal_id)/i;

    return columns.map(col => {
      const tags = tagMap[col.name] || {};
      let sensitivity = (tags.sensitivity_level || tags.sensitivity || '').toUpperCase();
      if (!sensitivity) {
        if (piiPatterns.test(col.name)) sensitivity = 'PII';
        else if (confPatterns.test(col.name)) sensitivity = 'CONFIDENTIAL';
        else sensitivity = 'INTERNAL';
      }
      const masked = sensitivity === 'PII' || sensitivity === 'CONFIDENTIAL';
      const elevatedPII = sensitivity === 'PII' && piiPatterns.test(col.name) && /ssn|dob|date_of_birth|birth|bank|credit_card/i.test(col.name);
      return { ...col, sensitivity, masked, elevatedPII };
    });
  } catch (e) {
    console.warn(`[UC] Schema fetch failed for ${ucFullName}:`, e.message);
    return null;
  }
}

// ─── UC Catalog Browser (lazy, no SQL warehouse needed) ──────────────────────
export function ucApiRequest(host, token, path) {
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: host, path, method: 'GET',
      headers: { 'Authorization': `Bearer ${token}` },
    }, (res) => {
      let body = '';
      res.on('data', c => body += c);
      res.on('end', () => { try { resolve(JSON.parse(body)); } catch (_) { reject(new Error('Bad UC API response')); } });
    });
    req.on('error', reject);
    req.end();
  });
}

export async function getUcAuth() {
  const host = getDatabricksHost();
  const token = await getWorkspaceOAuthToken();
  if (!host || !token) throw new Error('DATABRICKS_HOST and workspace credentials are required');
  return { host, token };
}
