"""
Unit tests for ThreatDesk configuration loading and validation.
"""

import os
import pytest
from app.config import load_config, ThreatIntelConfig

def test_load_config():
    config = load_config()
    assert isinstance(config, ThreatIntelConfig)
    expected_db = os.getenv("SNOWFLAKE_DATABASE", "THREAT_DB")
    assert config.database == expected_db
    assert "CVE" in config.allowed_tables
    assert "KEV" in config.allowed_tables
    assert "EPSS" in config.allowed_tables

    # Check table structure
    assert "CVE" in config.tables
    assert "CVE_ID" in config.tables["CVE"].columns
    assert config.tables["CVE"].columns["CVE_ID"].type == "VARCHAR"

    assert "KEV" in config.tables
    assert "VENDOR_PROJECT" in config.tables["KEV"].columns

    assert "EPSS" in config.tables
    assert "EPSS_SCORE" in config.tables["EPSS"].columns
