import os
from crewai import Agent, LLM
from crewai.tools import tool
import joblib
import pandas as pd

def get_ml_risk_score(revenue, debt, noi):
    """Predicts risk using the trained Random Forest model."""
    model = joblib.load('models/risk_model.pkl')
    prediction = model.predict([[revenue, debt, noi]])
    return "High Risk" if prediction[0] == 1 else "Low Risk"

# Import your custom backend functions
from src.tools.ocr_tool import extract_text_from_pdf
from src.algorithms import evaluate_financial_risk
from src.tools.db_tool import check_compliance_blacklist

# 1. Paste your Gemini API key here inside the quotation marks
import os
from dotenv import load_dotenv

# Load the keys securely from your local hidden .env file
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# 2. Bundle the model and the key into a unified LLM config block
gemini_model = LLM(
    model="gemini/gemini-2.5-flash",
    api_key=GEMINI_KEY
)

# ====================================================================
# DEFINING CREWAI COMPATIBLE CUSTOM TOOLS
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
def compliance_screening_tool(company_name: str) -> dict:
    """Queries local SQLite database to check if a corporate entity name is blacklisted."""
    return check_compliance_blacklist(company_name)


# ====================================================================
# CREATING THE MULTI-AGENT FACTORY
# ====================================================================

def create_fintech_crew():
    """Instantiates the three agents and links their LLMs and Tools cleanly."""
    
    # Node 1: Ingestion Analyst
    ingestion_agent = Agent(
        role='Financial Document Ingestion Analyst',
        goal='Accurately parse extracted document text streams to identify corporate names and financial balance aggregates.',
        backstory='An expert in reading unstructured financial data, tax disclosures, bank statements, and accounting ledger formats.',
        tools=[ocr_extraction_tool],
        llm=gemini_model, # <-- Pass the structured LLM block here cleanly
        max_iter=3,        # Hard stop for this specific agent
        max_rpm=10,        # Keeps this agent's "speed" within your budget
        verbose=True,
        allow_delegation=False
    )

    # Node 2: Credit Underwriter
    underwriting_agent = Agent(
        role='Credit Risk Underwriter',
        goal='Apply strict algorithmic underwriting rules to assess leverage capacity and generate credit decisions.',
        backstory='A veteran fintech credit analyst responsible for calculating risk metrics like DSCR and parsing cash health ratios.',
        tools=[financial_underwriting_tool],
        llm=gemini_model, # <-- Pass the structured LLM block here cleanly
        max_iter=3,        # Hard stop for this specific agent
        max_rpm=10,        # Keeps this agent's "speed" within your budget
        verbose=True,
        allow_delegation=False
    )

    # Node 3: Compliance Auditor
    compliance_agent = Agent(
        role='Corporate Compliance and AML Enforcement Auditor',
        goal='Ensure applicant entities do not appear on high-risk watchlists or global legal restriction lists.',
        backstory='Specialized in anti-money laundering frameworks and corporate screening databases to safeguard institutional capital.',
        tools=[compliance_screening_tool],
        llm=gemini_model, # <-- Pass the structured LLM block here cleanly
        max_iter=3,        # Hard stop for this specific agent
        max_rpm=10,        # Keeps this agent's "speed" within your budget
        verbose=True,
        allow_delegation=False
    )
# ... (Keep your ingestion_agent, underwriting_agent, and compliance_agent definitions exactly as they are) ...

    # ==========================================
    # TASK DEFINITIONS (Add this right below compliance_agent)
    # ==========================================
    from crewai import Task, Crew, Process

    ingestion_task = Task(
        description=(
           "Analyze the following user-uploaded document context: \n\n"
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
            "Focus strictly on determining the Debt Service Coverage Ratio (DSCR) and cash stability metrics based on the provided document context."
        ),
        expected_output="An algorithmic underwriting profile with risk ratios and an explicit credit capacity decision.",
        agent=underwriting_agent
    )

    compliance_task = Task(
        description=(
            "Cross-verify the corporate entity against global high-risk watchlists and anti-money laundering (AML) frameworks. "
            "Compile all findings from previous stages into a single, cohesive risk assessment report."
        ),
        expected_output="The final comprehensive underwriting and compliance dossier.",
        agent=compliance_agent
    )

    # ==========================================
    # CREW ASSEMBLY
    # ==========================================
    fintech_crew = Crew(
        agents=[ingestion_agent, underwriting_agent, compliance_agent],
        tasks=[ingestion_task, underwriting_task, compliance_task],
        process=Process.sequential,  # Guarantees the step-by-step pipeline
        verbose=True,               # Keeps your colored logging terminal visible
        memory=True,
        max_rpm=15,                 # Master safety governor
        cache=True                  # Avoids redundant API calls
    )

    return fintech_crew
 # ... (all your agent definitions: ingestion_agent, underwriting_agent, compliance_agent) ...
