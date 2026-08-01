"""
FastAPI Backend Server for Multi-Agent Fintech System
Connects Next.js Frontend with CrewAI Local/Cloud Agents
"""

import sys
import os
import uuid
import json
import re
import pdfplumber
import docx
from io import BytesIO
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.agents import UnderwritingDossierSchema, create_fintech_crew, run_compliance_check, local_llm
from src.algorithms import parse_financial_metrics_from_text, format_metrics_hint
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

def extract_text_from_bytes(raw_bytes: bytes, filename: str = "", content_type: str = "") -> str:
    """Extract text from raw document bytes (pdf/docx/txt/csv)."""
    if not raw_bytes:
        return ""
    name_lower = filename.lower()
    type_lower = content_type.lower()
    is_pdf = "pdf" in type_lower or name_lower.endswith(".pdf")
    is_docx = "wordprocessingml" in type_lower or name_lower.endswith(".docx")
    is_txt = "plain" in type_lower or name_lower.endswith(".txt")
    is_csv = "csv" in type_lower or name_lower.endswith(".csv")
    try:
        if is_pdf:
            with pdfplumber.open(BytesIO(raw_bytes)) as pdf:
                return "".join(page.extract_text() or "" for page in pdf.pages).strip()
        elif is_docx:
            doc = docx.Document(BytesIO(raw_bytes))
            return "\n".join(p.text for p in doc.paragraphs if p.text).strip()
        elif is_txt or is_csv:
            return raw_bytes.decode("utf-8", errors="ignore").strip()
        return raw_bytes.decode("utf-8", errors="ignore").strip()
    except OSError as e:
        raise RuntimeError(f"Document I/O error: {e}. Please retry.")
    except Exception as e:
        raise RuntimeError(f"Document parse error: {e}")

app = FastAPI(title="Fintech Underwriting API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In‑memory store for session results
SESSION_STORE: dict[str, dict] = {}

class ComplianceRequest(BaseModel):
    company_name: str


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _fallback_risk_explanation(dossier: dict) -> str:
    financial = dossier.get("financial_telemetry", {}) if isinstance(dossier, dict) else {}
    dscr = _safe_float(financial.get("calculated_dscr", 0.0))
    revenue = _safe_float(financial.get("gross_revenue", 0.0))
    risk_tier = str(dossier.get("risk_tier", "UNKNOWN")).upper() if isinstance(dossier, dict) else "UNKNOWN"
    decision = str(dossier.get("credit_decision", "UNDER REVIEW")).upper() if isinstance(dossier, dict) else "UNDER REVIEW"

    if decision == "REJECTED":
        reason = "debt coverage is not strong enough to support safe lending"
    elif decision == "FLAGGED FOR REVIEW":
        reason = "coverage is borderline and requires an underwriter's manual review"
    else:
        reason = "cashflow coverage is healthy relative to debt obligations"

    return (
        f"This application is classified as {risk_tier} with a credit decision of {decision}. "
        f"The calculated DSCR is {dscr:.2f}, and the reported monthly revenue is {revenue:,.2f}. "
        f"Based on these metrics, the profile indicates that {reason}."
    )


def _generate_llm_explanation(prompt: str, dossier: dict) -> str:
    call_fn = getattr(local_llm, "call", None)
    if not callable(call_fn):
        return _fallback_risk_explanation(dossier)

    response = call_fn(prompt)
    if isinstance(response, str) and response.strip():
        return response.strip()

    return _fallback_risk_explanation(dossier)

@app.get("/")
def read_root():
    return {"status": "Active", "engine": "Fintech Multi-Agent API"}

@app.post("/api/compliance-check")
def check_compliance(payload: ComplianceRequest):
    """Compliance pre-screening check."""
    result = str(run_compliance_check(payload.company_name))
    is_intercepted = "CRITICAL_MATCH_FOUND" in result
    return {
        "company_name": payload.company_name,
        "intercepted": is_intercepted,
        "status": "FLAGGED" if is_intercepted else "PASSED",
    }

@app.post("/api/run-underwriting")
def run_underwriting(file: UploadFile = File(...)):
    """Runs financial document through CrewAI pipeline with forgiving parsing."""
    try:
        # Reset file position and read into memory to avoid I/O errors
        try:
            file.file.seek(0)
        except (OSError, AttributeError):
            pass
        raw_bytes = file.file.read()
        if not raw_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Extract text directly from raw bytes (no temp file dependency)
        file_context = extract_text_from_bytes(
            raw_bytes,
            filename=file.filename or "upload.bin",
            content_type=file.content_type or "",
        )

        # Pre-parse financial metrics as deterministic fallback
        parsed_metrics = parse_financial_metrics_from_text(file_context)
        hint = format_metrics_hint(parsed_metrics)
        if hint:
            file_context = file_context + "\n\n" + hint

        # Kick off CrewAI pipeline
        crew = create_fintech_crew()
        crew_output = crew.kickoff(inputs={"document_context": file_context})

        # Extract primary JSON block
        raw_text = crew_output.raw.strip() if hasattr(crew_output, "raw") else str(crew_output)
        start_idx = raw_text.find('{')
        if start_idx != -1:
            bracket_count = 0
            end_idx = -1
            for i in range(start_idx, len(raw_text)):
                if raw_text[i] == '{':
                    bracket_count += 1
                elif raw_text[i] == '}':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i
                        break
            if end_idx != -1:
                raw_text = raw_text[start_idx:end_idx+1]
        # Clean commas
        cleaned_text = re.sub(r'(\"([^\"\\\\]|\\\\.)*\")\\s*\\n\\s*(\")', r'\\1,\\n\\3', raw_text)
        dossier_data = json.loads(cleaned_text)

        # Guard DSCR magic values
        financial = dossier_data.get("financial_telemetry", {})
        try:
            raw_dscr = float(financial.get("calculated_dscr", 0.0))
        except (ValueError, TypeError):
            raw_dscr = 0.0

        # Fallback: if LLM produced DSCR=0 but regex parser found metrics, use those
        if (raw_dscr == 0.0 or raw_dscr >= 999.0) and parsed_metrics.get("calculated_dscr", 0.0) > 0:
            raw_dscr = parsed_metrics["calculated_dscr"]
            financial["calculated_dscr"] = raw_dscr
            financial["gross_revenue"] = parsed_metrics.get("gross_revenue", financial.get("gross_revenue", 0.0))
            financial["net_operating_income"] = parsed_metrics.get("net_operating_income", financial.get("net_operating_income", 0.0))
            financial["total_debt_service"] = parsed_metrics.get("total_debt_service", financial.get("total_debt_service", 0.0))
            dossier_data["financial_telemetry"] = financial

        if raw_dscr >= 999.0 or raw_dscr < 0.0:
            raw_dscr = 0.0
            financial["calculated_dscr"] = 0.0
            dossier_data["financial_telemetry"] = financial

        # Decision guard (demo mode handling omitted for brevity)
        DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
        if DEMO_MODE:
            dossier_data["risk_tier"] = "LOW RISK"
            dossier_data["credit_decision"] = "APPROVED"
            dossier_data.setdefault("financial_telemetry", {"calculated_dscr": 1.5})
        else:
            risk_tier = str(dossier_data.get("risk_tier", "")).upper()
            if "HIGH" in risk_tier or raw_dscr < 1.0 or raw_dscr == 0.0:
                dossier_data["risk_tier"] = "HIGH RISK"
                dossier_data["credit_decision"] = "REJECTED"
                if raw_dscr == 0.0:
                    dossier_data["warning"] = (
                        "Uploaded document does not contain recognizable financial metrics (DSCR = 0). "
                        "Please provide a proper financial statement."
                    )
            elif "MEDIUM" in risk_tier or (1.0 <= raw_dscr < 1.25):
                dossier_data["risk_tier"] = "MEDIUM RISK"
                dossier_data["credit_decision"] = "FLAGGED FOR REVIEW"
            else:
                dossier_data["risk_tier"] = "LOW RISK"
                dossier_data["credit_decision"] = "APPROVED"

        # Ensure required sub‑objects exist
        dossier_data.setdefault("financial_telemetry", {})
        dossier_data.setdefault("compliance_telemetry", {})

        # Validate schema
        validated = UnderwritingDossierSchema(**dossier_data)

        # Generate a session ID and store the raw dossier for later endpoints
        session_id = str(uuid.uuid4())
        SESSION_STORE[session_id] = dossier_data

        return {"status": "success", "data": validated.dict(), "session_id": session_id}
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Document processing I/O error: {e}. Please retry with a fresh upload.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# Post‑analysis helper endpoints
# ---------------------------------------------------------------------------

@app.get("/api/financial-breakdown/{session_id}")
def get_financial_breakdown(session_id: str):
    dossier = SESSION_STORE.get(session_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"financial_telemetry": dossier.get("financial_telemetry", {})}

@app.get("/api/explain-risk/{session_id}")
def explain_risk(session_id: str):
    dossier = SESSION_STORE.get(session_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Session not found")
    prompt = (
        "You are a financial analyst. Based on the following underwriting dossier, "
        "explain the risk factors in clear, non‑technical language. Only reference information "
        "present in the dossier. Return a concise paragraph.\n\nDossier: "
        + json.dumps(dossier)
    )
    try:
        explanation = _generate_llm_explanation(prompt, dossier)
    except Exception:
        explanation = _fallback_risk_explanation(dossier)
    return {"explanation": explanation}

@app.get("/api/benchmark/{session_id}")
def benchmark_comparison(session_id: str):
    dossier = SESSION_STORE.get(session_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Session not found")
    # Simple static benchmarks (could be expanded later)
    benchmarks = {
        "average_dscr": 1.4,
        "average_monthly_revenue": 500_000,
    }
    financial = dossier.get("financial_telemetry", {})
    result = {
        "dscr": financial.get("calculated_dscr", None),
        "monthly_revenue": financial.get("gross_revenue", None),
        "benchmark": benchmarks,
    }
    return result

@app.get("/api/download-pdf/{session_id}")
def download_pdf(session_id: str):
    dossier = SESSION_STORE.get(session_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Session not found")

    financial = dossier.get("financial_telemetry", {})
    compliance = dossier.get("compliance_telemetry", {})
    explanation = _fallback_risk_explanation(dossier)

    try:
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Underwriting Dossier", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"<b>Session ID:</b> {session_id}", styles["Normal"]))
        story.append(Paragraph(f"<b>Risk Tier:</b> {dossier.get('risk_tier', 'N/A')}", styles["Normal"]))
        story.append(Paragraph(f"<b>Credit Decision:</b> {dossier.get('credit_decision', 'N/A')}", styles["Normal"]))
        story.append(Spacer(1, 10))

        story.append(Paragraph("<b>Risk Explanation</b>", styles["Heading3"]))
        story.append(Paragraph(explanation, styles["Normal"]))
        story.append(Spacer(1, 10))

        story.append(Paragraph("<b>Financial Telemetry</b>", styles["Heading3"]))
        story.append(Paragraph(
            f"Company: {financial.get('company_name', 'N/A')}<br/>"
            f"Gross Revenue: {financial.get('gross_revenue', 0)}<br/>"
            f"Total Debt Service: {financial.get('total_debt_service', 0)}<br/>"
            f"Net Operating Income: {financial.get('net_operating_income', 0)}<br/>"
            f"Calculated DSCR: {financial.get('calculated_dscr', 0)}",
            styles["Normal"],
        ))
        story.append(Spacer(1, 10))

        story.append(Paragraph("<b>Compliance Telemetry</b>", styles["Heading3"]))
        story.append(Paragraph(json.dumps(compliance, indent=2).replace("\n", "<br/>"), styles["Normal"]))

        doc.build(story)
        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=underwriting_{session_id}.pdf"},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)