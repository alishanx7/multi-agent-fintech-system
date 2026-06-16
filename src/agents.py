import os
import joblib
import pandas as pd
from dotenv import load_dotenv
from crewai import Agent, Crew, Process, LLM, Task  # All critical imports hoisted to the top
from crewai.tools import tool
from pydantic import BaseModel, Field
from typing import List, Optional

# Imported custom backend functions
from src.tools.ocr_tool import extract_text_from_pdf
from src.algorithms import evaluate_financial_risk
from src.tools.db_tool import screen_corporate_entity

class FinancialMetricsSchema(BaseModel):
    company_name: str = Field(description="The exact legal name of the corporate entity.")
    gross_revenue: float = Field(description="Total extracted revenue or credits.")
    total_debt_service: float = Field(description="Total operational debits or debt obligations.")
    net_operating_income: float = Field(description="Calculated net operating income.")
    calculated_dscr: float = Field(description="The final computed Debt Service Coverage Ratio (NOI / Debt Service).")

class ComplianceMetricsSchema(BaseModel):
    watchlist_checked: bool = Field(description="True if the local SQLite compliance database was scanned.")
    blacklist_match_found: bool = Field(description="True if the entity was explicitly flagged in the database.")
    final_clearance_status: str = Field(description="Must be 'PASSED', 'DENIED', or 'MANUAL_OVERRIDE_APPROVED'.")

class UnderwritingDossierSchema(BaseModel):
    financial_telemetry: FinancialMetricsSchema
    compliance_telemetry: ComplianceMetricsSchema
    credit_decision: str = Field(description="Explicit final decision: 'APPROVED' or 'DECLINED'.")
    risk_tier: str = Field(description="Assessed risk profile: 'LOW RISK', 'MEDIUM RISK', or 'HIGH RISK'.")
    underwriter_justification: str = Field(description="Detailed analytical rationale for the final credit decision.")
# ====================================================================
# 1. ENVIRONMENT CONFIGURATION & MODEL INITIALIZATION
# ====================================================================
load_dotenv()

# First-class Gemini integration for orchestration and reasoning
gemini_model = LLM(
    model="gemini/gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
)

def get_ml_risk_score(revenue, debt, noi):
    """Predicts risk using the trained Random Forest model."""
    model = joblib.load('models/risk_model.pkl')
    prediction = model.predict([[revenue, debt, noi]])
    return "High Risk" if prediction[0] == 1 else "Low Risk"

# ====================================================================
# 2. DEFINING CREWAI COMPATIBLE CUSTOM TOOLS
# ====================================================================

@tool("PDF Document Text Extractor")
def ocr_extraction_tool(pdf_path: str) -> str:
    """Reads a local PDF file path and extracts its entire raw text content."""
    return extract_text_from_pdf(pdf_path)


@tool("Algorithmic Risk Underwriter Engine")
def financial_underwriting_tool(net_operating_income: float, total_debt_service: float, monthly_revenue: float) -> dict:
    """Calculates financial risk metrics (DSCR, Risk Tier) by processing business metrics."""
    return evaluate_financial_risk(net_operating_income, total_debt_service, monthly_revenue)


@tool("SQLite Corporate Compliance Watchlist Screener")
def compliance_screening_tool(company_name: str) -> str:
    """Queries local SQLite database to check if a corporate entity name is blacklisted."""
    return check_compliance_blacklist(company_name)


# ====================================================================
# 3. STANDALONE COMPLIANCE CHECK WORKFLOW 
# ====================================================================

# This dedicated agent runs the immediate pre-screening check
compliance_officer = Agent(
    role="Regulatory Compliance Specialist",
    goal="Identify and flag institutional risk, sanctions, or corporate fraud footprints.",
    backstory="An elite regulatory auditor dedicated to preventing money laundering and fraud.",
    tools=[screen_corporate_entity], 
    llm=gemini_model,
    verbose=True
)

def run_compliance_check(company_name: str):
    """
    WEEK 4 MILESTONE: Intercept check.
    Executes a standalone screening task. 
    Returns the exact result to the orchestrator to check for intercepts.
    """
    screening_task = Task(
        description=f"Run a comprehensive regulatory background check on the entity: '{company_name}'. Use your tools to check internal databases.",
        expected_output="A string explicitly starting with 'CRITICAL_MATCH_FOUND' with risk analysis details, or 'CLEAN'.",
        agent=compliance_officer
    )
    
    crew = Crew(
        agents=[compliance_officer],
        tasks=[screening_task],
        process=Process.sequential
    )
    
    return crew.kickoff()


# ====================================================================
# 4. MULTI-AGENT UNDERWRITING FACTORY
# ====================================================================

def create_fintech_crew():
    """Instantiates the three pipeline agents and links their tasks cleanly."""
    
    # Node 1: Ingestion Analyst
    ingestion_agent = Agent(
        role='Financial Document Ingestion Analyst',
        goal='Accurately parse extracted document text streams to identify corporate names and financial balance aggregates.',
        backstory='An expert in reading unstructured financial data, tax disclosures, bank statements, and accounting ledger formats.',
        tools=[ocr_extraction_tool],
        llm=gemini_model,
        max_iter=2,
        verbose=True,
        allow_delegation=False
    )

    # Node 2: Credit Underwriter
    underwriting_agent = Agent(
        role='Credit Risk Underwriter',
        goal='Apply strict algorithmic underwriting rules to assess leverage capacity and generate credit decisions.',
        backstory='A veteran fintech credit analyst responsible for calculating risk metrics like DSCR and parsing cash health ratios.',
        tools=[financial_underwriting_tool],
        llm=gemini_model,
        max_iter=2,
        verbose=True,
        allow_delegation=False
    )

    # Node 3: Compliance Auditor
    compliance_agent = Agent(
        role='Corporate Compliance and AML Enforcement Auditor',
        goal='Ensure applicant entities do not appear on high-risk watchlists or global legal restriction lists.',
        backstory='Specialized in anti-money laundering frameworks and corporate screening databases to safeguard institutional capital.',
        tools=[compliance_screening_tool],
        llm=gemini_model,
        max_iter=2,
        verbose=True,
        allow_delegation=False
    )

    # Task Configurations
    ingestion_task = Task(
        description=(
           "Analyze the following user-uploaded document context string:\n\n"
           "--- START DOCUMENT ---\n"
           "{document_context}\n"  
           "--- END DOCUMENT ---\n\n"
           "Identify the exact legal corporate name and aggregate all key balance metrics from this data stream."
        ),
        expected_output="A structured summary containing the verified corporate identity and key financial data points.",
        agent=ingestion_agent
    )

    underwriting_task = Task(
        description=(
           "Use the parsed data extracted by the ingestion analyst to calculate leverage metrics. "
           "Focus strictly on determining the Debt Service Coverage Ratio (DSCR) and cash stability metrics."
        ),
        expected_output="An algorithmic underwriting profile with risk ratios and an explicit credit capacity decision.",
        agent=underwriting_agent
    )

    compliance_task = Task(
        description=(
            "Cross-verify the corporate entity against global high-risk watchlists and anti-money laundering (AML) frameworks. "
            "Compile all data metrics, risk tiers, calculations, and decisions from previous stages into the required structured format."
        ),
        expected_output="A perfectly formatted JSON object matching the UnderwritingDossierSchema structure.",
        agent=compliance_agent,
        output_json=UnderwritingDossierSchema
    )

    # Assembly Line
    fintech_crew = Crew(
        agents=[ingestion_agent, underwriting_agent, compliance_agent],
        tasks=[ingestion_task, underwriting_task, compliance_task],
        process=Process.sequential,
        verbose=True,
        memory=True,              # Activated the overarching memory context system
        embedder={
            "provider": "google-generativeai",
            "config": {
                "model": "models/embedding-001", # Light, super-fast embedding model
                "api_key": os.getenv("GEMINI_API_KEY")
            }
        },
        max_rpm=2,
        cache=True
    )

    return fintech_crew