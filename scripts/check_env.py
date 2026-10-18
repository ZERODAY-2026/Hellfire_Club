"""
Phase 1: Environment and Connectivity Check for ThreatDesk.
Reports required environment variable presence (set/missing),
tests Gemma API call with GEMMA_MODEL and fallback model,
and connects to Snowflake to run a test query.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    "GEMINI_API_KEY",
    "GEMMA_MODEL",
    "GEMMA_FALLBACK_MODEL",
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_DATABASE",
    "SNOWFLAKE_SCHEMA",
    "SNOWFLAKE_WAREHOUSE",
]

def check_env_vars():
    print("=== 1. Checking Environment Variables ===")
    all_set = True
    for var in REQUIRED_VARS:
        val = os.getenv(var)
        if val and val.strip():
            print(f"  [PASS] {var}: set")
        else:
            print(f"  [FAIL] {var}: missing")
            all_set = False

    # Check roles (either SNOWFLAKE_ADMIN_ROLE or SNOWFLAKE_ROLE)
    admin_role = os.getenv("SNOWFLAKE_ADMIN_ROLE") or os.getenv("SNOWFLAKE_ROLE")
    if admin_role:
        print(f"  [PASS] Snowflake admin/setup role: set")
    else:
        print(f"  [FAIL] Snowflake admin/setup role: missing")
        all_set = False

    return all_set

def check_gemma():
    print("\n=== 2. Checking Gemma API Calls ===")
    api_key = os.getenv("GEMINI_API_KEY")
    model_primary = os.getenv("GEMMA_MODEL")
    model_fallback = os.getenv("GEMMA_FALLBACK_MODEL")

    if not api_key:
        print("  [FAIL] GEMINI_API_KEY is missing, skipping Gemma check.")
        return False

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
    except Exception as e:
        print(f"  [FAIL] Failed to initialize google-genai client: {e}")
        return False

    success = True
    for model_name in [model_primary, model_fallback]:
        if not model_name:
            continue
        print(f"  Testing model: {model_name}...")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents="Return a JSON object with key 'status' and value 'ok'.",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            print(f"  [PASS] Model {model_name} responded: {response.text.strip()}")
        except Exception as e:
            print(f"  [WARN] Model {model_name} error (may be transient rate limit or service error): {e}")
            if model_name == model_primary:
                success = False

    return success

def check_snowflake():
    print("\n=== 3. Checking Snowflake Connection ===")
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    user = os.getenv("SNOWFLAKE_USER")
    database = os.getenv("SNOWFLAKE_DATABASE")
    schema = os.getenv("SNOWFLAKE_SCHEMA")
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
    admin_role = os.getenv("SNOWFLAKE_ADMIN_ROLE") or os.getenv("SNOWFLAKE_ROLE")
    readonly_role = os.getenv("SNOWFLAKE_READONLY_ROLE") or "THREAT_ANALYST"

    password = os.getenv("SNOWFLAKE_PASSWORD")
    private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
    private_key_passphrase = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
    token = os.getenv("SNOWFLAKE_TOKEN")

    conn_params = {
        "account": account,
        "user": user,
        "database": database,
        "schema": schema,
        "warehouse": warehouse,
    }

    if password:
        conn_params["password"] = password
        print("  Using password authentication.")
    elif private_key_path:
        import cryptography.hazmat.backends as crypto_backends
        import cryptography.hazmat.primitives.serialization as crypto_serialization
        with open(private_key_path, "rb") as key_file:
            p_key = crypto_serialization.load_pem_private_key(
                key_file.read(),
                password=private_key_passphrase.encode() if private_key_passphrase else None,
                backend=crypto_backends.default_backend()
            )
        pk_bytes = p_key.private_bytes(
            encoding=crypto_serialization.Encoding.DER,
            format=crypto_serialization.PrivateFormat.PKCS8,
            encryption_algorithm=crypto_serialization.NoEncryption()
        )
        conn_params["private_key"] = pk_bytes
        print("  Using key-pair authentication.")
    elif token:
        conn_params["token"] = token
        print("  Using token authentication.")
    else:
        print("  [FAIL] No authentication method configured.")
        return False

    roles_to_try = [readonly_role, admin_role]
    connected = False

    try:
        import snowflake.connector
    except ImportError:
        print("  [FAIL] snowflake-connector-python not installed.")
        return False

    for role in roles_to_try:
        if not role:
            continue
        print(f"  Attempting connection with role: {role}...")
        try:
            params = conn_params.copy()
            params["role"] = role
            conn = snowflake.connector.connect(**params)
            cur = conn.cursor()
            cur.execute("SELECT CURRENT_VERSION(), CURRENT_ROLE(), CURRENT_WAREHOUSE()")
            row = cur.fetchone()
            print(f"  [PASS] Successfully connected using role {role}!")
            print(f"         Snowflake Version: {row[0]}")
            print(f"         Current Role:      {row[1]}")
            print(f"         Current Warehouse: {row[2]}")
            cur.close()
            conn.close()
            connected = True
            break
        except Exception as e:
            print(f"  [WARN] Failed with role {role}: {e}")

    return connected

def main():
    print("Running ThreatDesk Environment & Connectivity Check...\n")
    env_ok = check_env_vars()
    gemma_ok = check_gemma()
    sf_ok = check_snowflake()

    print("\n=== Summary ===")
    print(f"  Environment Variables: {'PASS' if env_ok else 'FAIL'}")
    print(f"  Gemma API:             {'PASS' if gemma_ok else 'FAIL'}")
    print(f"  Snowflake Connection:  {'PASS' if sf_ok else 'FAIL'}")

    if env_ok and gemma_ok and sf_ok:
        print("\nAll checks passed successfully!")
        sys.exit(0)
    else:
        print("\nSome checks failed. Please review output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
