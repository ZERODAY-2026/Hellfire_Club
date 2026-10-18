"""
Evaluation script for ThreatDesk.
Runs the 25-question evaluation set through the pipeline, validating SQL, executing against Snowflake,
verifying expected tables and keywords, and measuring accuracy and execution latency.
"""

import os
import time
import yaml
from dotenv import load_dotenv
from app.planner import generate_sql_plan
from app.validator import validate_sql
from app.executor import execute_query
from app.config import load_config
import sqlglot
from sqlglot import exp

load_dotenv()

def run_evaluation():
    eval_path = os.path.join(os.path.dirname(__file__), "questions.yaml")
    if not os.path.exists(eval_path):
        print(f"[!] Evaluation questions file not found at {eval_path}")
        return

    with open(eval_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    questions = data.get("questions", [])
    total_questions = len(questions)
    print(f"Starting ThreatDesk Evaluation: {total_questions} test cases loaded.\n")
    print("="*80)

    if total_questions == 0:
        print("[!] No evaluation questions found.")
        return

    config = load_config()
    results = []
    passed_count = 0

    for idx, q in enumerate(questions, 1):
        qid = q.get("id", f"q{idx}")
        question_text = q.get("question")
        expected_tables = [t.upper() for t in q.get("expected_tables", [])]
        expected_keywords = q.get("expected_keywords", [])

        print(f"\n[{idx}/{total_questions}] ID: {qid}")
        print(f"Question: {question_text}")

        start_time = time.time()
        test_passed = True
        error_msg = ""
        sql = ""
        clean_sql = ""
        exec_success = False
        row_count = 0
        tables_matched = True
        keywords_matched = True
        check_details = []

        try:
            # 1. Planner
            plan = generate_sql_plan(question_text)
            sql = plan.sql

            # 2. Validator
            validation = validate_sql(sql)
            if not validation.is_valid:
                test_passed = False
                error_msg = f"Validation failed: {validation.error_message}"
            else:
                clean_sql = validation.cleaned_sql

                # Verify expected tables from sqlglot AST
                parsed = sqlglot.parse_one(clean_sql, read="snowflake")
                used_tables = {t.name.upper() for t in parsed.find_all(exp.Table)}

                for exp_tbl in expected_tables:
                    if exp_tbl not in used_tables:
                        tables_matched = False
                        check_details.append(f"Expected table '{exp_tbl}' not found in query tables {list(used_tables)}")

                # Verify expected keywords
                for kw in expected_keywords:
                    # Case-insensitive keyword check
                    if kw.upper() not in clean_sql.upper():
                        keywords_matched = False
                        check_details.append(f"Expected keyword/clause '{kw}' not found in clean SQL")

                if not tables_matched or not keywords_matched:
                    test_passed = False
                    error_msg = "; ".join(check_details)
                else:
                    # 3. Executor
                    exec_result = execute_query(clean_sql)
                    if not exec_result.success:
                        test_passed = False
                        error_msg = f"Execution failed: {exec_result.error}"
                    else:
                        exec_success = True
                        row_count = exec_result.row_count

        except Exception as e:
            test_passed = False
            error_msg = str(e)

        duration = time.time() - start_time

        if test_passed:
            passed_count += 1
            print(f"  [PASS] ({duration:.2f}s) - Rows: {row_count}")
        else:
            print(f"  [FAIL] ({duration:.2f}s) - Error: {error_msg}")

        results.append({
            "id": qid,
            "question": question_text,
            "passed": test_passed,
            "error": error_msg,
            "duration": duration,
            "sql": sql,
            "clean_sql": clean_sql,
            "rows": row_count,
            "tables_matched": tables_matched,
            "keywords_matched": keywords_matched
        })

    success_rate = (passed_count / total_questions) * 100 if total_questions > 0 else 0.0

    print("\n" + "="*80)
    print("EVALUATION SUMMARY")
    print("="*80)
    print(f"Total Questions: {total_questions}")
    print(f"Passed: {passed_count}")
    print(f"Failed: {total_questions - passed_count}")
    print(f"Success Rate: {success_rate:.1f}%")
    print("="*80)

    # Save evaluation report
    report_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(os.path.dirname(__file__), "evaluation_report.yaml")

    with open(report_path, 'w', encoding='utf-8') as f:
        yaml.dump({
            "total": total_questions,
            "passed": passed_count,
            "success_rate": success_rate,
            "results": results
        }, f)
    print(f"Evaluation report saved to {report_path}")

if __name__ == "__main__":
    run_evaluation()
