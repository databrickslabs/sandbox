import { query, DEMO_MODE } from '../db.js';
import { ucApiRequest, getUcAuth } from '../databricks.js';
import { normalizeRole } from '../lib/roles.js';

function callerEmail(req) {
  return req.headers['x-forwarded-email'] || req.headers['x-forwarded-user'] || req.body?.requester_email || 'anonymous';
}

export function registerRoutes(app) {
  // ─── Identity — resolve SSO user or return demo mode personas ────────────────
  app.get('/api/portal/identity', async (req, res) => {
    if (DEMO_MODE) return res.json({ mode: 'demo' });

    const email = callerEmail(req) === 'anonymous' ? '' : callerEmail(req);
    if (!email) return res.json({ mode: 'demo', reason: 'no_sso_header' });

    const ADMIN_EMAILS = (process.env.ADMIN_EMAIL || process.env.DATABRICKS_USER || '')
      .split(',').map(e => e.trim().toLowerCase()).filter(Boolean);
    const isHardcodedAdmin = ADMIN_EMAILS.includes(email.toLowerCase());

    try {
      const resolveScim = async () => {
        try {
          const { host, token } = await getUcAuth();
          const filter = encodeURIComponent(`userName eq "${email}"`);
          const scimData = await ucApiRequest(host, token,
            `/api/2.0/preview/scim/v2/Users?filter=${filter}&count=1&attributes=groups,displayName,name`);
          const scimUser = (scimData.Resources || [])[0];
          const displayName = scimUser?.displayName
            || [scimUser?.name?.givenName, scimUser?.name?.familyName].filter(Boolean).join(' ')
            || null;
          const groupNames = (scimUser?.groups || []).map(g => g.display).filter(Boolean);
          let groupRole = null;
          if (groupNames.length) {
            const { rows: matched } = await query(
              `SELECT role FROM portal_groups WHERE group_name = ANY($1) ORDER BY
                 CASE role WHEN 'admin' THEN 1 WHEN 'steward' THEN 2 ELSE 3 END LIMIT 1`,
              [groupNames]
            );
            groupRole = matched[0]?.role ? normalizeRole(matched[0].role) : null;
          }
          return { displayName, groupRole };
        } catch (_) { return { displayName: null, groupRole: null }; }
      };

      const { rows: [user] } = await query(
        `SELECT user_id, email, display_name, role, department FROM users WHERE email = $1`, [email]);

      if (user) {
        if (isHardcodedAdmin && user.role !== 'admin') {
          await query(`UPDATE users SET role = 'admin' WHERE email = $1`, [email]);
          user.role = 'admin';
          console.info(`[identity] Promoted ${email} to admin (ADMIN_EMAIL match)`);
        } else if (!isHardcodedAdmin) {
          const { groupRole } = await resolveScim();
          if (groupRole && user.role !== groupRole) {
            await query(`UPDATE users SET role = $1 WHERE email = $2`, [groupRole, email]);
            user.role = groupRole;
            console.info(`[identity] ${email} → role '${groupRole}' via group sync`);
          }
        }
        if (!user.display_name || user.display_name === user.email || user.display_name.includes('@')) {
          const { displayName: scimName } = await resolveScim();
          if (scimName) {
            await query(`UPDATE users SET display_name = $1 WHERE email = $2`, [scimName, email]);
            user.display_name = scimName;
          }
        }
        user.role = normalizeRole(user.role);
        return res.json({ mode: 'sso', user });
      }

      const { displayName: scimDisplayName, groupRole } = await resolveScim();
      let role = 'analyst';
      if (isHardcodedAdmin) {
        role = 'admin';
      } else if (groupRole) {
        role = groupRole;
        console.info(`[identity] ${email} → role '${role}' via group`);
      }

      const displayName = scimDisplayName
        || email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
      const { rows: [newUser] } = await query(
        `INSERT INTO users (email, display_name, role, department)
         VALUES ($1, $2, $3, 'General') RETURNING *`, [email, displayName, normalizeRole(role)]);
      console.info(`[identity] Auto-registered ${email} as ${normalizeRole(role)} (name: ${displayName})`);
      return res.json({ mode: 'sso', user: { ...newUser, role: normalizeRole(newUser.role) }, new_user: true });
    } catch (e) {
      console.warn('[/api/portal/identity]', e.message);
      return res.json({ mode: 'demo', reason: e.message });
    }
  });

  // ─── Admin: Users ─────────────────────────────────────────────────────────────
  app.get('/api/portal/admin/users', async (req, res) => {
    try {
      const { rows } = await query(
        `SELECT user_id, email, display_name, role, department, created_at FROM users ORDER BY display_name`);
      res.json(rows.map(u => ({ ...u, role: normalizeRole(u.role) })));
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.post('/api/portal/admin/users', async (req, res) => {
    try {
      const { email, display_name, role, department } = req.body;
      if (!email) return res.status(400).json({ error: 'email is required' });
      const normalizedRole = normalizeRole(role);
      const { rows: [user] } = await query(
        `INSERT INTO users (email, display_name, role, department)
         VALUES ($1, $2, $3, $4)
         ON CONFLICT (email) DO UPDATE
           SET display_name = EXCLUDED.display_name,
               role         = EXCLUDED.role,
               department   = EXCLUDED.department
         RETURNING *`,
        [email.trim().toLowerCase(), display_name || '', normalizedRole, department || '']
      );
      res.status(201).json({ ...user, role: normalizeRole(user.role) });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  app.put('/api/portal/admin/users/:id', async (req, res) => {
    try {
      const { id } = req.params;
      const { role, department, display_name } = req.body;
      const sets = [];
      const params = [];
      if (role)         { params.push(normalizeRole(role)); sets.push(`role = $${params.length}`); }
      if (department)   { params.push(department);   sets.push(`department = $${params.length}`); }
      if (display_name) { params.push(display_name); sets.push(`display_name = $${params.length}`); }
      if (sets.length === 0) return res.status(400).json({ error: 'Nothing to update' });
      params.push(id);
      const { rows: [user] } = await query(
        `UPDATE users SET ${sets.join(', ')} WHERE user_id = $${params.length}::uuid RETURNING *`, params);
      if (!user) return res.status(404).json({ error: 'User not found' });
      res.json({ ...user, role: normalizeRole(user.role) });
    } catch (e) {
      res.status(500).json({ error: e.message });
    }
  });

  // ─── SCIM user search — proxies Databricks workspace SCIM API ────────────────
  app.get('/api/portal/admin/scim-search', async (req, res) => {
    try {
      const { q = '' } = req.query;
      if (!q || q.length < 2) return res.json([]);

      const { host, token } = await getUcAuth();
      const filter = encodeURIComponent(`displayName co "${q}" or userName co "${q}"`);
      const scimData = await ucApiRequest(host, token,
        `/api/2.0/preview/scim/v2/Users?filter=${filter}&count=10&attributes=displayName,userName,emails`);

      const users = (scimData.Resources || []).map(u => ({
        display_name: u.displayName || u.userName,
        email: (u.emails?.find(e => e.primary)?.value) || u.userName,
      })).filter(u => u.email);

      res.json(users);
    } catch (e) {
      console.warn('[SCIM search]', e.message);
      res.json([]);
    }
  });

  // ─── SCIM Group search ────────────────────────────────────────────────────────
  app.get('/api/portal/admin/scim-groups-search', async (req, res) => {
    try {
      const { q = '' } = req.query;
      if (!q || q.length < 1) return res.json([]);
      const { host, token } = await getUcAuth();
      const filter = encodeURIComponent(`displayName co "${q}"`);
      const scimData = await ucApiRequest(host, token,
        `/api/2.0/preview/scim/v2/Groups?filter=${filter}&count=20&attributes=displayName,id,members`);
      const groups = (scimData.Resources || []).map(g => ({
        scim_id:    g.id,
        group_name: g.displayName,
        member_count: (g.members || []).length,
      }));
      res.json(groups);
    } catch (e) {
      console.warn('[SCIM groups search]', e.message);
      res.json([]);
    }
  });

  // ─── Portal Groups CRUD ───────────────────────────────────────────────────────
  app.get('/api/portal/admin/groups', async (req, res) => {
    try {
      const { rows } = await query(`SELECT * FROM portal_groups ORDER BY group_name`);
      res.json(rows.map(g => ({ ...g, role: normalizeRole(g.role) })));
    } catch (e) { res.status(500).json({ error: e.message }); }
  });

  app.post('/api/portal/admin/groups', async (req, res) => {
    try {
      const { group_name, scim_id, role, department } = req.body;
      if (!group_name) return res.status(400).json({ error: 'group_name required' });
      const { rows: [g] } = await query(
        `INSERT INTO portal_groups (group_name, scim_id, role, department)
         VALUES ($1, $2, $3, $4)
         ON CONFLICT (group_name) DO UPDATE SET role=$3, department=$4, scim_id=$2
         RETURNING *`,
        [group_name, scim_id || null, normalizeRole(role), department || 'General']
      );
      res.json({ ...g, role: normalizeRole(g.role) });
    } catch (e) { res.status(500).json({ error: e.message }); }
  });

  app.delete('/api/portal/admin/groups/:id', async (req, res) => {
    try {
      await query(`DELETE FROM portal_groups WHERE group_id = $1`, [req.params.id]);
      res.json({ ok: true });
    } catch (e) { res.status(500).json({ error: e.message }); }
  });
}
