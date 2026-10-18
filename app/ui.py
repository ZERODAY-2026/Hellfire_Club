"""
Streamlit UI for ThreatDesk: Vulnerability & Enterprise Intelligence Data Agent.
Provides an interactive web interface for natural language queries backed by Gemma and Snowflake.
Editorial redesign inspired by squarespace.com.
"""

import streamlit as st
import pandas as pd
import os
import time
from app.runtime import cached_load_config, warm_up_warehouse
from app.perf import pipeline_cache, get_data_version, log_stage_timing
from app.planner import generate_sql_plan
from app.validator import validate_sql
from app.executor import execute_query
from app.explainer import explain_results

st.set_page_config(
    page_title="ThreatDesk — Enterprise AI Intelligence",
    page_icon="🛡️",
    layout="wide"
)

# Load external CSS stylesheet
styles_path = os.path.join(os.path.dirname(__file__), "styles.css")
if os.path.exists(styles_path):
    with open(styles_path, "r", encoding="utf-8") as f:
        custom_css = f.read()
    st.markdown('<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">', unsafe_allow_html=True)
    st.markdown(f"<style>{custom_css}</style>", unsafe_allow_html=True)

# Warm up Snowflake warehouse on first session load
warm_up_warehouse()

# Initialize session state variables
if "query_input" not in st.session_state:
    st.session_state.query_input = ""
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "run_query_trigger" not in st.session_state:
    st.session_state.run_query_trigger = False
if "last_result" not in st.session_state:
    st.session_state.last_result = None

# Slim Top Bar
st.markdown("""
<div class="top-bar">
    <div class="brand-name">
        <span>🛡️</span> ThreatDesk
    </div>
    <div style="display: flex; gap: 0.75rem; align-items: center;">
        <span class="status-pill"><span class="status-dot"></span> Snowflake Connected</span>
        <span class="status-pill"><span class="status-dot"></span> Gemma Active</span>
        <span class="status-pill">⚡ Optimized & Cached</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:
    st.markdown("### ⚙️ Dataset & Settings")

    config_options = {
        "Threat Intelligence (KEV, CVE, EPSS)": "threat_intel.yaml",
        "TPC-H E-Commerce & Supply Chain": "tpch_sample.yaml"
    }

    selected_dataset_label = st.selectbox("Select Active Dataset Config:", list(config_options.keys()))
    active_config_file = config_options[selected_dataset_label]

    # Load config info using cached loader
    try:
        cfg = cached_load_config(active_config_file)
        st.success(f"Connected to `{cfg.database}.{cfg.schema_name}`")
        st.markdown(f"**Allowed Tables:** `{', '.join(cfg.allowed_tables)}`")
    except Exception as e:
        st.error(f"Config error: {e}")

    st.markdown("---")
    st.markdown("### ⚡ Performance & Cache")
    data_version = get_data_version(active_config_file)
    st.caption(f"Data Version Hash: `{data_version}`")
    if st.button("Clear Pipeline Cache", use_container_width=True):
        pipeline_cache.clear()
        st.success("Cache cleared!")

    st.markdown("---")
    st.markdown("### 🔍 About ThreatDesk")
    st.markdown("""
    **ThreatDesk** allows analysts to query complex datasets using plain English with guaranteed safety and traceability.

    * **Planner**: Gemma interprets natural language into SQL.
    * **Validator**: `sqlglot` enforces read-only safety & table allowlists.
    * **Executor**: Secure execution against Snowflake.
    * **Explainer**: Grounded synthesis of results.
    """)

# Hero Section
st.markdown("""
<div class="hero-container">
    <div class="hero-headline">Ask your vulnerability data anything.</div>
    <div class="hero-subtitle">Every answer is fully traceable to executed SQL, runtime metrics, and Snowflake query IDs.</div>
</div>
""", unsafe_allow_html=True)

# Conversation History Chips (Follow-up state)
if st.session_state.conversation_history:
    st.markdown("<p style='text-align: center; font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.25rem;'>CONVERSATION TURN HISTORY</p>", unsafe_allow_html=True)
    history_html = '<div class="history-bar">'
    for idx, prev_q in enumerate(st.session_state.conversation_history):
        history_html += f'<div class="history-chip">Turn {idx+1}: {prev_q}</div>'
    history_html += '</div>'
    st.markdown(history_html, unsafe_allow_html=True)

# Main Query Input
query_input = st.text_input(
    "Ask a natural language query:",
    key="query_input",
    placeholder="e.g., Show me vulnerabilities with EPSS score greater than 0.95...",
    label_visibility="collapsed"
)

col_b1, col_b2, col_b3 = st.columns([2, 1, 2])
with col_b2:
    submit_btn = st.button("Run Query", type="primary", use_container_width=True)

if submit_btn or st.session_state.run_query_trigger:
    st.session_state.run_query_trigger = False
    current_query = st.session_state.query_input.strip()

    if current_query:
        if not st.session_state.conversation_history or st.session_state.conversation_history[-1] != current_query:
            st.session_state.conversation_history.append(current_query)

        # Check cache first
        cached_res = pipeline_cache.get(current_query, active_config_file, data_version)
        if cached_res:
            cached_res["is_cached"] = True
            st.session_state.last_result = cached_res
        else:
            total_start = time.time()
            with st.spinner("Processing intelligence query through pipeline..."):

                # Step 1: Planner
                t0 = time.time()
                with st.status("Step 1: Planning the query with Gemma...", expanded=False) as status:
                    try:
                        plan = generate_sql_plan(current_query, active_config_file)
                        t1 = time.time()
                        log_stage_timing(current_query, "planner", t1 - t0, True)
                        status.update(label="SQL plan generated successfully!", state="complete", expanded=False)
                    except Exception as e:
                        log_stage_timing(current_query, "planner", time.time() - t0, False)
                        st.error(f"Planner error: {e}")
                        st.stop()

                # Step 2: Validator (Checking safety & allowlists)
                t0 = time.time()
                with st.status("Step 2: Checking it is safe (Validator)...", expanded=False) as status:
                    validation = validate_sql(plan.sql, active_config_file)
                    t1 = time.time()
                    log_stage_timing(current_query, "validator", t1 - t0, validation.is_valid)
                    if not validation.is_valid:
                        st.markdown(f"""
                        <div class="unsafe-card">
                            <h3 style="margin-top:0;">🛡️ Unsafe or Unsupported Request</h3>
                            <p><strong>Reason:</strong> {validation.error_message}</p>
                            <p>ThreatDesk enforces strict read-only safety and table allowlists. Please refine your query and try again.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.stop()
                    clean_sql = validation.cleaned_sql
                    status.update(label="SQL query validated safely!", state="complete", expanded=False)

                # Step 3: Executor (Running in Snowflake)
                t0 = time.time()
                with st.status("Step 3: Running it in Snowflake...", expanded=False) as status:
                    exec_result = execute_query(clean_sql)
                    t1 = time.time()
                    log_stage_timing(current_query, "executor", t1 - t0, exec_result.success)
                    if not exec_result.success:
                        st.error(f"Execution error: {exec_result.error}. Please verify connection and retry.")
                        st.stop()
                    status.update(label=f"Query executed successfully ({exec_result.row_count} rows)!", state="complete", expanded=False)

                # Step 4: Explainer (Writing the explanation)
                t0 = time.time()
                with st.status("Step 4: Writing the explanation...", expanded=False) as status:
                    try:
                        explanation_res = explain_results(current_query, clean_sql, exec_result.rows, exec_result.sfqid, active_config_file, plan.reasoning)
                        explanation_text = explanation_res.explanation
                        t1 = time.time()
                        log_stage_timing(current_query, "explainer", t1 - t0, True)
                        status.update(label="Intelligence report synthesized!", state="complete", expanded=False)
                    except Exception as e:
                        explanation_text = f"Query executed successfully. (Snowflake Query ID: {exec_result.sfqid})"
                        log_stage_timing(current_query, "explainer", time.time() - t0, False)

                total_duration = time.time() - total_start
                log_stage_timing(current_query, "total_pipeline", total_duration, True)

                result_bundle = {
                    "plan": plan,
                    "validation": validation,
                    "clean_sql": clean_sql,
                    "exec_result": exec_result,
                    "explanation_text": explanation_text,
                    "total_duration": total_duration,
                    "is_cached": False
                }
                pipeline_cache.set(current_query, active_config_file, data_version, result_bundle)
                st.session_state.last_result = result_bundle
    else:
        st.warning("Please enter a question above.")

# Render last result if available in session state
if st.session_state.last_result:
    res = st.session_state.last_result
    exec_result = res["exec_result"]
    clean_sql = res["clean_sql"]
    explanation_text = res["explanation_text"]
    plan = res["plan"]
    is_cached = res.get("is_cached", False)
    dur = res.get("total_duration", exec_result.execution_time)

    # Editorial Single-Column Results & Evidence Panel
    st.markdown("<div class='result-wrapper'>", unsafe_allow_html=True)

    cache_badge = '<div class="proof-badge" style="background-color: #EFF6FF; color: #1E40AF; border-color: #BFDBFE;">⚡ Cached from earlier run</div>' if is_cached else f'<div class="proof-badge">⚡ Runtime: {dur:.3f}s</div>'

    # Proof Badges
    st.markdown(f"""
    <div class="proof-badges">
        {cache_badge}
        <div class="proof-badge">📊 Rows: {exec_result.row_count}</div>
        <div class="proof-badge">🔗 Snowflake Query ID: {exec_result.sfqid or 'N/A'}</div>
        <div class="proof-badge">🗄️ Database: {cfg.database}.{cfg.schema_name}</div>
    </div>
    """, unsafe_allow_html=True)

    # Intelligence Report / Answer
    st.markdown("""
    <div class="evidence-card">
        <div class="evidence-title">🛡️ Intelligence Report</div>
    """, unsafe_allow_html=True)
    st.markdown(explanation_text)
    st.markdown("</div>", unsafe_allow_html=True)

    # Empty Result State handling if row_count == 0
    if exec_result.row_count == 0:
        st.markdown(f"""
        <div class="empty-state-container">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="margin: 0 auto 1rem auto; color: var(--text-secondary);">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                <line x1="8" y1="11" x2="14" y2="11"></line>
            </svg>
            <div class="empty-state-title">No rows matched</div>
            <div class="empty-state-subtitle">Your query executed successfully against `{clean_sql}`, but no records matched the criteria. Try relaxing your filter criteria.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Execution Results Table
        st.markdown(f"""
        <div class="evidence-card">
            <div class="evidence-title">📋 Execution Results ({exec_result.row_count} total rows)</div>
        """, unsafe_allow_html=True)
        df = pd.DataFrame(exec_result.rows)
        display_df = df.head(50)
        st.dataframe(display_df, use_container_width=True)
        if exec_result.row_count > 50:
            st.caption(f"Showing first 50 of {exec_result.row_count} rows.")

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Complete Results as CSV",
            data=csv,
            file_name="threatdesk_results.csv",
            mime="text/csv",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # Executed SQL Expander
    with st.expander("💻 Executed SQL Query (Traceability)", expanded=False):
        st.code(clean_sql, language="sql")

    # Planner Reasoning Card
    st.markdown("""
    <div class="evidence-card">
        <div class="evidence-title">🧠 Planner Reasoning & Safety Verification</div>
    """, unsafe_allow_html=True)
    st.write(plan.reasoning)
    st.success("Passed all deterministic safety checks (read-only SELECT, table allowlist enforced).")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
