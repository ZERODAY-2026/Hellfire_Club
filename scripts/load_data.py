import os
import json
import gzip
import csv
import urllib.request
import datetime
from dotenv import load_dotenv
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import pandas as pd

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
EPSS_URL = "https://epss.cyentia.com/epss_scores-current.csv.gz"

def download_file(url, dest_path):
    print(f"Downloading {url} -> {dest_path}...")
    headers = {'User-Agent': 'ThreatDesk-SecurityAgent/1.0'}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
        out_file.write(response.read())
    print("Download complete.")

def load_kev_data():
    kev_path = os.path.join(DATA_DIR, "kev.json")
    if not os.path.exists(kev_path):
        download_file(KEV_URL, kev_path)

    with open(kev_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    vulnerabilities = data.get("vulnerabilities", [])
    kev_rows, cve_rows = [], []

    for v in vulnerabilities:
        cve_id = v.get("cveID")
        date_added = v.get("dateAdded")
        short_desc = v.get("shortDescription")

        kev_rows.append({
            "cve_id": cve_id,
            "vendor_project": v.get("vendorProject"),
            "product": v.get("product"),
            "vulnerability_name": v.get("vulnerabilityName"),
            "date_added": date_added,
            "short_description": short_desc,
            "required_action": v.get("requiredAction"),
            "due_date": v.get("dueDate"),
            "known_ransomware_use": v.get("knownRansomwareCampaignUse"),
            "notes": v.get("notes")
        })

        cve_rows.append({
            "cve_id": cve_id,
            "published_date": date_added,
            "cvss_score": 8.0,
            "severity": "HIGH",
            "description": short_desc
        })

    kev_df = pd.DataFrame(kev_rows)
    kev_df['date_added'] = pd.to_datetime(kev_df['date_added']).dt.date
    kev_df['due_date'] = pd.to_datetime(kev_df['due_date'], errors='coerce').dt.date
    kev_df.columns = [c.upper() for c in kev_df.columns]

    cve_df = pd.DataFrame(cve_rows)
    cve_df['published_date'] = pd.to_datetime(cve_df['published_date']).dt.date
    cve_df.columns = [c.upper() for c in cve_df.columns]

    print(f"Loaded {len(kev_df)} KEV records and {len(cve_df)} CVE records from KEV.")
    return kev_df, cve_df

def load_epss_data():
    epss_gz_path = os.path.join(DATA_DIR, "epss_scores-current.csv.gz")
    if not os.path.exists(epss_gz_path):
        download_file(EPSS_URL, epss_gz_path)

    rows = []
    score_date = datetime.date.today().isoformat()
    with gzip.open(epss_gz_path, 'rt', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith('#'):
                continue
            if row[0] == 'cve':
                if len(row) > 3:
                    score_date = row[3]
                continue
            if len(row) >= 3:
                rows.append({
                    "cve_id": row[0].upper(),
                    "epss_score": float(row[1]),
                    "percentile": float(row[2]),
                    "score_date": score_date
                })
    df = pd.DataFrame(rows)
    df['score_date'] = pd.to_datetime(df['score_date']).dt.date
    df.columns = [c.upper() for c in df.columns]
    print(f"Loaded {len(df)} EPSS records.")
    return df

def main():
    print("Starting Phase 2: Data load...")
    kev_df, cve_df = load_kev_data()
    epss_df = load_epss_data()

    # Get env vars
    db_name = os.getenv("SNOWFLAKE_DATABASE")
    schema_name = os.getenv("SNOWFLAKE_SCHEMA")
    app_role = os.getenv("SNOWFLAKE_ROLE")

    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=db_name,
        schema=schema_name,
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        role=os.getenv("SNOWFLAKE_ADMIN_ROLE")
    )
    cursor = conn.cursor()

    # --- FIX: explicitly set the Snowflake context before loading data ---
    cursor.execute(f"USE DATABASE {db_name}")
    cursor.execute(f"USE SCHEMA {schema_name}")

    print("Loading CVE table...")
    write_pandas(conn, cve_df, 'CVE', auto_create_table=True, overwrite=True)

    print("Loading KEV table...")
    write_pandas(conn, kev_df, 'KEV', auto_create_table=True, overwrite=True)

    print("Loading EPSS table...")
    write_pandas(conn, epss_df, 'EPSS', auto_create_table=True, overwrite=True)

    print(f"Granting SELECT permissions to {app_role} role...")
    cursor.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA {db_name}.{schema_name} TO ROLE {app_role}")
    cursor.execute(f"GRANT SELECT ON FUTURE TABLES IN SCHEMA {db_name}.{schema_name} TO ROLE {app_role}")

    # Verify row counts
    for table in ['CVE', 'KEV', 'EPSS']:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"\n--- Table {table} (Row count: {count}) ---")
        cursor.execute(f"SELECT * FROM {table} LIMIT 3")
        cols = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        print("Columns:", cols)
        for r in rows:
            print("  ", r)
            
    cursor.close()
    conn.close()
    print("\nPhase 2 data load completed successfully!")

if __name__ == "__main__":
    main()