"""
Gemma-based SQL planner using the google-genai SDK.
Converts natural language questions into Snowflake SQL queries.
"""

import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from app.config import load_config
from app.schemas import PlanResponse

load_dotenv()

def get_genai_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")
    return genai.Client(api_key=api_key)

def generate_sql_plan(question: str, config_path: str = None) -> PlanResponse:
    config = load_config(config_path)
    client = get_genai_client()

    primary_model = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")
    fallback_model = os.getenv("GEMMA_FALLBACK_MODEL", "gemma-4-31b-it")

    schema_desc = []
    for table_name, t_cfg in config.tables.items():
        cols = ", ".join([f"{col} ({c_info.type})" for col, c_info in t_cfg.columns.items()])
        schema_desc.append(f"Table {table_name}: {t_cfg.description}\n  Columns: {cols}")

    schema_text = "\n".join(schema_desc)

    system_instruction = f"""You are an expert {config.domain_persona} and Snowflake SQL query generator for ThreatDesk ({config.domain_name}).
You have access to the following Snowflake tables in database {config.database}, schema {config.schema_name}:

{schema_text}

Rules:
1. Return a JSON object with keys "sql" and "reasoning".
2. "sql" must be a valid Snowflake SQL SELECT query querying only the allowed tables ({', '.join(config.allowed_tables)}). If the question is ambiguous, out-of-domain, unsupported, or requests data/tables not present in the schema, return SELECT '' as sql and explain the refusal in "reasoning".
3. Always use fully qualified table names in the format {config.database}.{config.schema_name}.TABLE_NAME.
4. Always include appropriate filters, sorting, and a LIMIT clause (default limit 200 if unspecified).
5. "reasoning" must briefly explain how the query addresses the user's question or why it was refused.
"""

    prompt = f"User Question: {question}"

    models_to_try = [primary_model, fallback_model, "gemini-3.8-flash"]
    last_error = None

    for model_name in models_to_try:
        if not model_name:
            continue
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )

            raw_text = response.text.strip()
            data = json.loads(raw_text)

            sql = data.get("sql", "").strip()
            reasoning = data.get("reasoning", "").strip()

            if not sql:
                raise ValueError("Planner returned empty SQL query.")

            return PlanResponse(sql=sql, reasoning=reasoning)

        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"All Gemma models failed to generate plan. Last error: {str(last_error)}")
