"""
Runtime resource caching and warehouse warm-up utilities for ThreatDesk.
Uses st.cache_resource from Streamlit via the outside layer.
"""

import streamlit as st
import time
from app.config import load_config, ThreatIntelConfig
from app.executor import execute_query

@st.cache_resource
def cached_load_config(config_file: str) -> ThreatIntelConfig:
    """Load and cache dataset configuration once across the application lifecycle."""
    return load_config(config_file)

def warm_up_warehouse() -> bool:
    """
    Run one harmless query through the existing executor path to wake the warehouse,
    without changing warehouse settings or credits.
    """
    if "warehouse_warmed" in st.session_state and st.session_state.warehouse_warmed:
        return True

    with st.spinner("Warming up Snowflake warehouse..."):
        try:
            # Harmless lightweight query (e.g. SELECT 1)
            result = execute_query("SELECT 1")
            if result.success:
                st.session_state.warehouse_warmed = True
                return True
        except Exception:
            pass
    return False
