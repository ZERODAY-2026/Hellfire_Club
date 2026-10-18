# ThreatDesk – System Architecture

ThreatDesk is an open-source, enterprise-grade AI data agent designed for the **ZeroDay OSS Hacktoberfest 2026 (PS1 DataMind)** track. It translates natural language security queries into deterministic, safe SQL queries executed against Snowflake, returning grounded threat intelligence reports synthesized by Gemma.

---

## 1. High-Level Architecture Diagram

```
[ User / Analyst ]
       │
       ▼  (Natural Language Query)
[ Streamlit UI / CLI ]
       │
       ├──► 1. Planner (Gemma via google-genai SDK)
       │        └─► Generates SQL plan & reasoning
       │
       ├──► 2. Validator (Deterministic sqlglot engine)
       │        ├─► Enforces Read-Only SELECT statements
       │        ├─► Restricts tables to allowlist (CVE, KEV, EPSS)
       │        ├─► Blocks DML/DDL (DROP, INSERT, UPDATE, etc.)
       │        └─► Enforces Row Limit (MAX 200)
       │
       ├──► 3. Executor (Snowflake Connector Python)
       │        └─► Connects using read-only role (THREAT_ANALYST)
       │
       └──► 4. Explainer (Gemma via google-genai SDK)
                └─► Synthesizes Markdown intelligence report strictly grounded in rows
```

---

## 2. Component Breakdown

### A. Planner (`app/planner.py`)
- **Model**: Gemma (`gemma-4-26b-a4b-it` / `gemma-4-31b-it`).
- **Role**: Receives natural language questions and database schema definitions from `configs/threat_intel.yaml`.
- **Output**: Pydantic `PlanResponse` containing `sql` and `reasoning`.

### B. Validator (`app/validator.py`)
- **Engine**: `sqlglot` (Snowflake dialect).
- **Security Invariants**:
  1. **Read-Only Enforcement**: Rejects any statement type other than `SELECT`.
  2. **Table Whitelisting**: Verifies referenced tables belong strictly to `CVE`, `KEV`, or `EPSS`.
  3. **Mutation Blocking**: Prohibits `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `GRANT`, `REVOKE`.
  4. **Row Limit Enforcement**: Automatically appends or validates `LIMIT` clauses to prevent memory exhaustion.

### C. Executor (`app/executor.py`)
- **Engine**: `snowflake-connector-python`.
- **Least Privilege Principle**: Connects exclusively using the read-only `THREAT_ANALYST` role with `USAGE` on `THREAT_WH` warehouse and `THREAT_DB.THREAT_SCHEMA` database/schema.
- **Output**: Structured `ExecutionResult` containing columns, rows, row count, and execution success status.

### D. Explainer (`app/explainer.py`)
- **Model**: Gemma (`gemma-4-26b-a4b-it`).
- **Role**: Grounded summarization. Takes user question, SQL, and Snowflake execution rows to generate professional threat intelligence reports without hallucination.

### E. Data Pipeline (`scripts/load_data.py`)
- Downloads official CISA KEV JSON catalog and EPSS CSV gzip feeds.
- Transforms and upcases column schemas.
- Loads records into Snowflake using optimized `write_pandas`.

---

## 3. Security & Governance

- **Secret Management**: `.env` is excluded via `.gitignore` and loaded exclusively at runtime via `python-dotenv`.
- **Secret Scanning**: Pre-commit hooks with `detect-secrets` prevent accidental secret leakage.
- **RBAC**: Database access is strictly partitioned between `ACCOUNTADMIN` (setup/load) and `THREAT_ANALYST` (read-only query execution).
