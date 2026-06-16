# ====================================================================
# ACTIVED: CREWAI FORMAL TASK EXECUTION TEST
# ====================================================================

import os
from crewai import Task, Crew, Process
from src.agents import create_fintech_crew

def run_autonomous_fintech_pipeline():
    print("=== INITIALIZING MULTI-AGENT AUTONOMOUS RISK AUDIT ===")
    
    # Locates the target PDF statement inside your local data folder
    data_dir = os.path.join(os.getcwd(), 'data')
    pdf_files = [f for f in os.listdir(data_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("[!] Execution Halted: No target PDF found in 'data/' directory.")
        return
    
    target_pdf_path = os.path.join(data_dir, pdf_files[0])
    print(f"[*] Target Statement Located: {pdf_files[0]}")

    # ====================================================================
    # FALLBACK CHECK: If your tool crashes because it's a fake PDF, 
    # pre-extract the plain text right here so your agent can still read it.
    # ====================================================================
    fallback_text_injection = None
    try:
        with open(target_pdf_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # If the file contains readable plaintext instead of binary PDF headers (%PDF)
            if "%PDF" not in content and len(content.strip()) > 0:
                fallback_text_injection = content
                print("[*] Notice: Plain text format detected inside PDF extension. Activating text injection fallback.")
    except Exception:
        pass # If it's a real binary PDF, reading it like a text file fails, which is expected.
    # ====================================================================

    try:
        # 1. Fetch armed factory agents
        crew_setup = create_fintech_crew()
        agents_list = crew_setup["agents"]
        
        ingestion_agent = agents_list[0]
        underwriter_agent = agents_list[1]
        compliance_agent = agents_list[2]

        print("[*] Framing sequential cross-node tasks...")

        # Update description dynamically if we intercepted plain text content
        if fallback_text_injection:
            ingestion_description = f"The target document at '{target_pdf_path}' failed standard PDF binary validation, but its plain text content was recovered. Analyze this raw text data directly: \n\n{fallback_text_injection}\n\nIdentify the corporate entity name, monthly revenue, net operating income, and total debt service payments."
        else:
            ingestion_description = f"Extract the text layout from the document at '{target_pdf_path}' using your tool. Identify the corporate entity name, monthly revenue, net operating income, and total debt service payments."

        # 2. Task 1: Read PDF and isolate raw numbers/names
        task_ingestion = Task(
            description=ingestion_description,
            expected_output="A structured summary showing Company Name, Monthly Revenue, Net Operating Income, and Total Debt Service.",
            agent=ingestion_agent
        )

        # 3. Task 2: Underwrite risk using the numbers found by the ingestion agent
        task_underwriting = Task(
            description="Review the financial data extracted by the Ingestion Analyst. Pass those extracted financial values into your underwriting engine tool to calculate risk tiers and financial viability.",
            expected_output="An analytical credit evaluation summary containing the risk tier, calculated metrics, and credit limit decision.",
            agent=underwriter_agent
        )

        # 4. Task 3: Screen the company name and compile the final comprehensive report
        task_compliance = Task(
            description=(
                "Take the corporate entity name discovered by the Ingestion Analyst and check its legality status "
                "using your compliance database screening tool. Once checked, take the Analytical Credit Evaluation "
                "Summary from the Credit Risk Underwriter, append your Final Compliance Status to it, and format it "
                "into a clean, comprehensive final audit dossier."
            ),
            expected_output=(
                "A complete, professional risk dossier containing: 1) The full Credit Underwriting evaluation "
                "(Risk Tier, DSCR, and Credit Limit Decision) and 2) The Compliance Watchlist screening status."
            ),
            agent=compliance_agent
        )

        # 5. Assembled the production-grade Crew using SEQUENTIAL processing
        fintech_risk_crew = Crew(
            agents=[ingestion_agent, underwriter_agent, compliance_agent],
            tasks=[task_ingestion, task_underwriting, task_compliance],
            process=Process.sequential, # Hand-off happens sequentially down the line
            verbose=True
        )

        print("[*] Operational Nodes Armed. Initializing Crew Pipeline Kickoff...\n")
        
        # 6. Let the crew deliberate, execute tools, and finalize results autonomously
        final_assessment_report = fintech_risk_crew.kickoff()

        print("\n================== FINAL MULTI-AGENT COMPREHENSIVE REPORT ==================")
        print(final_assessment_report)
        print("============================================================================")
        print("\n[✔] Week 3 Multi-Agent Autonomous Pipeline Run Succeeded!")

    except Exception as e:
        print(f"\n[!] Critical pipeline breakdown: {e}")

if __name__ == "__main__":
    run_autonomous_fintech_pipeline()