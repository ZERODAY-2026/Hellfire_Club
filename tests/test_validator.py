"""
Unit tests for deterministic SQL validator.
"""

import pytest
from app.validator import validate_sql

def test_valid_select_threat():
    sql = "SELECT cve_id, cvss_score FROM cve WHERE severity = 'HIGH' LIMIT 10"
    res = validate_sql(sql, "threat_intel.yaml")
    assert res.is_valid
    assert res.cleaned_sql is not None

def test_valid_select_tpch():
    sql = "SELECT orderkey, totalprice FROM orders WHERE orderstatus = 'O' LIMIT 10"
    res = validate_sql(sql, "tpch_sample.yaml")
    assert res.is_valid
    assert res.cleaned_sql is not None
    assert "SNOWFLAKE_SAMPLE_DATA" in res.cleaned_sql.upper()

def test_missing_limit_injection():
    sql = "SELECT cve_id FROM kev"
    res = validate_sql(sql, "threat_intel.yaml")
    assert res.is_valid
    assert "LIMIT" in res.cleaned_sql.upper()

def test_disallowed_table():
    sql = "SELECT * FROM secret_users"
    res = validate_sql(sql, "threat_intel.yaml")
    assert not res.is_valid
    assert "not allowed" in res.error_message.lower()

def test_forbidden_dml():
    sql = "DROP TABLE kev"
    res = validate_sql(sql, "threat_intel.yaml")
    assert not res.is_valid
    assert "only select queries" in res.error_message.lower() or "forbidden" in res.error_message.lower()

def test_multiple_statements():
    sql = "SELECT * FROM cve; DROP TABLE cve;"
    res = validate_sql(sql, "threat_intel.yaml")
    assert not res.is_valid
    assert "Multiple SQL statements" in res.error_message
