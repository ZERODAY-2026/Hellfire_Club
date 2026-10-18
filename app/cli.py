"""
Command Line Interface for ThreatDesk.
Orchestrates the pipeline: Question -> Planner -> Validator -> Executor -> Explainer.
"""

import sys
import argparse
from app.planner import generate_sql_plan
from app.validator import validate_sql
from app.executor import execute_query
from app.explainer import explain_results

def main():
    parser = argparse.ArgumentParser(description="ThreatDesk: Enterprise AI Data Agent")
    parser.add_argument("question", nargs="?", help="Natural language question")
    parser.add_argument("--config", default=None, help="Dataset configuration YAML file")
    args = parser.parse_args()

    config_path = args.config
    question = args.question

    if not question:
        print("ThreatDesk CLI - Interactive Mode")
        print("Type 'exit' or 'quit' to exit.\n")
        while True:
            try:
                question = input("ThreatDesk> ").strip()
                if not question:
                    continue
                if question.lower() in ["exit", "quit"]:
                    break
                process_question(question, config_path)
                print("\n" + "-"*60 + "\n")
            except (KeyboardInterrupt, EOFError):
                print("\nExiting ThreatDesk.")
                break
    else:
        process_question(question, config_path)

def process_question(question: str, config_path: str = None):
    print(f"[*] Question: {question}")

    # 1. Planner
    print("[*] Generating SQL plan with Gemma...")
    try:
        plan = generate_sql_plan(question, config_path)
        print(f"    Reasoning: {plan.reasoning}")
        print(f"    Generated SQL:\n    {plan.sql}")
    except Exception as e:
        print(f"[!] Planner error: {e}")
        return

    # 2. Validator
    print("[*] Validating SQL query...")
    validation = validate_sql(plan.sql, config_path)
    if not validation.is_valid:
        print(f"[!] Validation failed: {validation.error_message}")
        return

    clean_sql = validation.cleaned_sql
    print(f"    Validated SQL:\n    {clean_sql}")

    # 3. Executor
    print("[*] Executing query against Snowflake...")
    exec_result = execute_query(clean_sql)
    if not exec_result.success:
        print(f"[!] Execution failed: {exec_result.error}")
        return

    print(f"    Returned {exec_result.row_count} rows in {exec_result.execution_time:.3f}s. Query ID: {exec_result.sfqid}")

    # 4. Explainer
    print("[*] Generating explanation with Gemma...")
    try:
        explanation_res = explain_results(question, clean_sql, exec_result.rows, exec_result.sfqid, config_path, plan.reasoning)
        print("\n--- ThreatDesk Intelligence Report ---")
        print(explanation_res.explanation)
        print("-" * 40)
    except Exception as e:
        print(f"[!] Explainer error: {e}")
        print(f"    Query executed. Query ID: {exec_result.sfqid}")

if __name__ == "__main__":
    main()
