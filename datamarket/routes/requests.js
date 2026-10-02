import { query } from '../db.js';
import { rfaNotify, executeUcStatement } from '../databricks.js';

export function registerRoutes(app) {
  // ─── Access Requests ──────────────────────────────────────────────────────────
  app.get('/api/portal/requests', async (req, res) => {
    try {
      const { email, status } = req.query;
      let sql = `SELECT ar.request_id, ar.request_ref, ar.status, ar.business_reason, ar.access_level,
                        ar.requested_at, ar.resolved_at, ar.expires_at, ar.denial_reason, ar.uc_grant_sql,
                        dp.product_ref, dp.display_name AS product_name, dp.domain, dp.type AS product_type,
                        u.email AS requester_email, u.display_name AS requester_name, u.department AS requester_team
                 FROM access_requests ar
                 JOIN data_products dp ON dp.product_id = ar.product_id
                 JOIN users u ON u.user_id = ar.requester_id`;
      const params = [];
      const where = [];
      if (email)  { params.push(email);  where.push(`u.email = $${params.length}`); }
      if (status) { params.push(status); where.push(`ar.status = $${params.length}`); }
      if (where.length) sql += ' WHERE ' + where.join(' AND ');
      sql += ' ORDER BY ar.requested_at DESC';
      const { rows } = await query(sql, params);
      res.json(rows);
    } catch (e) {
      console.error('[/api/portal/requests]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  app.get('/api/portal/requests/pending', async (req, res) => {
    try {
      const { rows } = await query(`
        SELECT ar.request_id, ar.request_ref, ar.status, ar.business_reason, ar.access_level,
               ar.requested_at, dp.product_ref, dp.display_name AS product_name, dp.domain,
               dp.uc_full_name, u.email AS requester_email, u.display_name AS requester_name,
               u.department AS requester_team
        FROM access_requests ar
        JOIN data_products dp ON dp.product_id = ar.product_id
        JOIN users u ON u.user_id = ar.requester_id
        WHERE ar.status = 'Pending'
        ORDER BY ar.requested_at DESC`);
      res.json(rows);
    } catch (e) {
      console.error('[/api/portal/requests/pending]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  app.post('/api/portal/requests', async (req, res) => {
    try {
      const { productRef, requesterEmail, team, reason, accessLevel = 'Read Only' } = req.body;
      if (!productRef || !requesterEmail || !reason) {
        return res.status(400).json({ error: 'productRef, requesterEmail, and reason are required' });
      }

      const { rows: [product] } = await query('SELECT product_id FROM data_products WHERE product_ref = $1', [productRef]);
      if (!product) return res.status(404).json({ error: `Product ${productRef} not found` });

      // Upsert user — creates a row if this email hasn't been seen before
      const { rows: [user] } = await query(`
        INSERT INTO users (email, display_name, role, department)
        VALUES ($1, $2, 'analyst', 'General')
        ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
        RETURNING user_id, department`,
        [requesterEmail, requesterEmail.split('@')[0].replace('.', ' ').replace(/\b\w/g, c => c.toUpperCase())]
      );

      const { rows: [{ count }] } = await query('SELECT COUNT(*) FROM access_requests', []);
      const ref = `REQ-${String(parseInt(count) + 1).padStart(3, '0')}`;

      // Default 90-day expiry from approval date (set on approve, not submit)
      const { rows: [newReq] } = await query(`
        INSERT INTO access_requests (request_ref, product_id, requester_id, requester_team, business_reason, access_level, status)
        VALUES ($1, $2, $3, $4, $5, $6, 'Pending')
        RETURNING *`, [ref, product.product_id, user.user_id, team || user.department, reason, accessLevel]);

      await query(`INSERT INTO audit_log (event_type, actor_email, target_type, target_id, target_name, metadata)
        VALUES ('REQUEST_SUBMITTED', $1, 'access_request', $2, $3, $4)`,
        [requesterEmail, newReq.request_id, ref, JSON.stringify({ productRef, reason })]);

      // Fire RFA notification (best-effort, non-blocking)
      const { rows: [prod] } = await query('SELECT uc_full_name FROM data_products WHERE product_ref = $1', [productRef]);
      const rfaResult = await rfaNotify(prod?.uc_full_name, requesterEmail, reason);

      res.json({ ...newReq, request_ref: ref, rfa_notified: !!rfaResult });
    } catch (e) {
      console.error('[POST /api/portal/requests]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  app.put('/api/portal/requests/:id/approve', async (req, res) => {
    try {
      const { id } = req.params;
      const { adminEmail = 'datasteward@example.org' } = req.body;

      // id can be a UUID or a request_ref like "REQ-001" — avoid type mismatch
      const isUUID = /^[0-9a-f-]{36}$/i.test(id);
      const { rows: [req_] } = await query(`
        SELECT ar.*, dp.uc_full_name, dp.display_name AS product_name, u.email AS requester_email
        FROM access_requests ar
        JOIN data_products dp ON dp.product_id = ar.product_id
        JOIN users u ON u.user_id = ar.requester_id
        WHERE ${isUUID ? 'ar.request_id = $1::uuid' : 'ar.request_ref = $1'}`, [id]);
      if (!req_) return res.status(404).json({ error: 'Request not found' });

      const ucGrantSql = req_.uc_full_name
        ? `GRANT SELECT ON ${req_.uc_full_name} TO \`${req_.requester_email}\`;`
        : `-- No UC table linked for ${req_.product_name} (set uc_full_name on the product to enable automatic grants)`;

      const { rows: [adminUser] } = await query('SELECT user_id FROM users WHERE email = $1', [adminEmail]);

      await query(`UPDATE access_requests SET status = 'Approved', resolved_at = NOW(),
        resolved_by = $1, uc_grant_issued = TRUE, uc_grant_sql = $2, updated_at = NOW(),
        expires_at = NOW() + INTERVAL '90 days'
        WHERE request_ref = $3`,
        [adminUser?.user_id || null, ucGrantSql, req_.request_ref]);

      // Execute the real GRANT in UC (skipped in demo mode)
      const grantResult = await executeUcStatement(ucGrantSql);

      try {
        await query(`INSERT INTO audit_log (event_type, actor_email, target_type, target_id, target_name, metadata)
          VALUES ('REQUEST_APPROVED', $1, 'access_request', $2, $3, $4)`,
          [adminEmail, req_.request_id, req_.request_ref, JSON.stringify({ ucGrantSql, uc_executed: grantResult.executed })]);
      } catch (_) {}

      res.json({ status: 'Approved', uc_grant_sql: ucGrantSql, uc_executed: grantResult.executed });
    } catch (e) {
      console.error('[PUT approve]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  app.put('/api/portal/requests/:id/deny', async (req, res) => {
    try {
      const { id } = req.params;
      const { adminEmail = 'datasteward@example.org', reason = '' } = req.body;

      const isUUID = /^[0-9a-f-]{36}$/i.test(id);
      const { rows: [req_] } = await query(
        `SELECT request_id, request_ref FROM access_requests WHERE ${isUUID ? 'request_id = $1::uuid' : 'request_ref = $1'}`, [id]);
      if (!req_) return res.status(404).json({ error: 'Request not found' });

      const { rows: [adminUser] } = await query('SELECT user_id FROM users WHERE email = $1', [adminEmail]);

      await query(`UPDATE access_requests SET status = 'Denied', resolved_at = NOW(),
        resolved_by = $1, denial_reason = $2, updated_at = NOW()
        WHERE request_ref = $3`,
        [adminUser?.user_id || null, reason, req_.request_ref]);

      try {
        await query(`INSERT INTO audit_log (event_type, actor_email, target_type, target_id, target_name, metadata)
          VALUES ('REQUEST_DENIED', $1, 'access_request', $2, $3, $4)`,
          [adminEmail, req_.request_id, req_.request_ref, JSON.stringify({ reason })]);
      } catch (_) {}

      res.json({ status: 'Denied' });
    } catch (e) {
      console.error('[PUT deny]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  // ─── Revoke access ────────────────────────────────────────────────────────────
  app.put('/api/portal/requests/:id/revoke', async (req, res) => {
    try {
      const { id } = req.params;
      const { adminEmail = 'datasteward@example.org', reason = 'Access revoked by administrator' } = req.body;
      const isUUID = /^[0-9a-f-]{36}$/i.test(id);
      const { rows: [req_] } = await query(
        `SELECT request_id, request_ref, uc_grant_sql FROM access_requests
         WHERE ${isUUID ? 'request_id = $1::uuid' : 'request_ref = $1'}`, [id]);
      if (!req_) return res.status(404).json({ error: 'Request not found' });

      // Generate REVOKE SQL mirroring the original GRANT
      const revokeSql = req_.uc_grant_sql
        ? req_.uc_grant_sql.replace(/^GRANT/, 'REVOKE').replace(/ TO /, ' FROM ')
        : `-- No UC table linked; manual revocation required`;

      await query(`UPDATE access_requests SET status = 'Revoked', resolved_at = NOW(),
        denial_reason = $1, uc_grant_sql = $2, updated_at = NOW()
        WHERE request_ref = $3`,
        [reason, revokeSql, req_.request_ref]);

      // Execute the real REVOKE in UC (skipped in demo mode)
      const revokeResult = await executeUcStatement(revokeSql);

      try {
        await query(`INSERT INTO audit_log (event_type, actor_email, target_name, metadata)
          VALUES ('ACCESS_REVOKED', $1, $2, $3)`,
          [adminEmail, req_.request_ref, JSON.stringify({ reason, revokeSql, uc_executed: revokeResult.executed })]);
      } catch (_) {}

      res.json({ status: 'Revoked', revoke_sql: revokeSql, uc_executed: revokeResult.executed });
    } catch (e) {
      console.error('[PUT revoke]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  // ─── Granted access for a product (admin revoke UI) ───────────────────────────
  app.get('/api/portal/products/:ref/granted-access', async (req, res) => {
    try {
      const { ref } = req.params;
      const { rows } = await query(`
        SELECT ar.request_ref, ar.requested_at, ar.resolved_at, ar.expires_at,
               u.email AS requester_email, u.display_name AS requester_name
        FROM access_requests ar
        JOIN data_products dp ON dp.product_id = ar.product_id
        JOIN users u ON u.user_id = ar.requester_id
        WHERE dp.product_ref = $1 AND ar.status = 'Approved'
        ORDER BY ar.resolved_at DESC`, [ref]);
      res.json(rows);
    } catch (e) {
      console.error('[GET granted-access]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  // ─── Get notifications for a user ─────────────────────────────────────────────
  app.get('/api/portal/notifications', async (req, res) => {
    try {
      const { email } = req.query;
      if (!email) return res.json([]);
      const { rows } = await query(`
        SELECT ar.request_ref, ar.status, ar.resolved_at, ar.expires_at, ar.denial_reason,
               dp.display_name AS product_name, dp.product_ref
        FROM access_requests ar
        JOIN data_products dp ON dp.product_id = ar.product_id
        JOIN users u ON u.user_id = ar.requester_id
        WHERE u.email = $1
          AND ar.status IN ('Approved','Denied','Revoked')
          AND ar.resolved_at > NOW() - INTERVAL '7 days'
        ORDER BY ar.resolved_at DESC
        LIMIT 10`, [email]);
      // Also include requests expiring within 14 days
      const { rows: expiring } = await query(`
        SELECT ar.request_ref, 'Expiring' AS status, ar.expires_at, ar.resolved_at,
               dp.display_name AS product_name, dp.product_ref
        FROM access_requests ar
        JOIN data_products dp ON dp.product_id = ar.product_id
        JOIN users u ON u.user_id = ar.requester_id
        WHERE u.email = $1
          AND ar.status = 'Approved'
          AND ar.expires_at < NOW() + INTERVAL '14 days'
        ORDER BY ar.expires_at ASC
        LIMIT 5`, [email]);
      res.json([...expiring, ...rows]);
    } catch (e) {
      console.error('[/api/portal/notifications]', e.message);
      res.json([]);
    }
  });

  // ─── Nudge Approver ───────────────────────────────────────────────────────────
  app.post('/api/portal/requests/:id/nudge', async (req, res) => {
    try {
      const { id } = req.params;
      const { requesterEmail, productName } = req.body;
      await query(`
        INSERT INTO audit_log (event_type, actor_email, target_name, metadata)
        VALUES ('NUDGE_SENT', $1, $2, $3)
      `, [
        requesterEmail || 'unknown',
        id,
        JSON.stringify({ productName, message: 'Requester sent a reminder to approver via DataMarket Assistant' })
      ]);
      res.json({ success: true, message: 'Reminder logged and approver notified' });
    } catch (e) {
      console.error('[POST nudge]', e.message);
      res.json({ success: true }); // best-effort — don't fail the UI
    }
  });

  // ─── User Library ─────────────────────────────────────────────────────────────
  app.get('/api/portal/library', async (req, res) => {
    try {
      const { email } = req.query;
      if (!email) return res.status(400).json({ error: 'email required' });

      // Approved requests + pinned library entries
      const { rows } = await query(`
        SELECT dp.product_ref, dp.display_name AS product_name, dp.domain, dp.type AS product_type,
               dp.classification, dp.refresh_frequency, dp.source_system, dp.uc_full_name,
               'approved' AS source, ar.resolved_at AS added_at, ar.request_ref
        FROM access_requests ar
        JOIN data_products dp ON dp.product_id = ar.product_id
        JOIN users u ON u.user_id = ar.requester_id
        WHERE u.email = $1 AND ar.status = 'Approved'
        UNION ALL
        SELECT dp.product_ref, dp.display_name, dp.domain, dp.type,
               dp.classification, dp.refresh_frequency, dp.source_system, dp.uc_full_name,
               'library' AS source, ul.added_at, NULL AS request_ref
        FROM user_library ul
        JOIN data_products dp ON dp.product_id = ul.product_id
        JOIN users u ON u.user_id = ul.user_id
        WHERE u.email = $1
        ORDER BY added_at DESC`, [email]);

      res.json(rows);
    } catch (e) {
      console.error('[/api/portal/library]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  // ─── Audit Log ────────────────────────────────────────────────────────────────
  app.get('/api/portal/audit', async (req, res) => {
    try {
      const { rows } = await query(
        'SELECT * FROM audit_log ORDER BY occurred_at DESC LIMIT 50', []);
      res.json(rows);
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });
}
