"""
Setup script to create and seed UC tables for the Supervisor agent's sub-agents.

Creates 6 tables in serverless_dxukih_catalog.agents:
  - expert_transcripts  (research sub-agent)
  - experts             (expert_finder sub-agent)
  - call_metrics        (analytics sub-agent)
  - engagement_summary  (analytics sub-agent)
  - restricted_list     (compliance sub-agent)
  - nda_registry        (compliance sub-agent)

Usage:
    python setup_tables.py --profile fe-vm-serverless-dxukih
    python setup_tables.py --profile fe-vm-serverless-dxukih --drop
    python setup_tables.py --profile fe-vm-serverless-dxukih --verify
"""

import argparse
import sys
import time

from databricks.sdk import WorkspaceClient


CATALOG = "serverless_dxukih_catalog"
SCHEMA = "agents"


# ---------------------------------------------------------------------------
# Table DDL
# ---------------------------------------------------------------------------

TABLES = {
    "expert_transcripts": """
CREATE TABLE IF NOT EXISTS {catalog}.{schema}.expert_transcripts (
    transcript_id STRING,
    expert_name STRING,
    topic STRING,
    transcript_excerpt STRING,
    interview_date DATE,
    relevance_score DOUBLE,
    sector STRING
)
""",
    "experts": """
CREATE TABLE IF NOT EXISTS {catalog}.{schema}.experts (
    expert_id STRING,
    name STRING,
    specialty STRING,
    interview_count INT,
    rating DOUBLE,
    topics STRING,
    bio STRING,
    region STRING
)
""",
    "call_metrics": """
CREATE TABLE IF NOT EXISTS {catalog}.{schema}.call_metrics (
    metric_date DATE,
    region STRING,
    call_count INT,
    avg_duration_min DOUBLE,
    segment STRING,
    revenue_usd DOUBLE
)
""",
    "engagement_summary": """
CREATE TABLE IF NOT EXISTS {catalog}.{schema}.engagement_summary (
    metric_name STRING,
    metric_value DOUBLE,
    period STRING,
    updated_at TIMESTAMP
)
""",
    "restricted_list": """
CREATE TABLE IF NOT EXISTS {catalog}.{schema}.restricted_list (
    entity_name STRING,
    restriction_type STRING,
    effective_date DATE,
    expiry_date DATE,
    reason STRING
)
""",
    "nda_registry": """
CREATE TABLE IF NOT EXISTS {catalog}.{schema}.nda_registry (
    expert_name STRING,
    nda_status STRING,
    effective_date DATE,
    expiry_date DATE,
    coverage_scope STRING
)
""",
}


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

SEED_DATA = {
    "expert_transcripts": """
INSERT INTO {catalog}.{schema}.expert_transcripts VALUES
('T-2025-1247', 'Dr. Sarah Chen', 'AI in Healthcare', 'We are seeing 40% year-over-year growth in AI-driven diagnostics adoption across tier-1 hospital systems. The key driver is FDA clearance of new radiology AI tools, which has accelerated trust among clinicians.', DATE '2025-01-15', 0.95, 'Healthcare'),
('T-2025-1248', 'Dr. Sarah Chen', 'Digital Health Regulation', 'The regulatory landscape is evolving faster than most health systems can adapt. We expect the EU AI Act to create a two-speed market: compliant vendors will gain share while others face exclusion.', DATE '2025-02-03', 0.88, 'Healthcare'),
('T-2025-1189', 'Michael Torres', 'Supply Chain Resilience', 'Leaders are prioritizing real-time visibility and transparency. The shift from just-in-time to just-in-case inventory models is costing 15-20% more but reducing disruption risk by 60%.', DATE '2025-01-22', 0.92, 'Supply Chain'),
('T-2025-1190', 'Michael Torres', 'Logistics Technology', 'Autonomous warehouse robotics reached an inflection point in Q4 2024. Companies deploying full-stack automation report 35% labor cost reduction with 2x throughput.', DATE '2025-02-10', 0.87, 'Supply Chain'),
('T-2025-1301', 'Dr. James Liu', 'Embedded Finance', 'Every SaaS platform is becoming a fintech company. We estimate embedded lending will grow from $33B to $68B by 2027, with vertical SaaS capturing the majority of new originations.', DATE '2025-01-28', 0.91, 'Fintech'),
('T-2025-1302', 'Dr. James Liu', 'Crypto Regulation', 'Institutional crypto adoption depends entirely on regulatory clarity. The MiCA framework in Europe has already driven 3x growth in compliant exchange volume.', DATE '2025-02-15', 0.84, 'Fintech'),
('T-2025-1303', 'Dr. James Liu', 'Digital Payments', 'Real-time payment rails are making batch processing obsolete. Countries with instant payment infrastructure see 22% higher digital commerce growth rates.', DATE '2025-03-01', 0.89, 'Fintech'),
('T-2025-1410', 'Rachel Martinez', 'Renewable Energy Transition', 'Grid-scale battery storage costs dropped 40% since 2022. We are now at the tipping point where solar-plus-storage is cheaper than natural gas peakers in 80% of US markets.', DATE '2025-01-10', 0.93, 'Energy'),
('T-2025-1411', 'Rachel Martinez', 'Carbon Markets', 'Voluntary carbon markets are consolidating rapidly. Only credits with rigorous MRV (measurement, reporting, verification) will retain value. We expect 50% of current credits to be worthless by 2027.', DATE '2025-02-20', 0.86, 'Energy'),
('T-2025-1520', 'David Kim', 'AI Security Threats', 'Adversarial AI attacks increased 300% in 2024. The most concerning vector is prompt injection in enterprise LLM deployments, which can exfiltrate sensitive data through seemingly benign queries.', DATE '2025-01-18', 0.94, 'Cybersecurity'),
('T-2025-1521', 'David Kim', 'Zero Trust Architecture', 'Enterprises adopting zero-trust report 68% fewer breach incidents. But implementation remains slow: only 12% of Fortune 500 companies have fully deployed ZTNA across all workloads.', DATE '2025-02-05', 0.90, 'Cybersecurity'),
('T-2025-1522', 'David Kim', 'Cloud Security Posture', 'Misconfigured cloud resources remain the number one cause of data breaches. Automated CSPM tools now detect 95% of misconfigurations, but remediation still averages 72 hours.', DATE '2025-03-10', 0.88, 'Cybersecurity'),
('T-2025-1630', 'Dr. Priya Patel', 'GLP-1 Market Dynamics', 'The GLP-1 market will exceed $100B by 2028. Supply chain constraints are the binding factor: active ingredient manufacturing capacity needs to triple to meet demand.', DATE '2025-01-25', 0.96, 'Healthcare'),
('T-2025-1631', 'Dr. Priya Patel', 'Biosimilar Competition', 'Biosimilar penetration in the US reached 40% for infused biologics but only 15% for self-administered products. Distribution complexity is the key barrier.', DATE '2025-02-12', 0.85, 'Healthcare'),
('T-2025-1740', 'Alex Novak', 'Retail Media Networks', 'Retail media ad spend will surpass $60B in 2025. The ROI advantage over traditional digital ads is 2.3x, driven by closed-loop attribution and first-party data.', DATE '2025-01-30', 0.91, 'Retail'),
('T-2025-1741', 'Alex Novak', 'Unified Commerce', 'Omnichannel retailers with unified inventory systems see 25% higher conversion rates. The gap between leaders and laggards is widening as technology costs decrease.', DATE '2025-02-18', 0.87, 'Retail'),
('T-2025-1850', 'Dr. Emily Watson', 'Climate Risk Modeling', 'Physical climate risk is being priced into commercial real estate for the first time. Properties in high-risk zones are seeing 8-15% valuation discounts, creating arbitrage opportunities for informed investors.', DATE '2025-02-01', 0.92, 'Climate/ESG'),
('T-2025-1851', 'Dr. Emily Watson', 'ESG Data Quality', 'Only 23% of corporate ESG disclosures meet institutional investor standards. The gap between reported and verified emissions data averages 35%, undermining portfolio decarbonization strategies.', DATE '2025-03-05', 0.89, 'Climate/ESG')
""",
    "experts": """
INSERT INTO {catalog}.{schema}.experts VALUES
('EXP-001', 'Dr. Sarah Chen', 'Healthcare AI & Digital Health', 23, 4.9, 'AI in healthcare, digital health regulation, clinical AI adoption, FDA approval processes', 'Former Chief Medical Officer at HealthTech Ventures. 15 years in healthcare technology strategy. Published 40+ papers on clinical AI validation.', 'North America'),
('EXP-002', 'Michael Torres', 'Supply Chain Analytics', 18, 4.8, 'supply chain resilience, logistics technology, warehouse automation, inventory optimization', 'VP of Supply Chain Innovation at a Fortune 100 retailer. Led digital transformation reducing fulfillment costs by 30%. MIT Supply Chain Management graduate.', 'North America'),
('EXP-003', 'Dr. James Liu', 'Fintech & Digital Payments', 21, 4.7, 'embedded finance, crypto regulation, digital payments, real-time payment rails, DeFi', 'Partner at Fintech Capital Partners. Previously Head of Strategy at a top-3 payment processor. PhD in Financial Engineering from Stanford.', 'Asia Pacific'),
('EXP-004', 'Rachel Martinez', 'Energy Transition & Sustainability', 15, 4.8, 'renewable energy, carbon markets, grid-scale storage, energy policy, clean tech investment', 'Managing Director at GreenShift Advisory. 20 years in energy markets including roles at two major energy companies. Board member of the Clean Energy Council.', 'Europe'),
('EXP-005', 'David Kim', 'Cybersecurity & AI Security', 19, 4.9, 'AI security threats, zero trust architecture, cloud security, adversarial AI, threat intelligence', 'Former CISO at a global bank. Founded a cybersecurity AI startup (acquired). CISSP, CISM certified. Regular speaker at Black Hat and RSA Conference.', 'North America'),
('EXP-006', 'Dr. Priya Patel', 'Pharma & Biotech', 14, 4.6, 'GLP-1 therapeutics, biosimilar markets, drug pricing, pharmaceutical supply chain, clinical trials', 'Chief Strategy Officer at a mid-cap biotech firm. Former McKinsey healthcare practice leader. MD/MBA from Johns Hopkins.', 'North America'),
('EXP-007', 'Alex Novak', 'Retail & Consumer Tech', 16, 4.5, 'retail media networks, unified commerce, consumer behavior, e-commerce, personalization', 'Head of Digital Commerce at a major department store chain. Previously at Amazon Retail division. Known for pioneering retail media strategies.', 'Europe'),
('EXP-008', 'Dr. Emily Watson', 'Climate Risk & ESG', 12, 4.7, 'climate risk modeling, ESG data quality, sustainable finance, carbon accounting, green bonds', 'Director of Climate Analytics at a global asset manager. PhD in Environmental Economics from LSE. Advisor to UN PRI on climate disclosure standards.', 'Europe')
""",
    "call_metrics": None,  # generated programmatically
    "engagement_summary": """
INSERT INTO {catalog}.{schema}.engagement_summary VALUES
('total_calls_90d', 2847, 'last_90_days', CURRENT_TIMESTAMP()),
('avg_duration_min', 52.3, 'last_90_days', CURRENT_TIMESTAMP()),
('month_over_month_growth_pct', 18.2, 'last_30_days', CURRENT_TIMESTAMP()),
('unique_experts_engaged', 87, 'last_90_days', CURRENT_TIMESTAMP()),
('unique_clients', 142, 'last_90_days', CURRENT_TIMESTAMP()),
('repeat_engagement_rate_pct', 64.5, 'last_90_days', CURRENT_TIMESTAMP()),
('avg_client_satisfaction', 4.6, 'last_90_days', CURRENT_TIMESTAMP()),
('revenue_per_call_usd', 1250.0, 'last_90_days', CURRENT_TIMESTAMP()),
('total_revenue_usd', 3558750.0, 'last_90_days', CURRENT_TIMESTAMP()),
('healthcare_segment_pct', 34.2, 'last_90_days', CURRENT_TIMESTAMP()),
('technology_segment_pct', 28.7, 'last_90_days', CURRENT_TIMESTAMP()),
('finance_segment_pct', 22.1, 'last_90_days', CURRENT_TIMESTAMP())
""",
    "restricted_list": """
INSERT INTO {catalog}.{schema}.restricted_list VALUES
('Acme Corp', 'trading', DATE '2025-06-01', DATE '2026-12-31', 'Active M&A proceedings - material non-public information'),
('GlobalPharma Inc', 'regulatory', DATE '2025-09-15', DATE '2026-08-15', 'FDA advisory committee review pending'),
('TechVentures LLC', 'nda', DATE '2025-01-01', DATE '2027-01-01', 'Exclusive consulting agreement with competitor'),
('EnergyFirst Holdings', 'trading', DATE '2025-10-01', DATE '2026-09-01', 'Pending regulatory approval for acquisition'),
('CryptoExchange Global', 'regulatory', DATE '2025-08-15', DATE '2026-07-15', 'SEC enforcement investigation ongoing'),
('MedDevice Partners', 'nda', DATE '2025-03-01', DATE '2026-11-01', 'Confidential product development partnership')
""",
    "nda_registry": """
INSERT INTO {catalog}.{schema}.nda_registry VALUES
('Dr. Sarah Chen', 'active', DATE '2024-01-01', DATE '2026-01-01', 'Healthcare technology and AI diagnostics'),
('Michael Torres', 'active', DATE '2024-03-15', DATE '2026-03-15', 'Supply chain and logistics operations'),
('Dr. James Liu', 'active', DATE '2024-06-01', DATE '2026-06-01', 'Financial technology and payments'),
('Rachel Martinez', 'active', DATE '2024-02-01', DATE '2026-02-01', 'Energy markets and sustainability'),
('David Kim', 'active', DATE '2024-04-01', DATE '2026-04-01', 'Cybersecurity and threat intelligence'),
('Dr. Priya Patel', 'active', DATE '2024-07-01', DATE '2026-07-01', 'Pharmaceutical and biotech markets'),
('Alex Novak', 'expired', DATE '2023-01-01', DATE '2025-01-01', 'Retail technology and e-commerce'),
('Dr. Emily Watson', 'pending', DATE '2025-04-01', DATE '2027-04-01', 'Climate risk and ESG analytics')
""",
}


def _call_metrics_seed_sql() -> str:
    """Generate ~90 rows of call_metrics covering 90 days across regions/segments."""
    regions = ["North America", "Europe", "Asia Pacific", "Latin America"]
    segments = ["Healthcare", "Technology", "Finance"]

    rows = []
    import random
    random.seed(42)

    for day_offset in range(0, 90, 3):  # every 3 days = ~30 rows per region*segment combo
        for region in regions:
            for segment in segments:
                base_calls = {"North America": 12, "Europe": 9, "Asia Pacific": 7, "Latin America": 4}
                base_rev = {"Healthcare": 1400, "Technology": 1200, "Finance": 1500}

                call_count = base_calls[region] + random.randint(-3, 5)
                avg_dur = round(45 + random.uniform(-10, 15), 1)
                rev = round(base_rev[segment] * call_count * (0.85 + random.uniform(0, 0.3)), 2)

                rows.append(
                    f"(DATE_ADD(CURRENT_DATE(), -{90 - day_offset}), "
                    f"'{region}', {call_count}, {avg_dur}, '{segment}', {rev})"
                )

    # batch into chunks of 50 to avoid overly long statements
    chunks = [rows[i:i + 50] for i in range(0, len(rows), 50)]
    statements = []
    for chunk in chunks:
        statements.append(
            f"INSERT INTO {{catalog}}.{{schema}}.call_metrics VALUES\n"
            + ",\n".join(chunk)
        )
    return statements


# ---------------------------------------------------------------------------
# Expected row counts for verification
# ---------------------------------------------------------------------------

EXPECTED_COUNTS = {
    "expert_transcripts": 18,
    "experts": 8,
    "call_metrics": 360,  # approximate: 30 date points * 4 regions * 3 segments
    "engagement_summary": 12,
    "restricted_list": 6,
    "nda_registry": 8,
}


# ---------------------------------------------------------------------------
# Execution helpers
# ---------------------------------------------------------------------------

def get_warehouse_id(ws: WorkspaceClient) -> str:
    """Get a serverless SQL warehouse ID."""
    for wh in ws.warehouses.list():
        if wh.enable_serverless_compute:
            return wh.id
    first = next(iter(ws.warehouses.list()), None)
    if first:
        return first.id
    raise RuntimeError("No SQL warehouse available")


def execute_sql(ws: WorkspaceClient, warehouse_id: str, statement: str, label: str = ""):
    """Execute a SQL statement and wait for completion."""
    result = ws.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=statement,
        wait_timeout="50s",
    )
    status = result.status
    if status and status.state:
        state = status.state.value if hasattr(status.state, "value") else str(status.state)
    else:
        state = "UNKNOWN"

    if state not in ("SUCCEEDED", "CLOSED"):
        error_msg = ""
        if status and status.error:
            error_msg = f" — {status.error.message}"
        raise RuntimeError(f"{label}: statement failed with state {state}{error_msg}")
    return result


def create_tables(ws: WorkspaceClient, warehouse_id: str, drop: bool = False):
    """Create all 6 tables (optionally dropping first)."""
    if drop:
        for table_name in TABLES:
            print(f"  Dropping {CATALOG}.{SCHEMA}.{table_name}...")
            execute_sql(
                ws, warehouse_id,
                f"DROP TABLE IF EXISTS {CATALOG}.{SCHEMA}.{table_name}",
                label=f"drop {table_name}",
            )

    for table_name, ddl in TABLES.items():
        print(f"  Creating {CATALOG}.{SCHEMA}.{table_name}...")
        execute_sql(
            ws, warehouse_id,
            ddl.format(catalog=CATALOG, schema=SCHEMA),
            label=f"create {table_name}",
        )


def seed_tables(ws: WorkspaceClient, warehouse_id: str):
    """Insert seed data into all tables."""
    for table_name, insert_sql in SEED_DATA.items():
        if table_name == "call_metrics":
            # call_metrics uses programmatic generation
            statements = _call_metrics_seed_sql()
            for i, stmt in enumerate(statements):
                print(f"  Seeding {CATALOG}.{SCHEMA}.call_metrics (batch {i+1}/{len(statements)})...")
                execute_sql(
                    ws, warehouse_id,
                    stmt.format(catalog=CATALOG, schema=SCHEMA),
                    label=f"seed call_metrics batch {i+1}",
                )
        else:
            print(f"  Seeding {CATALOG}.{SCHEMA}.{table_name}...")
            execute_sql(
                ws, warehouse_id,
                insert_sql.format(catalog=CATALOG, schema=SCHEMA),
                label=f"seed {table_name}",
            )


def verify_tables(ws: WorkspaceClient, warehouse_id: str):
    """Verify row counts for all tables."""
    all_ok = True
    for table_name, expected in EXPECTED_COUNTS.items():
        fqn = f"{CATALOG}.{SCHEMA}.{table_name}"
        result = execute_sql(ws, warehouse_id, f"SELECT COUNT(*) FROM {fqn}", label=f"count {table_name}")
        count = int(result.result.data_array[0][0]) if result.result and result.result.data_array else 0
        status = "OK" if count >= expected * 0.8 else "LOW"
        if status == "LOW":
            all_ok = False
        print(f"  {fqn}: {count} rows (expected ~{expected}) [{status}]")

    return all_ok


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Setup UC tables for Supervisor sub-agents")
    parser.add_argument("--profile", default="fe-vm-serverless-dxukih", help="Databricks CLI profile")
    parser.add_argument("--drop", action="store_true", help="Drop tables before recreating")
    parser.add_argument("--verify", action="store_true", help="Only verify existing tables")
    args = parser.parse_args()

    print(f"Connecting with profile: {args.profile}")
    ws = WorkspaceClient(profile=args.profile)
    warehouse_id = get_warehouse_id(ws)
    print(f"Using warehouse: {warehouse_id}\n")

    if args.verify:
        print("Verifying tables...")
        ok = verify_tables(ws, warehouse_id)
        sys.exit(0 if ok else 1)

    print("Creating tables...")
    create_tables(ws, warehouse_id, drop=args.drop)
    print()

    print("Seeding data...")
    seed_tables(ws, warehouse_id)
    print()

    print("Verifying...")
    verify_tables(ws, warehouse_id)
    print("\nDone!")


if __name__ == "__main__":
    main()
