#!/usr/bin/env python3
"""
Generate ABAC masking_functions.sql and terraform.tfvars from table DDL files.

Reads DDL files from a folder, combines them with the ABAC prompt template,
sends to an LLM, and writes the generated output files.  Optionally runs
validate_abac.py on the result.

Authentication:
  The script reads auth.auto.tfvars (or --auth-file) to get Databricks
  credentials and catalog/schema.  This means --catalog and --schema are
  optional when auth.auto.tfvars is populated.

Supported LLM providers:
  - databricks (default) — Claude Sonnet via Databricks Foundation Model API
  - anthropic            — Claude via the Anthropic API
  - openai               — GPT-4o / o1 via OpenAI API

Usage:
  # One-time setup
  cp auth.auto.tfvars.example auth.auto.tfvars   # fill in credentials

  # Put DDL files (one or many) in the ddl/ folder
  mkdir -p ddl/
  cp my_tables.sql ddl/

  # Generate (reads catalog/schema from auth.auto.tfvars)
  python generate_abac.py

  # Or override catalog/schema explicitly
  python generate_abac.py --catalog my_catalog --schema my_schema

  # Use a specific provider / model
  python generate_abac.py --provider anthropic --model claude-sonnet-4-20250514

  # Custom DDL folder and output directory
  python generate_abac.py --ddl-dir ./my_ddls --out-dir ./my_output
"""

import argparse
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROMPT_TEMPLATE_PATH = SCRIPT_DIR / "ABAC_PROMPT.md"
DEFAULT_AUTH_FILE = SCRIPT_DIR / "auth.auto.tfvars"


def load_auth_config(auth_file: Path) -> dict:
    """Load auth config from a .tfvars file. Returns empty dict if not found."""
    if not auth_file.exists():
        return {}
    try:
        import hcl2
    except ImportError:
        print("  WARNING: python-hcl2 not installed — cannot read auth file.")
        print("  Install with: pip install python-hcl2")
        return {}
    try:
        with open(auth_file) as f:
            cfg = hcl2.load(f)
        non_empty = {k: v for k, v in cfg.items() if v}
        if non_empty:
            print(f"  Loaded auth from: {auth_file}")
            if "uc_catalog_name" in non_empty:
                print(f"    catalog: {non_empty['uc_catalog_name']}")
            if "uc_schema_name" in non_empty:
                print(f"    schema:  {non_empty['uc_schema_name']}")
        return cfg
    except Exception as e:
        print(f"  WARNING: Failed to parse {auth_file}: {e}")
        return {}


def configure_databricks_env(auth_cfg: dict):
    """Set Databricks SDK env vars from auth config if not already set."""
    mapping = {
        "databricks_workspace_host": "DATABRICKS_HOST",
        "databricks_client_id": "DATABRICKS_CLIENT_ID",
        "databricks_client_secret": "DATABRICKS_CLIENT_SECRET",
    }
    for tfvar_key, env_key in mapping.items():
        val = auth_cfg.get(tfvar_key, "")
        if val and not os.environ.get(env_key):
            os.environ[env_key] = val


def load_ddl_files(ddl_dir: Path) -> str:
    """Read all .sql files from ddl_dir and concatenate them."""
    sql_files = sorted(ddl_dir.glob("*.sql"))
    if not sql_files:
        print(f"ERROR: No .sql files found in {ddl_dir}")
        print("  Place your CREATE TABLE / DESCRIBE TABLE DDL in .sql files there.")
        sys.exit(1)

    parts = []
    for f in sql_files:
        content = f.read_text().strip()
        if content:
            parts.append(f"-- Source: {f.name}\n{content}")
            print(f"  Loaded DDL: {f.name} ({len(content)} chars)")

    combined = "\n\n".join(parts)
    print(f"  Total DDL: {len(combined)} chars from {len(sql_files)} file(s)\n")
    return combined


def build_prompt(catalog: str, schema: str, ddl_text: str) -> str:
    """Build the full prompt by injecting catalog/schema/DDL into the template."""
    template = PROMPT_TEMPLATE_PATH.read_text()

    section_marker = "### MY CATALOG AND SCHEMA"
    idx = template.find(section_marker)
    if idx == -1:
        print("WARNING: Could not find '### MY CATALOG AND SCHEMA' in ABAC_PROMPT.md")
        print("  Appending DDL at the end of the prompt instead.\n")
        prompt = template + f"\n\nCatalog: {catalog}\nSchema: {schema}\n\n{ddl_text}\n"
    else:
        prompt_body = template[:idx].rstrip()
        user_input = (
            f"\n\n### MY CATALOG AND SCHEMA\n\n"
            f"```\nCatalog: {catalog}\nSchema:  {schema}\n```\n\n"
            f"### MY TABLES\n\n```sql\n{ddl_text}\n```\n"
        )
        prompt = prompt_body + user_input

    return prompt


def extract_code_blocks(response_text: str) -> tuple[str | None, str | None]:
    """Extract the SQL and HCL code blocks from the LLM response."""
    sql_block = None
    hcl_block = None

    blocks = re.findall(r"```(\w*)\n(.*?)```", response_text, re.DOTALL)

    for lang, content in blocks:
        content = content.strip()
        lang_lower = lang.lower()

        if lang_lower == "sql" and sql_block is None:
            sql_block = content
        elif lang_lower in ("hcl", "terraform") and hcl_block is None:
            hcl_block = content
        elif not lang and sql_block is None and "CREATE" in content.upper() and "FUNCTION" in content.upper():
            sql_block = content
        elif not lang and hcl_block is None and "groups" in content and "tag_policies" in content:
            hcl_block = content

    return sql_block, hcl_block


TFVARS_STRIP_KEYS = {
    "databricks_account_id",
    "databricks_client_id",
    "databricks_client_secret",
    "databricks_workspace_id",
    "databricks_workspace_host",
    "uc_catalog_name",
    "uc_schema_name",
}


def sanitize_tfvars_hcl(hcl_block: str) -> str:
    """
    Make AI-generated tfvars easier and safer to use:
    - Strip auth + catalog/schema variables (these come from auth.auto.tfvars)
    - Insert section-level explanations and doc links
    """

    # --- Strip auth fields (and common adjacent headers) ---
    stripped_lines: list[str] = []
    for line in hcl_block.splitlines():
        # Drop common header line(s) that introduce auth vars
        if re.match(r"^\s*#\s*Authentication\b", line, re.IGNORECASE):
            continue
        if re.match(r"^\s*#\s*Databricks\s+Authentication\b", line, re.IGNORECASE):
            continue

        m = re.match(r"^\s*([A-Za-z0-9_]+)\s*=", line)
        if m and m.group(1) in TFVARS_STRIP_KEYS:
            continue

        stripped_lines.append(line)

    # Collapse excessive blank lines
    compact: list[str] = []
    last_blank = False
    for line in stripped_lines:
        blank = line.strip() == ""
        if blank and last_blank:
            continue
        compact.append(line)
        last_blank = blank

    text = "\n".join(compact).strip() + "\n"

    # --- Insert explanatory blocks before major sections ---
    docs = (
        "# Docs:\n"
        "# - Governed tags / tag policies: https://docs.databricks.com/en/database-objects/tags.html\n"
        "# - Unity Catalog ABAC overview: https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac\n"
        "# - ABAC policies (masks + filters): https://docs.databricks.com/aws/en/data-governance/unity-catalog/abac/policies\n"
        "# - Row filters + column masks: https://docs.databricks.com/en/tables/row-and-column-filters.html\n"
        "#\n"
    )

    groups_block = (
        "# ----------------------------------------------------------------------------\n"
        "# Groups (business roles)\n"
        "# ----------------------------------------------------------------------------\n"
        "# Keys are group names. Use these to represent business personas (e.g., Analyst,\n"
        "# Researcher, Compliance). These groups are used for workspace onboarding,\n"
        "# Databricks One consumer access, data grants, and optional Genie Space ACLs.\n"
        "#\n"
        + docs
    )

    tag_policies_block = (
        "# ----------------------------------------------------------------------------\n"
        "# Tag policies (governed tags)\n"
        "# ----------------------------------------------------------------------------\n"
        "# Each entry defines a governed tag key and the allowed values. You’ll assign\n"
        "# these tags to tables/columns below, then reference them in FGAC policies.\n"
        "#\n"
        + docs
    )

    tag_assignments_block = (
        "# ----------------------------------------------------------------------------\n"
        "# Tag assignments (classify tables/columns)\n"
        "# ----------------------------------------------------------------------------\n"
        "# Apply governed tags to Unity Catalog objects.\n"
        "# - entity_type: \"tables\" or \"columns\"\n"
        "# - entity_name: relative to uc_catalog_name.uc_schema_name\n"
        "#   - table:  \"Customers\"\n"
        "#   - column: \"Customers.SSN\"   (format: Table.Column)\n"
        "#\n"
        + docs
    )

    fgac_block = (
        "# ----------------------------------------------------------------------------\n"
        "# FGAC policies (who sees what, and how)\n"
        "# ----------------------------------------------------------------------------\n"
        "# Each entry creates either a COLUMN MASK or ROW FILTER policy.\n"
        "#\n"
        "# Common fields:\n"
        "# - name: logical name for the policy (must be unique)\n"
        "# - policy_type: POLICY_TYPE_COLUMN_MASK | POLICY_TYPE_ROW_FILTER\n"
        "# - to_principals: list of group names who receive this policy\n"
        "# - except_principals: optional list of groups excluded (break-glass/admin)\n"
        "# - comment: human-readable intent (recommended)\n"
        "#\n"
        "# For COLUMN MASK:\n"
        "# - match_condition: ABAC condition, e.g. hasTagValue('phi_level','full_phi')\n"
        "# - match_alias: the column alias used by the ABAC engine\n"
        "# - function_name: masking UDF name (relative; Terraform prefixes catalog.schema)\n"
        "#\n"
        "# For ROW FILTER:\n"
        "# - when_condition: ABAC condition controlling where the row filter applies\n"
        "# - function_name: row filter UDF name (relative; must be zero-argument)\n"
        "#\n"
        "# Example \u2014 column mask (mask SSN for analysts, exempt compliance):\n"
        "#   {\n"
        "#     name              = \"mask_ssn_analysts\"\n"
        "#     policy_type       = \"POLICY_TYPE_COLUMN_MASK\"\n"
        "#     to_principals     = [\"Junior_Analyst\", \"Senior_Analyst\"]\n"
        "#     except_principals = [\"Compliance_Officer\"]\n"
        "#     comment           = \"Mask SSN showing only last 4 digits\"\n"
        "#     match_condition   = \"hasTagValue('pii_level', 'highly_sensitive')\"\n"
        "#     match_alias       = \"masked_ssn\"\n"
        "#     function_name     = \"mask_ssn\"\n"
        "#   }\n"
        "#\n"
        "# Example \u2014 row filter (restrict regional staff to their rows):\n"
        "#   {\n"
        "#     name           = \"filter_us_region\"\n"
        "#     policy_type    = \"POLICY_TYPE_ROW_FILTER\"\n"
        "#     to_principals  = [\"US_Region_Staff\"]\n"
        "#     comment        = \"Only show rows where region = US\"\n"
        "#     when_condition = \"hasTagValue('region_scope', 'global')\"\n"
        "#     function_name  = \"filter_by_region_us\"\n"
        "#   }\n"
        "#\n"
        + docs
    )

    def insert_before(pattern: str, block: str, s: str) -> str:
        # Avoid double-inserting if the block already exists nearby
        if block.strip() in s:
            return s
        return re.sub(pattern, block + r"\g<0>", s, count=1, flags=re.MULTILINE)

    text = insert_before(r"^groups\s*=\s*\{", groups_block, text)
    text = insert_before(r"^tag_policies\s*=\s*\[", tag_policies_block, text)
    text = insert_before(r"^tag_assignments\s*=\s*\[", tag_assignments_block, text)
    text = insert_before(r"^fgac_policies\s*=\s*\[", fgac_block, text)

    return text


def call_anthropic(prompt: str, model: str) -> str:
    """Call Claude via the Anthropic API."""
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed. Run:")
        print("  pip install anthropic")
        sys.exit(2)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    print(f"  Calling Anthropic ({model})...")

    message = client.messages.create(
        model=model,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def call_openai(prompt: str, model: str) -> str:
    """Call GPT via the OpenAI API."""
    try:
        import openai
    except ImportError:
        print("ERROR: openai package not installed. Run:")
        print("  pip install openai")
        sys.exit(2)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set.")
        print("  export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)
    print(f"  Calling OpenAI ({model})...")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a Databricks Unity Catalog ABAC expert."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=8192,
    )
    return response.choices[0].message.content


def call_databricks(prompt: str, model: str) -> str:
    """Call a model via the Databricks Foundation Model API."""
    try:
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.service.serving import ChatMessage, ChatMessageRole
    except ImportError:
        print("ERROR: databricks-sdk package not installed. Run:")
        print("  pip install databricks-sdk")
        sys.exit(2)

    w = WorkspaceClient()
    print(f"  Calling Databricks FMAPI ({model})...")

    response = w.serving_endpoints.query(
        name=model,
        messages=[
            ChatMessage(role=ChatMessageRole.SYSTEM, content="You are a Databricks Unity Catalog ABAC expert."),
            ChatMessage(role=ChatMessageRole.USER, content=prompt),
        ],
        max_tokens=8192,
    )
    return response.choices[0].message.content


PROVIDERS = {
    "databricks": {
        "call": call_databricks,
        "default_model": "databricks-claude-sonnet-4",
    },
    "anthropic": {
        "call": call_anthropic,
        "default_model": "claude-sonnet-4-20250514",
    },
    "openai": {
        "call": call_openai,
        "default_model": "gpt-4o",
    },
}


class Spinner:
    """Simple terminal spinner for long-running operations."""

    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, message: str = "Working"):
        self._message = message
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_time = 0.0

    def __enter__(self):
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        if self._thread:
            self._thread.join()
        elapsed = time.time() - self._start_time
        sys.stderr.write(f"\r  {self._message} — done ({elapsed:.1f}s)\n")
        sys.stderr.flush()

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            elapsed = time.time() - self._start_time
            frame = self.FRAMES[i % len(self.FRAMES)]
            sys.stderr.write(f"\r  {frame} {self._message} ({elapsed:.0f}s)")
            sys.stderr.flush()
            i += 1
            self._stop.wait(0.1)


def call_with_retries(call_fn, prompt: str, model: str, max_retries: int) -> str:
    """Call an LLM provider with exponential backoff retries."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            with Spinner(f"Calling LLM (attempt {attempt}/{max_retries})"):
                return call_fn(prompt, model)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                wait = min(2 ** attempt, 60)
                print(f"\n  Attempt {attempt} failed: {e}")
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"\n  Attempt {attempt} failed: {e}")
    raise RuntimeError(f"All {max_retries} attempts failed. Last error: {last_error}")


def run_validation(out_dir: Path) -> bool:
    """Run validate_abac.py on the generated files. Returns True if passed."""
    validator = SCRIPT_DIR / "validate_abac.py"
    tfvars_path = out_dir / "terraform.tfvars"
    sql_path = out_dir / "masking_functions.sql"

    if not validator.exists():
        print("\n  [SKIP] validate_abac.py not found — skipping validation")
        return True

    cmd = [sys.executable, str(validator), str(tfvars_path)]
    if sql_path.exists():
        cmd.append(str(sql_path))

    print("\n  Running validation...\n")
    result = subprocess.run(cmd, cwd=str(SCRIPT_DIR))
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Generate ABAC configuration from table DDL using AI",
        epilog="Example: python generate_abac.py  (reads catalog/schema from auth.auto.tfvars)",
    )
    parser.add_argument("--catalog", help="Unity Catalog name (reads from auth.auto.tfvars if omitted)")
    parser.add_argument("--schema", help="Schema name (reads from auth.auto.tfvars if omitted)")
    parser.add_argument(
        "--auth-file",
        default=str(DEFAULT_AUTH_FILE),
        help="Path to auth tfvars file (default: auth.auto.tfvars)",
    )
    parser.add_argument(
        "--provider",
        choices=list(PROVIDERS.keys()),
        default="databricks",
        help="LLM provider (default: databricks)",
    )
    parser.add_argument("--model", help="Model name (defaults depend on provider)")
    parser.add_argument(
        "--ddl-dir",
        default=str(SCRIPT_DIR / "ddl"),
        help="Directory containing .sql DDL files (default: ./ddl/)",
    )
    parser.add_argument(
        "--out-dir",
        default=str(SCRIPT_DIR / "generated"),
        help="Output directory for generated files (default: ./generated/)",
    )
    parser.add_argument("--max-retries", type=int, default=3, help="Max LLM call attempts with exponential backoff (default: 3)")
    parser.add_argument("--skip-validation", action="store_true", help="Skip running validate_abac.py")
    parser.add_argument("--dry-run", action="store_true", help="Build the prompt and print it without calling the LLM")

    args = parser.parse_args()

    ddl_dir = Path(args.ddl_dir)
    out_dir = Path(args.out_dir)
    auth_file = Path(args.auth_file)

    print("=" * 60)
    print("  ABAC Configuration Generator")
    print("=" * 60)

    auth_cfg = load_auth_config(auth_file)

    catalog = args.catalog or auth_cfg.get("uc_catalog_name", "")
    schema = args.schema or auth_cfg.get("uc_schema_name", "")

    if not catalog:
        print("ERROR: --catalog not provided and uc_catalog_name not set in auth file.")
        print(f"  Either pass --catalog or set uc_catalog_name in {auth_file}")
        sys.exit(1)
    if not schema:
        print("ERROR: --schema not provided and uc_schema_name not set in auth file.")
        print(f"  Either pass --schema or set uc_schema_name in {auth_file}")
        sys.exit(1)

    if not ddl_dir.exists():
        print(f"\nERROR: DDL directory '{ddl_dir}' does not exist.")
        print(f"  mkdir -p {ddl_dir}")
        print("  # Then place your CREATE TABLE .sql files there")
        sys.exit(1)

    print(f"  Catalog:  {catalog}")
    print(f"  Schema:   {schema}")
    print(f"  Provider: {args.provider}")
    print(f"  DDL dir:  {ddl_dir}")
    print(f"  Out dir:  {out_dir}")
    print()

    ddl_text = load_ddl_files(ddl_dir)
    prompt = build_prompt(catalog, schema, ddl_text)

    if args.dry_run:
        print("=" * 60)
        print("  DRY RUN — Prompt that would be sent:")
        print("=" * 60)
        print(prompt)
        sys.exit(0)

    if args.provider == "databricks":
        configure_databricks_env(auth_cfg)

    provider_cfg = PROVIDERS[args.provider]
    model = args.model or provider_cfg["default_model"]
    call_fn = provider_cfg["call"]

    response_text = call_with_retries(call_fn, prompt, model, args.max_retries)

    sql_block, hcl_block = extract_code_blocks(response_text)

    if not sql_block:
        print("\nWARNING: Could not extract SQL code block from the response.")
        print("  The full response will be saved to generated_response.md for manual extraction.\n")
    if not hcl_block:
        print("\nWARNING: Could not extract HCL code block from the response.")
        print("  The full response will be saved to generated_response.md for manual extraction.\n")

    out_dir.mkdir(parents=True, exist_ok=True)

    response_path = out_dir / "generated_response.md"
    response_path.write_text(response_text)
    print(f"\n  Full LLM response saved to: {response_path}")

    tuning_md = f"""# Review & Tune (Before Apply)

This folder contains a **first draft** of:
- `masking_functions.sql` — masking UDFs + row filter functions
- `terraform.tfvars` — groups, tags, and FGAC policies that reference those functions

Before you apply, tune for your business roles and security requirements:

## Checklist

- **Groups and personas**: Do the groups map to real business roles?
- **Sensitive columns**: Are the right columns tagged (PII/PHI/financial/etc.)?
- **Masking behavior**: Are you using the right approach (partial, redact, hash) per sensitivity and use case?
- **Row filters and exceptions**: Are filters too broad/strict? Are exceptions minimal and intentional?
- **Validate before apply**: Run validation before `terraform apply`.

## Suggested workflow

1. Review and edit `masking_functions.sql` (if needed), then run it in your Databricks SQL editor for `{catalog}.{schema}`.
2. Review and edit `terraform.tfvars` (groups, tags, principals, policies).
3. Validate (while files are still in `generated/`):
   ```bash
   python validate_abac.py generated/terraform.tfvars generated/masking_functions.sql
   ```
4. Copy to module root:
   ```bash
   cp generated/terraform.tfvars terraform.tfvars
   ```
5. Apply (use -parallelism=1 to avoid tag policy race conditions):
   ```bash
   terraform init && terraform plan && terraform apply -parallelism=1
   ```
"""

    tuning_path = out_dir / "TUNING.md"
    tuning_path.write_text(tuning_md)
    print(f"  Tuning checklist written to: {tuning_path}")

    if sql_block:
        sql_header = (
            "-- ============================================================================\n"
            "-- GENERATED MASKING FUNCTIONS (FIRST DRAFT)\n"
            "-- ============================================================================\n"
            f"-- Target: {catalog}.{schema}\n"
            "-- Next: review generated/TUNING.md, tune if needed, then run this SQL.\n"
            "-- ============================================================================\n\n"
        )

        sql_block = sql_header + sql_block.replace("{catalog}", catalog).replace("{schema}", schema)
        sql_path = out_dir / "masking_functions.sql"
        sql_path.write_text(sql_block + "\n")
        print(f"  masking_functions.sql written to: {sql_path}")
        print(f"    (placeholders replaced: {{catalog}} → {catalog}, {{schema}} → {schema})")

    if hcl_block:
        hcl_header = (
            "# ============================================================================\n"
            "# GENERATED ABAC CONFIG (FIRST DRAFT)\n"
            "# ============================================================================\n"
            "# NOTE: Authentication + catalog/schema come from auth.auto.tfvars.\n"
            "# This file is ABAC-only (groups, tags, and FGAC policies).\n"
            "# Tune the following before apply:\n"
            "# - groups (business roles)\n"
            "# - tag_assignments (what data is considered sensitive)\n"
            "# - fgac_policies (who sees what, and how)\n"
            "# Then validate before copying to root:\n"
            "#   python validate_abac.py generated/terraform.tfvars generated/masking_functions.sql\n"
            "# ============================================================================\n\n"
        )

        hcl_block = sanitize_tfvars_hcl(hcl_block)
        tfvars_path = out_dir / "terraform.tfvars"
        tfvars_path.write_text(hcl_header + hcl_block + "\n")
        print(f"  terraform.tfvars written to: {tfvars_path}")

    if sql_block and hcl_block and not args.skip_validation:
        passed = run_validation(out_dir)
        if not passed:
            print("\n  Validation found errors. Review the output above and fix before running terraform apply.")
            sys.exit(1)
    elif not args.skip_validation and (not sql_block or not hcl_block):
        print("\n  [SKIP] Validation skipped — could not extract both code blocks.")
        print(f"  Review {response_path} and manually extract the files.")

    print("\n" + "=" * 60)
    print("  Done!")
    if sql_block and hcl_block:
        print("  Next steps:")
        print(f"    1. Review {out_dir}/TUNING.md")
        print(f"    2. Run {out_dir}/masking_functions.sql in your Databricks SQL editor")
        print(f"    3. python validate_abac.py {out_dir}/terraform.tfvars {out_dir}/masking_functions.sql")
        print(f"    4. cp {out_dir}/terraform.tfvars terraform.tfvars")
        print("    5. terraform init && terraform plan && terraform apply -parallelism=1")
    print("=" * 60)


if __name__ == "__main__":
    main()
