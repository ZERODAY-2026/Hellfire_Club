"""
Gemma-based result explainer using google-genai SDK.
Synthesizes natural language explanations grounded strictly in Snowflake execution results.
"""

import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv
from app.schemas import ExplainerResponse
from app.config import load_config

load_dotenv()

def explain_results(question: str, sql: str, rows: list, sfqid: str = None, config_path: str = None, reasoning: str = None) -> ExplainerResponse:
    config = load_config(config_path)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set.")

    client = genai.Client(api_key=api_key)
    primary_model = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")
    fallback_model = os.getenv("GEMMA_FALLBACK_MODEL", "gemma-4-31b-it")

    system_instruction = f"""You are ThreatDesk Intelligence Explainer ({config.domain_name}).
Your job is to provide clear, professional, concise answers to user questions based STRICTLY on the provided query results and SQL context.
Rules:
1. Ground your answer entirely in the provided rows, SQL query, and planner reasoning. Do not invent or hallucinate entities, scores, or details not present in the data.
2. If the execution results have 0 rows or the query returns no records, state clearly and professionally in the intelligence report that no matching records were found in the ThreatDesk dataset (or that the requested information is outside the dataset).
3. Highlight key metrics and findings clearly when rows are present.
4. Return a JSON object with key "explanation".
"""

    prompt = f"""User Question: {question}
SQL Query Used: {sql}
Planner Reasoning: {reasoning or 'N/A'}
Execution Results ({len(rows)} rows):
{json.dumps(rows, default=str, indent=2)}
"""

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
            explanation = data.get("explanation", "").strip()
            if not explanation:
                explanation = raw_text

            return ExplainerResponse(explanation=explanation)

        except Exception as e:
            last_error = e
            continue

    if not rows or len(rows) == 0:
        summary = f"No matching records found in the ThreatDesk dataset for your query. (Snowflake Query ID: {sfqid or 'N/A'})"
    else:
        summary = f"Query executed successfully returning {len(rows)} rows. (Snowflake Query ID: {sfqid or 'N/A'})"
    return ExplainerResponse(explanation=summary)
