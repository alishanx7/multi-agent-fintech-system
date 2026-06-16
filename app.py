"""
Multi-Agent Fintech Underwriting & Compliance System
Streamlit application entry point with Comprehensive Binary File Extraction (PDF, DOCX, TXT, CSV).
"""

import streamlit as st 
import pypdf
import docx
import re
import os
import joblib

# Imported custom backend functions
from src.agents import create_fintech_crew, run_compliance_check

# Initialized Session State flags before anything else compiles
if "compliance_intercepted" not in st.session_state:
    st.session_state.compliance_intercepted = False
if "company_to_process" not in st.session_state:
    st.session_state.company_to_process = ""
if "compliance_passed" not in st.session_state:
    st.session_state.compliance_passed = False

def extract_text_from_file(uploaded_file):
    """Universal text extraction utility for financial and corporate documents."""
    text = ""
    file_type = uploaded_file.type

    try:
        # Handles PDF documents
        if file_type == "application/pdf":
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                    
        # Handles Word documents (.docx)
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = docx.Document(uploaded_file)
            for paragraph in doc.paragraphs:
                if paragraph.text:
                    text += paragraph.text + "\n"
                    
        # Handles standard plain text files (.txt)
        elif file_type == "text/plain":
            text = uploaded_file.getvalue().decode("utf-8")
            
        # Handles tabular data comma-separated files (.csv)
        elif file_type == "text/csv":
            text = uploaded_file.getvalue().decode("utf-8")
            
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"Parser Engine failure during extraction: {str(e)}")

#  NEW: HELPER FUNCTION (Root level)
def render_dossier_dashboard(crew_output):
    """Component to render dashboard metrics from Pydantic data."""
    dossier_data = crew_output.pydantic.dict()
    
    # Extract
    financial = dossier_data.get("financial_telemetry", {})
    dscr = f"{financial.get('calculated_dscr', 0.0):.2f}"
    
    # Render UI
    st.header(" Real-Time Underwriting Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Calculated DSCR", dscr)
    # ... add your other metrics here ...
    st.json(dossier_data)

def main():
    st.set_page_config(page_title="Fintech Underwriting System", layout="wide")
    #  PROFESSIONAL FINTECH UI
    # 2. Separation Tabs
    tab1, tab2 = st.tabs([" Loan Application", " Admin Override Panel"])
    
    with tab1:
        st.title("Loan Application Intake")
        # uploader and pipeline button here
        
    with tab2:
        st.title("Administrative Oversight")
        st.write("Monitor flagged applications and perform human-in-the-loop overrides.")
        # 'compliance_intercepted' logic here
    st.title(" Multi-Agent Fintech Underwriting & Compliance System")
    st.write("Upload any corporate document (PDF, TXT, CSV, DOCX) to trigger the automated risk assessment pipeline.")
    
    st.divider()

    # System Configuration Sidebar
    st.sidebar.header("System Configuration")
    st.sidebar.success("API Protection: ENABLED")
    st.sidebar.info("Agent Rate Limits: 10 RPM\nMax Iterations: 3")
    st.sidebar.info("Parser Engine: Active (PDF/Docx/TXT)")

    # Frontend Universal File Uploader Component
    uploaded_file = st.file_uploader(
        "Choose a financial or corporate document", 
        type=["pdf", "txt", "csv", "docx"],
        help="Accepts financial statements, tax disclosures, ledgers, or registration files."
    )

    # Defining safety threshold (2 Megabytes)
    MAX_FILE_SIZE_MB = 2
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    # Context Display & Size Validation Area
    file_is_valid = False
    file_context = ""

    # Seting up the fallback testing target name
    company_input = "Apex Global Logistics Solutions Pvt Ltd"

    if uploaded_file is not None:
        if uploaded_file.size > MAX_FILE_SIZE_BYTES:
            st.error(f" File size exceeds the maximum allowable limit of {MAX_FILE_SIZE_MB}MB for this evaluation sandbox.")
        else:
            with st.spinner("Extracting content from binary layout..."):
                try:
                    # Runs the extraction engine
                    file_context = extract_text_from_file(uploaded_file)

                    #  DEFENSIVE EDGE-CASE VALIDATION CHECKS
                    if not file_context or len(file_context.strip()) < 10:
                        st.error(" Validation Error: The uploaded document appears to be empty or unreadable.")
                        file_is_valid = False
                        
                    elif file_context.count('?') > len(file_context) * 0.3 or len([c for c in file_context if c.isalnum()]) < len(file_context) * 0.2:
                        st.error(" Content Integrity Error: Scrambled or corrupted text streams detected.")
                        file_is_valid = False
                        
                    else:
                        st.success(f"File successfully parsed and staged: **{uploaded_file.name}**")
                        file_is_valid = True
                        
                        # Shows an expander for visual validation preview
                        with st.expander(" View Extracted Document Stream Preview"):
                            st.text_area("Raw Text Sample", value=file_context[:1000], height=150, disabled=True)
                            
                except Exception as e:
                    st.error(f" Critical Parser Engine Failure: {str(e)}")
                    file_is_valid = False
    else:
        file_context = "No input file provided by user. Operating in fallback sandbox mode."

    st.divider()

    # ====================================================================
    # STEP 1 & 2: REGULATORY BLACKLIST PRE-SCREENING BUTTON
    # ====================================================================
    if not st.session_state.compliance_passed and not st.session_state.compliance_intercepted:
        if st.button("Initiate Onboarding & Compliance Audit", type="primary", disabled=(not file_is_valid)):
            st.session_state.company_to_process = company_input
            
            with st.spinner("Running Automated Regulatory Screening Engine..."):
                compliance_result = str(run_compliance_check(company_input))
                
            if "CRITICAL_MATCH_FOUND" in compliance_result:
                st.session_state.compliance_intercepted = True
                st.rerun()
            else:
                st.session_state.compliance_passed = True
                st.success(" Automated Compliance Screening Passed Cleanly.")
                st.rerun()

    # ====================================================================
    # HUMAN-IN-THE-LOOP CONTROL PANEL (Only Renders if Intercepted)
    # ====================================================================
    if st.session_state.compliance_intercepted:
        st.error(" RISK INTERCEPT: This company matches records on the Regulatory Compliance Blacklist!")
        st.subheader(" Human-in-the-Loop Intervention Panel")
        st.write(f"Reviewing Match Record for: **{st.session_state.company_to_process}**")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(" Manual Override (Approve for Underwriting)", key="override_btn"):
                st.warning(f"Override Logged. Proceeding with underwriting for: {st.session_state.company_to_process}")
                st.session_state.compliance_intercepted = False
                st.session_state.compliance_passed = True
                st.rerun()
                
        with col2:
            if st.button(" Reject Entity Permanently", key="reject_btn"):
                st.error(f"Application Denied for '{st.session_state.company_to_process}'. Stream dropped.")
                st.session_state.compliance_intercepted = False
                st.session_state.compliance_passed = False
                st.rerun()

   
    # ====================================================================
    # STEP 3: FINAL RISK ASSESSMENT PIPELINE RUNNER
    # ====================================================================
    if st.session_state.compliance_passed:
        st.success(f" Compliance Clearance Approved for: {st.session_state.company_to_process}")
        
        if st.button(" Run Risk Assessment Pipeline", type="primary"):
            with st.spinner("Agents are analyzing multi-page documents, recalling memory states, and executing structural validations..."):
                st.toast("Crew initialized. Local short-term vector embeddings active.")
                try:
                    import time
                    start_time = time.time() #starts performance timer
                    # 1. Initialized upgraded memory-enabled crew
                    crew = create_fintech_crew()
                    crew_output = crew.kickoff(inputs={"document_context": file_context})
                    
                    #2.  performance tracking
                    latency = time.time() - start_time
                    st.session_state.last_latency = f"{latency:.2f}s"
                    st.sidebar.metric("Pipeline Latency", st.session_state.last_latency)

                    st.success(" System Integration Complete!")
                    

                   # 3. Pydantic-Validated Dashboard Rendering
                   # This calls the helper function we placed at the root level
                    render_dossier_dashboard(crew_output)
                   
                except Exception as e:
                        
                    st.error(f" System Integration Error: {e}")
                    st.write("Please check the system logs for structural mismatch details.")
                    st.exception(e)
                    # 3. Pull validated Pydantic properties
                    dossier_data = crew_output.pydantic.dict()

                    financial_metrics = dossier_data.get("financial_telemetry", {})
                    compliance_metrics = dossier_data.get("compliance_telemetry", {})

                    # 4. Type-safe property assignment mapping
                    dscr_display = f"{financial_metrics.get('calculated_dscr', 0.0):.2f}"
                    risk_display = str(dossier_data.get("risk_tier", "UNKNOWN")).upper()
                    credit_decision = str(dossier_data.get("credit_decision", "DECLINED")).upper()
                    justification_text = dossier_data.get("underwriter_justification", "No justification provided.")

                    # Clean UI color delta flags state management
                    if risk_display == "HIGH RISK" or credit_decision == "DECLINED":
                        risk_delta = "Default Warning"
                        delta_color_type = "normal"  # Red
                    else:
                        risk_delta = "Statistical Match"
                        delta_color_type = "inverse"  # Green

                    # 5. Display Core Dashboard Analytics UI
                    st.success("Pipeline Executed with 100% Validated Type Constraints!")
                    st.divider()
                    st.header("Real-Time Underwriting Summary")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(label="Calculated DSCR", value=dscr_display, delta="Target: >1.25")
                    with col2:
                        st.metric(label="Scikit-Learn ML Risk", value=risk_display, delta=risk_delta, delta_color=delta_color_type)
                    with col3:
                        st.metric(label="Compliance Screening", value="PASSED/OVERRIDDEN", delta="0 Blockers Remaining")

                    st.divider()
                    st.subheader("Comprehensive Risk Assessment Dossier")

                    st.markdown(f"### **Credit Capacity Determination:** `{credit_decision}`")
                    st.info(f"**Underwriter Justification:**\n\n{justification_text}")

                    with st.expander("View Validated Structural System Metadata Schema (JSON)"):
                        st.json(dossier_data)

                except Exception as e:
                    st.error("Pipeline Execution Halted Safely")
                    st.exception(e)

if __name__ == "__main__":
    main()