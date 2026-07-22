import { query } from '../db.js';
import { getUcAuth } from '../databricks.js';
import { httpsJsonRequest } from '../auth.js';

export function registerRoutes(app) {
  // ─── Ask Catalog — FMAPI semantic search over product metadata ───────────────
  app.post('/api/portal/ask-catalog', async (req, res) => {
    try {
      const { question } = req.body;
      if (!question?.trim()) return res.status(400).json({ error: 'question required' });

      // Fetch published products for context
      const { rows: products } = await query(`
        SELECT product_ref, display_name, description, domain, type, tags,
               source_system, classification, uc_full_name, owner_email
        FROM data_products
        WHERE is_active = TRUE AND COALESCE(status,'Published') = 'Published'
        ORDER BY display_name LIMIT 60
      `);

      if (!products.length) return res.json({ matches: [], question, reason: 'no_products' });

      // Build compact product list for the prompt
      const productList = products.map(p => {
        const tags = Array.isArray(p.tags) ? p.tags.join(', ')
                   : typeof p.tags === 'string' ? p.tags.replace(/[{}"]/g, '') : '';
        return `${p.product_ref} | ${p.display_name} | ${p.domain || 'Other'} | ${p.type || 'Dataset'} | ${(p.description || '').substring(0, 120)} | ${tags}`;
      }).join('\n');

      const prompt = `You are a data catalog assistant. A user is searching for data products.
Given the question below and the catalog of available data products, identify the 3-5 most relevant products.
For each match, write one sentence explaining why it is relevant to the user's question.

User question: "${question}"

Catalog (format: ref | name | domain | type | description | tags):
${productList}

Respond with ONLY a valid JSON array, no other text:
[{"ref":"DP-001","name":"Product Name","reason":"One sentence why relevant."}]
If nothing is relevant, return: []`;

      const { host, token } = await getUcAuth();
      const fmResp = await httpsJsonRequest({
        hostname: host.replace(/^https?:\/\//, ''),
        path: '/serving-endpoints/databricks-meta-llama-3-3-70b-instruct/invocations',
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: prompt }],
          max_tokens: 512,
          temperature: 0.1
        }),
        timeoutMs: 25000
      });

      const raw = fmResp.data?.choices?.[0]?.message?.content || '[]';
      const jsonMatch = raw.match(/\[[\s\S]*\]/);
      let matches = [];
      try { matches = jsonMatch ? JSON.parse(jsonMatch[0]) : []; } catch (_) {}

      // Enrich matches with full product row
      const enriched = matches
        .map(m => {
          const p = products.find(p => p.product_ref === m.ref);
          if (!p) return null;
          return {
            ref: m.ref,
            name: p.display_name,
            reason: m.reason,
            domain: p.domain,
            type: p.type,
            classification: p.classification,
            uc_full_name: p.uc_full_name,
            source_system: p.source_system,
            tags: Array.isArray(p.tags) ? p.tags
                : typeof p.tags === 'string' ? p.tags.replace(/[{}"]/g,'').split(',').map(t=>t.trim()).filter(Boolean)
                : [],
          };
        })
        .filter(Boolean);

      res.json({ matches: enriched, question });
    } catch (e) {
      console.error('[ask-catalog]', e.message);
      res.status(500).json({ error: e.message });
    }
  });
}
