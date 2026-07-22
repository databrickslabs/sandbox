import { query, getPool } from '../db.js';

// ─── Caller identity helpers (SSO header or request body fallback) ────────────
export function callerEmail(req) {
  return req.headers['x-forwarded-email'] || req.headers['x-forwarded-user'] || req.body?.requester_email || 'anonymous';
}
export function callerName(req) {
  const email = callerEmail(req);
  return req.body?.requester_name || email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export function registerRoutes(app) {
  // ─── Feature Requests (Loop 1 — data demand signal) ─────────────────────────
  app.get('/api/portal/feature-requests', async (req, res) => {
    try {
      const email = callerEmail(req);
      const { rows } = await query(`
        SELECT fr.*,
               COALESCE(v.voter_emails, ARRAY[]::text[]) AS voter_emails,
               (fr.requester_email = $1 OR $1 = ANY(COALESCE(v.voter_emails, ARRAY[]::text[]))) AS user_voted
        FROM feature_requests fr
        LEFT JOIN (
          SELECT request_id, array_agg(voter_email) AS voter_emails
          FROM feature_request_votes GROUP BY request_id
        ) v ON v.request_id = fr.request_id
        ORDER BY fr.upvotes DESC, fr.created_at DESC
      `, [email]);
      res.json(rows);
    } catch (e) { res.status(500).json({ error: e.message }); }
  });

  app.post('/api/portal/feature-requests', async (req, res) => {
    try {
      const { title, description } = req.body;
      if (!title?.trim()) return res.status(400).json({ error: 'title required' });
      const email = callerEmail(req);
      const name  = callerName(req);
      const { rows: [fr] } = await query(`
        INSERT INTO feature_requests (title, description, requester_email, requester_name, upvotes)
        VALUES ($1, $2, $3, $4, 1) RETURNING *
      `, [title.trim(), description?.trim() || null, email, name]);
      // Auto-vote by requester
      await query(`
        INSERT INTO feature_request_votes (request_id, voter_email) VALUES ($1, $2) ON CONFLICT DO NOTHING
      `, [fr.request_id, email]);
      res.json(fr);
    } catch (e) { res.status(500).json({ error: e.message }); }
  });

  app.post('/api/portal/feature-requests/:id/vote', async (req, res) => {
    try {
      const id    = parseInt(req.params.id);
      const email = callerEmail(req);
      const pool  = await getPool();
      const client = await pool.connect();
      try {
        await client.query('BEGIN');
        const { rows: existing } = await client.query(
          `SELECT vote_id FROM feature_request_votes WHERE request_id=$1 AND voter_email=$2`, [id, email]);
        let voted;
        if (existing.length) {
          await client.query(`DELETE FROM feature_request_votes WHERE request_id=$1 AND voter_email=$2`, [id, email]);
          await client.query(`UPDATE feature_requests SET upvotes = GREATEST(0, upvotes-1), updated_at=NOW() WHERE request_id=$1`, [id]);
          voted = false;
        } else {
          await client.query(`INSERT INTO feature_request_votes (request_id, voter_email) VALUES ($1, $2)`, [id, email]);
          await client.query(`UPDATE feature_requests SET upvotes = upvotes+1, updated_at=NOW() WHERE request_id=$1`, [id]);
          voted = true;
        }
        await client.query('COMMIT');
        return res.json({ voted });
      } catch (e) {
        await client.query('ROLLBACK');
        throw e;
      } finally {
        client.release();
      }
    } catch (e) { res.status(500).json({ error: e.message }); }
  });

  app.put('/api/portal/feature-requests/:id/status', async (req, res) => {
    try {
      const { status } = req.body;
      const allowed = ['open', 'on_roadmap', 'done', 'declined'];
      if (!allowed.includes(status)) return res.status(400).json({ error: 'invalid status' });
      const { rows: [fr] } = await query(
        `UPDATE feature_requests SET status=$1, updated_at=NOW() WHERE request_id=$2 RETURNING *`,
        [status, parseInt(req.params.id)]);
      res.json(fr);
    } catch (e) { res.status(500).json({ error: e.message }); }
  });
}
