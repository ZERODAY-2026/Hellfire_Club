"""
Snowflake query executor using snowflake-connector-python with the read-only role.
"""

import os
import time
from dotenv import load_dotenv
import snowflake.connector
from app.schemas import ExecutionResult

load_dotenv()

def execute_query(sql: str) -> ExecutionResult:
    account = os.getenv("SNOWFLAKE_ACCOUNT")
    user = os.getenv("SNOWFLAKE_USER")
    password = os.getenv("SNOWFLAKE_PASSWORD")
    database = os.getenv("SNOWFLAKE_DATABASE")
    schema = os.getenv("SNOWFLAKE_SCHEMA")
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
    readonly_role = os.getenv("SNOWFLAKE_READONLY_ROLE", "THREATDESK_READONLY")
    timeout = int(os.getenv("STATEMENT_TIMEOUT_SECONDS", 60))

    if not all([account, user, password, database, schema, warehouse]):
        return ExecutionResult(
            success=False,
            error="Missing required Snowflake environment variables."
        )

    start_time = time.time()
    try:
        conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            database=database,
            schema=schema,
            warehouse=warehouse,
            role=readonly_role
        )
        cursor = conn.cursor()
        cursor.execute(f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {timeout}")
        cursor.execute(f"USE WAREHOUSE {warehouse}")
        cursor.execute(sql)

        sfqid = cursor.sfqid

        columns = [desc[0].lower() for desc in cursor.description] if cursor.description else []
        raw_rows = cursor.fetchall()

        rows = []
        for r in raw_rows:
            row_dict = {}
            for idx, col in enumerate(columns):
                val = r[idx]
                if hasattr(val, "isoformat"):
                    val = val.isoformat()
                row_dict[col] = val
            rows.append(row_dict)

        cursor.close()
        conn.close()

        duration = time.time() - start_time

        return ExecutionResult(
            success=True,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            sfqid=sfqid,
            execution_time=duration
        )

    except Exception as e:
        duration = time.time() - start_time
        return ExecutionResult(
            success=False,
            error=str(e),
            execution_time=duration
        )
