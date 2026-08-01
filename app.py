"""
Multi-Agent Fintech Underwriting & Compliance System
Streamlit application entry point with Comprehensive Binary File Extraction (PDF, DOCX, TXT, CSV).
"""

import streamlit as st 
import pdfplumber
import docx
import re
import os
import json
import time
import tempfile
from io import BytesIO

# Imported custom backend functions
from src.agents import create_fintech_crew, run_compliance_check
from src.algorithms import parse_financial_metrics_from_text, format_metrics_hint

# Initialized Session State flags before anything else compiles
if "compliance_intercepted" not in st.session_state:
    st.session_state.compliance_intercepted = False
if "company_to_process" not in st.session_state:
    st.session_state.company_to_process = ""
if "compliance_passed" not in st.session_state:
    st.session_state.compliance_passed = False
if "last_latency" not in st.session_state:
    st.session_state.last_latency = None

def extract_text_from_file(uploaded_file):
    """Universal text extraction utility for financial and corporate documents."""
    file_type = getattr(uploaded_file, "type", getattr(uploaded_file, "content_type", "")) or ""
    filename = getattr(uploaded_file, "name", getattr(uploaded_file, "filename", "")) or ""

    is_pdf = "pdf" in file_type.lower() or filename.lower().endswith(".pdf")
    is_docx = "wordprocessingml" in file_type.lower() or filename.lower().endswith(".docx")
    is_txt = "plain" in file_type.lower() or filename.lower().endswith(".txt")
    is_csv = "csv" in file_type.lower() or filename.lower().endswith(".csv")

    # Read all bytes into memory immediately to avoid Errno 5 from closed temp files
    if hasattr(uploaded_file, "getvalue"):
        raw_bytes = uploaded_file.getvalue()
    elif hasattr(uploaded_file, "read"):
        raw_bytes = uploaded_file.read()
    else:
        raw_bytes = b""

    if not raw_bytes:
        return ""

    try:
        if is_pdf:
            with pdfplumber.open(BytesIO(raw_bytes)) as pdf:
                text = "".join(page.extract_text() or "" for page in pdf.pages)
        elif is_docx:
            doc = docx.Document(BytesIO(raw_bytes))
            text = "\n".join(p.text for p in doc.paragraphs if p.text)
        elif is_txt or is_csv:
            text = raw_bytes.decode("utf-8", errors="ignore") if isinstance(raw_bytes, bytes) else raw_bytes
        else:
            return raw_bytes.decode("utf-8", errors="ignore").strip()
        return text.strip()
    except OSError as e:
        raise RuntimeError(f"Parser Engine I/O error: {e}. Try saving the file and re-uploading.")
    except Exception as e:
        raise RuntimeError(f"Parser Engine failure during extraction: {str(e)}")

#  UPGRADED: ROBUST FORGIVING PARSER & UI COMPONENT RENDERER
def render_dossier_dashboard(crew_output):
    """Component to render dashboard metrics safely with aggressive structural repair for local LLMs."""
    if crew_output is None:
        st.error("Pipeline returned no data. The crew output is None.")
        return

    dossier_data = None

    # Step A: Try to extract as a validated Pydantic dictionary
    if hasattr(crew_output, 'pydantic') and crew_output.pydantic is not None:
        try:
            dossier_data = crew_output.pydantic.dict()
        except Exception:
            pass

    # Step B: Fallback to parsing raw text output with structural repair
    if dossier_data is None and hasattr(crew_output, 'raw') and crew_output.raw:
        try:
            raw_text = crew_output.raw.strip()
            
            # 1. Strip markdown wraps if present
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
            if match:
                raw_text = match.group(1)
            else:
                start_idx = raw_text.find('{')
                end_idx = raw_text.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    raw_text = raw_text[start_idx:end_idx+1]
            
            # 2. Repair missing commas between consecutive key-value strings (Gemma 3 local issue)
            raw_text = re.sub(r'("([^"\\]|\\.)*")\s*\n\s*(")', r'\1,\n\3', raw_text)
            
            dossier_data = json.loads(raw_text)
        except Exception as json_err:
            st.warning(f"Could not parse raw text output as structured JSON: {json_err}")

    # If all parsing attempts failed completely, show fallback text viewer
    if dossier_data is None:
        st.error("Failed to cleanly parse structured data. Displaying response stream below:")
        st.text_area("Raw Stream Output", value=str(crew_output), height=250)
        return

    # Safe extraction of nested structures
    financial = dossier_data.get("financial_telemetry", {})
    raw_dscr = financial.get('calculated_dscr', 0.0) if isinstance(financial, dict) else 0.0
    
    try:
        dscr = f"{float(raw_dscr):.2f}"
    except (ValueError, TypeError):
        dscr = str(raw_dscr)
    
    risk_rating = dossier_data.get("risk_tier") or dossier_data.get("risk_rating") or "N/A"
    verdict = dossier_data.get("credit_decision") or "UNDER REVIEW"

    # Render Clean UI Elements instead of raw JSON strings
    st.success("🎉 Underwriting Risk Profile Successfully Staged!")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Calculated DSCR", dscr)
    with col2:
        st.metric("Risk Profile", str(risk_rating).upper())
    with col3:
        st.metric("Underwriting Verdict", str(verdict).upper())

    st.info(f"**Underwriter Justification:** {dossier_data.get('underwriter_justification', 'No manual rationale supplied by agents.')}")

    with st.expander("🔍 View Complete Raw Telemetry Data Package"):
        st.json(dossier_data)


def main():
    st.set_page_config(page_title="Fintech Underwriting System", layout="wide")
    
    # System Configuration Sidebar
    st.sidebar.header("System Configuration")
    st.sidebar.success("API Protection: ENABLED")
    st.sidebar.info("Agent Rate Limits: 10 RPM\nMax Iterations: 3")
    st.sidebar.info("Parser Engine: Active (PDF/Docx/TXT)")
    if st.session_state.last_latency:
        st.sidebar.metric("Last Pipeline Latency", st.session_state.last_latency)

    st.title("🛡️ Multi-Agent Fintech Underwriting & Compliance System")
    st.write("Upload any corporate document (PDF, TXT, CSV, DOCX) to trigger the automated risk assessment pipeline.")
    st.divider()

    # Tabs configuration
    tab1, tab2 = st.tabs(["📋 Loan Application Intake", "⚙️ Administrative Oversight Panel"])
    
    file_is_valid = False
    file_context = "No input file provided by user. Operating in fallback sandbox mode."
    company_input = "Apex Global Logistics Solutions Pvt Ltd"

    with tab1:
        uploaded_file = st.file_uploader(
            "Choose a financial or corporate document", 
            type=["pdf", "txt", "csv", "docx"],
            help="Accepts financial statements, tax disclosures, ledgers, or registration files."
        )

        MAX_FILE_SIZE_MB = 2
        MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

        if uploaded_file is not None:
            if uploaded_file.size > MAX_FILE_SIZE_BYTES:
                st.error(f"File size exceeds the maximum allowable limit of {MAX_FILE_SIZE_MB}MB.")
            else:
                with st.spinner("Extracting content from binary layout..."):
                    try:
                        file_context = extract_text_from_file(uploaded_file)

                        if not file_context or len(file_context.strip()) < 10:
                            st.error("Validation Error: The uploaded document appears to be empty or unreadable.")
                            file_is_valid = False
                        elif file_context.count('?') > len(file_context) * 0.3 or len([c for c in file_context if c.isalnum()]) < len(file_context) * 0.2:
                            st.error("Content Integrity Error: Scrambled or corrupted text streams detected.")
                            file_is_valid = False
                        else:
                            parsed = parse_financial_metrics_from_text(file_context)
                            hint = format_metrics_hint(parsed)
                            if hint:
                                file_context = file_context + "\n\n" + hint
                            st.success(f"File successfully parsed and staged: **{uploaded_file.name}**")
                            file_is_valid = True
                            
                            with st.expander("View Extracted Document Stream Preview"):
                                st.text_area("Raw Text Sample", value=file_context[:1000], height=150, disabled=True)
                    except Exception as e:
                        st.error(f"Critical Parser Engine Failure: {str(e)}")
                        file_is_valid = False

        st.divider()

        # ====================================================================
        # STEP 1 & 2: REGULATORY BLACKLIST PRE-SCREENING BUTTON
        # ====================================================================
        # If intercepted, hide execution interface completely in Tab 1 until manual switch/clearance occurs.
        if st.session_state.compliance_intercepted:
            st.warning(" Application Processing Interrupted. A manual compliance check is required in the 'Administrative Oversight Panel' before continuing.")
            
        elif not st.session_state.compliance_passed:
            if st.button("Initiate Onboarding & Compliance Audit", type="primary", disabled=(not file_is_valid)):
                st.session_state.company_to_process = company_input
                
                with st.spinner("Running Automated Regulatory Screening Engine..."):
                    compliance_result = str(run_compliance_check(company_input))
                    
                if "CRITICAL_MATCH_FOUND" in compliance_result:
                    st.session_state.compliance_intercepted = True
                    st.session_state.compliance_passed = False # Explicit safety lock
                    st.toast(" Compliance Alert! Risk Intercept Activated.", icon="⚠️")
                    st.rerun()
                else:
                    st.session_state.compliance_passed = True
                    st.success("Automated Compliance Screening Passed Cleanly.")
                    st.rerun()

        # ====================================================================
        # STEP 3: FINAL RISK ASSESSMENT PIPELINE RUNNER
        # ====================================================================
        if st.session_state.compliance_passed:
            st.success(f"- Compliance Clearance Approved for: **{st.session_state.company_to_process}**")
            
            if st.button(" Run Risk Assessment Pipeline", type="primary"):
                with st.spinner("Agents are analyzing multi-page documents, recalling memory states, and executing structural validations..."):
                    st.toast("Local Gemma 3 Engine executing context analytics...")
                    try:
                        start_time = time.time()
                        
                        crew = create_fintech_crew()
                        crew_output = crew.kickoff(inputs={"document_context": file_context})
                        
                        # Fallback: if LLM produced DSCR=0, use regex-parsed metrics
                        parsed = parse_financial_metrics_from_text(file_context)
                        if hasattr(crew_output, 'pydantic') and crew_output.pydantic is not None:
                            ft = crew_output.pydantic.financial_telemetry
                            if ft and (ft.calculated_dscr == 0.0 or ft.calculated_dscr >= 999.0):
                                pm = parsed.get("calculated_dscr", 0.0)
                                if pm > 0:
                                    ft.calculated_dscr = pm
                                    if parsed.get("gross_revenue"):
                                        ft.gross_revenue = parsed["gross_revenue"]
                                    if parsed.get("net_operating_income"):
                                        ft.net_operating_income = parsed["net_operating_income"]
                                    if parsed.get("total_debt_service"):
                                        ft.total_debt_service = parsed["total_debt_service"]
                        
                        latency = time.time() - start_time
                        st.session_state.last_latency = f"{latency:.2f}s"

                        st.success(" System Integration Complete!")
                        render_dossier_dashboard(crew_output)
                       
                    except Exception as e:
                        st.error(f"System Integration Error: {e}")
                        st.exception(e)

    with tab2:
        st.title("Administrative Oversight Panel")
        st.write("Monitor flagged applications and perform human-in-the-loop overrides.")
        
        # Human-in-the-loop intervention required block
        if st.session_state.compliance_intercepted:
            st.error(" RISK INTERCEPT: This company matches records on the Regulatory Compliance Blacklist!")
            st.write(f"Reviewing Flagged Match Record for: **{st.session_state.company_to_process}**")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Manual Override (Approve for Underwriting)", key="override_btn"):
                    # Elevate credentials and grant clearance manually
                    st.session_state.compliance_intercepted = False
                    st.session_state.compliance_passed = True
                    st.toast("Application unlocked by Administrator.", icon="🔓")
                    st.rerun()
                    
            with col2:
                if st.button("Reject Entity Permanently", key="reject_btn"):
                    st.error(f"Application Denied for '{st.session_state.company_to_process}'. Stream dropped.")
                    st.session_state.compliance_intercepted = False
                    st.session_state.compliance_passed = False
                    st.rerun()
        else:
            st.info("No active compliance intercepts requiring manual authorization at this time.")

if __name__ == "__main__":
    main()