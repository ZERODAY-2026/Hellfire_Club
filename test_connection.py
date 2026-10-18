import os
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

try:
    # Connect using your application configuration
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE")
    )
    
    cursor = conn.cursor()
    cursor.execute("SELECT CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_WAREHOUSE();")
    result = cursor.fetchone()
    
    print("Successfully connected to Snowflake!")
    print(f"Active Role: {result[0]}")
    print(f"Active Database: {result[1]}")
    print(f"Active Warehouse: {result[2]}")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")