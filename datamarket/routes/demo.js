import { query, DEMO_MODE } from '../db.js';

export function registerRoutes(app) {
  // ─── Demo Seed ────────────────────────────────────────────────────────────────
  app.post('/api/portal/demo-seed', async (req, res) => {
    if (!DEMO_MODE) {
      return res.status(403).json({ error: 'Demo seed is disabled in production mode.' });
    }
    try {
      await query(`
        INSERT INTO users (email, display_name, role, department) VALUES
          ('analyst@example.org',     'Alex Analyst',   'analyst',      'Finance'),
          ('datasteward@example.org', 'Dana Steward',   'admin', 'Data Governance')
        ON CONFLICT (email) DO NOTHING
      `);

      await query(`
        INSERT INTO data_products (product_ref, uc_full_name, display_name, description, type, domain, tags, source_system, refresh_frequency, owner_email, classification, last_refreshed) VALUES
          ('DP-001', 'your_catalog.your_schema.revenue_summary',
           'Revenue Summary', 'Monthly revenue aggregations by business unit and region.',
           'Dataset', 'Finance', ARRAY['revenue','monthly','kpi'], 'ERP', 'Monthly', 'datasteward@example.org', 'Internal', NOW() - INTERVAL '5 days'),
          ('DP-002', 'your_catalog.your_schema.customer_360',
           'Customer 360', 'Unified customer profile combining CRM, support, and usage data.',
           'Dataset', 'Operations', ARRAY['customer','crm','unified'], 'CRM', 'Daily', 'datasteward@example.org', 'Confidential', NOW() - INTERVAL '1 day'),
          ('DP-003', 'your_catalog.your_schema.vendor_payments',
           'Vendor Payments', 'All vendor payment transactions with contract and PO references.',
           'Dataset', 'Finance', ARRAY['vendor','payments','procurement'], 'AP System', 'Weekly', 'datasteward@example.org', 'Confidential', NOW() - INTERVAL '3 days'),
          ('DP-004', NULL,
           'Operational KPI Dashboard', 'Executive dashboard showing service delivery metrics across all departments.',
           'Dashboard', 'Operations', ARRAY['dashboard','kpi','executive'], 'Databricks', 'Daily', 'datasteward@example.org', 'Internal', NOW() - INTERVAL '1 day'),
          ('DP-005', 'your_catalog.your_schema.employee_headcount',
           'Employee Headcount', 'Active employee counts by department, location, and classification.',
           'Dataset', 'HR', ARRAY['hr','headcount','workforce'], 'HRIS', 'Monthly', 'datasteward@example.org', 'Confidential', NOW() - INTERVAL '15 days'),
          ('DP-006', 'your_catalog.your_schema.service_requests',
           'Service Requests', 'Citizen and internal service requests with status tracking and SLA metrics.',
           'Dataset', 'Operations', ARRAY['service','requests','sla'], 'ServiceNow', 'Daily', 'datasteward@example.org', 'Internal', NOW() - INTERVAL '1 day'),
          ('DP-007', NULL,
           'Budget vs. Actuals Report', 'Automated report comparing approved budget to actual expenditure by quarter.',
           'Report', 'Finance', ARRAY['budget','report','quarterly'], 'ERP', 'Quarterly', 'datasteward@example.org', 'Internal', NOW() - INTERVAL '45 days'),
          ('DP-008', 'your_catalog.your_schema.it_asset_inventory',
           'IT Asset Inventory', 'Complete inventory of hardware, software, and cloud assets with lifecycle status.',
           'Dataset', 'IT', ARRAY['assets','inventory','it'], 'CMDB', 'Weekly', 'datasteward@example.org', 'Internal', NOW() - INTERVAL '4 days')
        ON CONFLICT (product_ref) DO NOTHING
      `);

      await query(`
        INSERT INTO access_requests (request_ref, product_id, requester_id, requester_team, business_reason, access_level, status)
        SELECT 'REQ-001',
               (SELECT product_id FROM data_products WHERE product_ref = 'DP-002'),
               (SELECT user_id FROM users WHERE email = 'analyst@example.org'),
               'Finance',
               'Need customer data for quarterly churn analysis report.',
               'Read Only', 'Pending'
        WHERE NOT EXISTS (SELECT 1 FROM access_requests WHERE request_ref = 'REQ-001')
      `);

      await query(`
        INSERT INTO audit_log (event_type, actor_email, target_name, metadata) VALUES
          ('REQUEST_SUBMITTED', 'analyst@example.org', 'REQ-001',
           '{"productRef":"DP-002","reason":"Quarterly churn analysis"}')
        ON CONFLICT DO NOTHING
      `);

      const { rows: counts } = await query(`
        SELECT
          (SELECT COUNT(*) FROM data_products) AS products,
          (SELECT COUNT(*) FROM users)         AS users,
          (SELECT COUNT(*) FROM access_requests) AS requests
      `);
      console.log('[demo-seed] Seeded:', counts[0]);
      res.json({ success: true, counts: counts[0] });
    } catch (e) {
      console.error('[demo-seed]', e.message);
      res.status(500).json({ error: e.message });
    }
  });

  // ─── Demo Reset (admin only) ───────────────────────────────────────────────
  app.post('/api/portal/demo-reset', async (req, res) => {
    if (!DEMO_MODE) {
      return res.status(403).json({ error: 'Demo reset is disabled in production mode (DEMO_MODE=false).' });
    }
    try {
      const SEEDED_REFS = ['DP-001','DP-002','DP-003','DP-004','DP-005','DP-006',
                           'DP-007','DP-008','DP-009','DP-010','DP-011','DP-012'];

      // Clear request history, audit trail, and personal libraries — NOT users or published products
      await query(`DELETE FROM access_requests`);
      await query(`DELETE FROM audit_log`);
      await query(`DELETE FROM user_library`);

      // Remove any pending/rejected products that were added during demos (not seeded refs)
      await query(
        `DELETE FROM data_products
         WHERE COALESCE(status,'Published') IN ('Pending','Rejected')
           AND product_ref != ALL($1::text[])`,
        [SEEDED_REFS]
      );

      // Re-ensure the three seed users always exist (safe upsert — never deletes anyone)
      await query(`
        INSERT INTO users (email, display_name, role, department) VALUES
          ('analyst@example.org',     'Alex Analyst',   'analyst',   'Finance'),
          ('datasteward@example.org', 'Dana Steward',   'admin',   'Data Governance')
        ON CONFLICT (email) DO NOTHING
      `);

      const { rows: counts } = await query(`
        SELECT
          (SELECT COUNT(*) FROM access_requests) AS requests,
          (SELECT COUNT(*) FROM audit_log)       AS audit,
          (SELECT COUNT(*) FROM user_library)    AS library,
          (SELECT COUNT(*) FROM data_products)   AS products,
          (SELECT COUNT(*) FROM users)           AS users
      `);
      console.log('[demo-reset] Demo data cleared:', counts[0]);
      res.json({ success: true, counts: counts[0] });
    } catch (e) {
      console.error('[demo-reset]', e.message);
      res.status(500).json({ error: e.message });
    }
  });
}
