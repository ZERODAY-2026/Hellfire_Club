# ThreatDesk – Data Sources & Licensing

ThreatDesk integrates three primary vulnerability intelligence and prioritization datasets. Below are the details of each data source, including update frequency, schema mappings, licensing terms, and usage notes.

## 1. CISA Known Exploited Vulnerabilities (KEV) Catalog
- **Source URL**: `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json`
- **Description**: A comprehensive catalog of vulnerabilities that have been exploited in the wild, maintained by the Cybersecurity and Infrastructure Security Agency (CISA).
- **Update Frequency**: Daily / As vulnerabilities are added.
- **Licensing & Terms of Use**: Public domain / US Government work. Free to use, reproduce, and distribute.
- **Snowflake Table**: `KEV`
- **Key Columns**:
  - `cve_id` (VARCHAR): Standard CVE identifier (e.g., `CVE-2021-44228`).
  - `vendor_project` (VARCHAR): Affected vendor or project.
  - `product` (VARCHAR): Affected product name.
  - `vulnerability_name` (VARCHAR): Descriptive vulnerability name.
  - `date_added` (DATE): Date added to the CISA KEV catalog.
  - `short_description` (TEXT): Summary of the vulnerability.
  - `required_action` (TEXT): Remediation action required by CISA directives.
  - `due_date` (DATE): Remediation deadline.
  - `known_ransomware_use` (VARCHAR): Known campaign usage status.
  - `notes` (TEXT): References and URLs.

## 2. EPSS (Exploit Prediction Scoring System)
- **Source URL**: `https://epss.cyentia.com/epss_scores-current.csv.gz`
- **Description**: Daily updated probabilistic model estimating the likelihood (probability between 0 and 1) that a software vulnerability will be exploited in the wild within the next 30 days. Maintained by FIRST and Cyentia Institute.
- **Update Frequency**: Daily.
- **Licensing & Terms of Use**: Creative Commons Attribution 4.0 International (CC BY 4.0). Free to use with attribution to FIRST and Cyentia Institute.
- **Snowflake Table**: `EPSS`
- **Key Columns**:
  - `cve_id` (VARCHAR): Standard CVE identifier.
  - `epss_score` (FLOAT): Probability score (0.0 to 1.0).
  - `percentile` (FLOAT): Relative ranking percentile (0.0 to 1.0).
  - `score_date` (DATE): Date of the EPSS score calculation.

## 3. CVE Reference Table
- **Derived / Base Table**: `CVE`
- **Description**: Core vulnerability catalog table linking CVE identifiers with published dates, severity, CVSS scores, and descriptions derived from upstream feeds.
- **Snowflake Table**: `CVE`
- **Key Columns**:
  - `cve_id` (VARCHAR): Standard CVE identifier.
  - `published_date` (DATE): Publication date.
  - `cvss_score` (FLOAT): CVSS base score.
  - `severity` (VARCHAR): Severity rating (e.g., `HIGH`, `CRITICAL`).
  - `description` (TEXT): Vulnerability description.

---

## Data Governance & Security
- All tables reside in Snowflake database `THREAT_DB`, schema `THREAT_SCHEMA`.
- A dedicated read-only role (`THREAT_ANALYST`) is provisioned for query execution and agent interactions, ensuring least-privilege security.
