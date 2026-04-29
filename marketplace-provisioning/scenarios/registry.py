"""
Scenario registry — maps display names to directory keys, catalog names, and answer keys.
"""

MYSTERIES = [
    "HR — The Talent Drain",
    "Marketing — The Budget Drain",
    "Operations — The Late Shipments",
    "Financial Planning — The Budget Overrun",
]

SCENARIOS = {
    "HR — The Talent Drain": {
        "key": "HR",
        "catalog_name": "hr_talent",
    },
    "Marketing — The Budget Drain": {
        "key": "marketing",
        "catalog_name": "mkt_budget",
    },
    "Operations — The Late Shipments": {
        "key": "operations",
        "catalog_name": "ops_shipments",
    },
    "Financial Planning — The Budget Overrun": {
        "key": "financial-planning",
        "catalog_name": "finplan_budget",
    },
}

MYSTERY_ANSWER_KEYS = {
    "HR — The Talent Drain": {
        "root_cause": (
            "A high-performing manager in the Southwest region left the company in July. "
            "11 of their 14 direct reports resigned within the following 60 days."
        ),
        "scoring_context": (
            "The misleading signal is that compensation data shows a company-wide salary lag "
            "vs. market benchmarks — plausible as a cause, but the lag is consistent across all "
            "regions and does not correlate with the turnover spike. The real pattern is geographic "
            "and manager-specific, not compensation-driven."
        ),
        "sample_recommendation": (
            "Implement a manager-dependency risk assessment across all regions. When a manager "
            "with high team retention influence gives notice, immediately activate a retention "
            "task force for their direct reports — including stay interviews, accelerated "
            "promotion reviews, and temporary skip-level mentorship. Additionally, build a "
            "succession pipeline so no single manager becomes a single point of failure for "
            "team stability."
        ),
        "query_path": [
            "Review company-wide voluntary turnover rate by quarter — Q3 shows a notable spike but variance is within arguable range.",
            "Break turnover by region — Southwest is elevated but not dramatically so at first glance.",
            "Filter Southwest by department and manager — one team shows 11 resignations clustered within a 60-day window.",
            "Cross-reference resignation dates against manager departure date — the pattern originates the week the manager left.",
        ],
    },
    "Marketing — The Budget Drain": {
        "root_cause": (
            "A paid search campaign had its audience targeting misconfigured — set to all ages "
            "and all geographies instead of the defined ICP. It generated high click volume from "
            "a demographic that has never converted, inflating spend with no return."
        ),
        "scoring_context": (
            "The misleading signal is that blended CPM rates rose ~15% over the period, consistent "
            "with industry benchmarks — which makes the cost increase appear to be an external "
            "market condition rather than an internal targeting error. The real issue is one "
            "misconfigured campaign, not market-wide CPM inflation."
        ),
        "sample_recommendation": (
            "Immediately correct the audience targeting on the misconfigured campaign to match "
            "the defined ICP. Implement a campaign launch checklist that requires a second reviewer "
            "to verify targeting parameters before any campaign goes live. Set up automated alerts "
            "when a campaign's conversion rate drops below a threshold relative to its spend, so "
            "misconfigurations are caught within days, not quarters."
        ),
        "query_path": [
            "Review total ad spend vs. conversions by month — spend is up, conversions are flat, but the ratio looks like a market efficiency issue.",
            "Break spend by campaign — one paid search campaign accounts for a disproportionate share of spend and clicks.",
            "Segment that campaign's clicks by audience demographic and geography — traffic is overwhelmingly outside the defined ICP.",
            "Compare conversion rate for that audience segment vs. historical ICP benchmarks — the segment converts at near zero, confirming a targeting misconfiguration.",
        ],
    },
    "Operations — The Late Shipments": {
        "root_cause": (
            "A single 3PL partner responsible for oversized and heavy SKUs has a 67% late delivery "
            "rate. Because that partner handles only 12% of total order volume, the issue is "
            "invisible in aggregate — but it accounts for 41% of all customer complaints."
        ),
        "scoring_context": (
            "The misleading signal is that Q2 included two major holidays, which caused a visible "
            "but proportional slowdown across all fulfillment partners — making it appear to be a "
            "seasonal issue rather than a partner-specific failure. The real issue is isolated to "
            "one 3PL and one product category."
        ),
        "sample_recommendation": (
            "Place the underperforming 3PL on a 30-day performance improvement plan with a "
            "target on-time rate of 90%+. In parallel, begin onboarding a backup fulfillment "
            "partner for oversized/heavy SKUs. Implement per-partner SLA dashboards with "
            "automated alerting when any single partner's late rate exceeds 15%, so issues "
            "are flagged before they reach customers at scale."
        ),
        "query_path": [
            "Review aggregate on-time delivery rate and CSAT scores by month — overall delivery looks acceptable, but CSAT decline is sharper than delivery metrics suggest.",
            "Join CSAT responses to orders and segment complaints by product category — oversized/heavy items are overrepresented in negative responses.",
            "Filter orders for that product category by fulfillment partner — a single 3PL is handling the majority of those SKUs.",
            "Calculate on-time delivery rate for that partner in isolation — 67% late rate confirms the partner is the root cause, masked by low overall volume share.",
        ],
    },
    "Financial Planning — The Budget Overrun": {
        "root_cause": (
            "Several one-time project costs were approved mid-quarter through an exception process "
            "and coded to a shared overhead cost center rather than the originating departments. "
            "Because the charges do not appear in any department's budget view, no individual owner "
            "flagged them — but they accumulated to a material overage at the company level. The "
            "exception approval workflow has no budget-check gate, so each request appeared "
            "reasonable in isolation."
        ),
        "scoring_context": (
            "The misleading signal is that headcount-related costs rose modestly in Q3 due to a "
            "hiring push, which is real and documentable and naturally attracts attention as the "
            "likely culprit — but accounts for only 4 of the 18 percentage points of overage. The "
            "real cause is exception-approved project costs miscoded to shared overhead."
        ),
        "sample_recommendation": (
            "Add a budget-check gate to the exception approval workflow so each request is validated "
            "against the originating department's remaining budget before approval. Require that "
            "exception-approved costs are posted to the originating department's cost center, not "
            "shared overhead, so department heads have visibility into their true spend. Implement "
            "a monthly reconciliation of shared overhead balances to flag unexpected accumulations "
            "before they reach material levels."
        ),
        "query_path": [
            "Review total opex budget vs. actual by quarter — Q3 shows an 18% overage at the company level, but the variance is not visible in any individual department's budget report.",
            "Break actual spend by cost center — a shared overhead cost center shows a large, unexplained balance with no corresponding budget allocation, while all departmental cost centers are within range.",
            "Pull GL transactions posted to the shared overhead cost center — the charges are a collection of one-time project costs from multiple departments, each approved individually through an exception process.",
            "Join exception approval records to the GL transactions — each charge was approved without a budget-check gate, and the originating department is captured in the approval record but was not used as the posting cost center, confirming the miscoding as the root cause.",
        ],
    },
}
