"""
Deterministic SQL validator using sqlglot for Snowflake dialect.
Validates that queries are read-only SELECT statements against allowed tables only,
and ensures proper LIMIT constraints.
"""

import os
import sqlglot
from sqlglot import exp
from app.config import load_config
from app.schemas import ValidationResult

def validate_sql(sql: str, config_path: str = None) -> ValidationResult:
    if not sql or not sql.strip():
        return ValidationResult(is_valid=False, error_message="Empty SQL query provided.")

    config = load_config(config_path)
    allowed_tables = {t.upper() for t in config.allowed_tables}

    try:
        parsed_expressions = sqlglot.parse(sql, read="snowflake")
        if not parsed_expressions or len(parsed_expressions) == 0:
            return ValidationResult(is_valid=False, error_message="Failed to parse SQL query.")

        if len(parsed_expressions) > 1:
            return ValidationResult(is_valid=False, error_message="Multiple SQL statements are not allowed.")

        expression = parsed_expressions[0]

        # 1. Check statement type: must be SELECT
        if not isinstance(expression, exp.Select):
            return ValidationResult(is_valid=False, error_message="Only SELECT queries are allowed.")

        # 2. Check referenced tables and fully qualify them
        tables = expression.find_all(exp.Table)
        for table in tables:
            table_name = table.name.upper()
            if table_name not in allowed_tables:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Table '{table_name}' is not allowed. Allowed tables: {list(allowed_tables)}"
                )
            table.set("db", config.schema_name)
            table.set("catalog", config.database)

        # 3. Check for forbidden operations / expressions
        forbidden_types = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter)
        for node in expression.walk():
            if isinstance(node, forbidden_types):
                return ValidationResult(is_valid=False, error_message="DML/DDL operations are strictly forbidden.")

        # 4. Check or enforce LIMIT
        row_limit = int(os.getenv("ROW_LIMIT", 200))
        limit_clause = expression.find(exp.Limit)
        if not limit_clause:
            expression = expression.limit(row_limit)
        else:
            limit_expression = limit_clause.expression
            if isinstance(limit_expression, exp.Literal) and limit_expression.is_number:
                val = int(limit_expression.this)
                if val > row_limit * 5:
                    expression.args["limit"].expression = exp.Literal.number(row_limit)

        cleaned_sql = expression.sql(dialect="snowflake")
        return ValidationResult(is_valid=True, cleaned_sql=cleaned_sql)

    except Exception as e:
        return ValidationResult(is_valid=False, error_message=f"SQL validation error: {str(e)}")
