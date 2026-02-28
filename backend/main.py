"""
main.py — FastAPI Application Entry Point for RTI-Saarthi
Run: uvicorn main:app --reload --port 8000
"""
import json
import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

load_dotenv()

# Internal imports
from agents import (AppealAgent, DraftingAgent, FilingAgent, QueryAgent,
                    RoutingAgent)
from utils.database import RTIApplication, generate_ref_number, get_db, init_db
from utils.pdf_generator import generate_rti_pdf

print("Gemini Key:", os.getenv("GEMINI_API_KEY"))

# ── Initialize FastAPI ────────────────────────────────────────
app = FastAPI(
    title="RTI-Saarthi API",
    description="AI-Powered Right to Information Filing Agent",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# ── Initialize DB on startup ──────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    print("✅ RTI-Saarthi API started. DB initialized.")

# ── Initialize Agents ─────────────────────────────────────────
query_agent    = QueryAgent()
routing_agent  = RoutingAgent()
drafting_agent = DraftingAgent()
filing_agent   = FilingAgent()
appeal_agent   = AppealAgent()


# ── Pydantic Models ───────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    question: str
    language: Optional[str] = "en"

class RTIFilingRequest(BaseModel):
    question: str
    applicant_name: str
    applicant_address: str
    applicant_mobile: str
    applicant_email: str
    user_state: Optional[str] = "Delhi"
    is_bpl: Optional[bool] = False
    bpl_card_no: Optional[str] = ""
    language: Optional[str] = "en"

class CheckAppealRequest(BaseModel):
    ref_number: str


# ── Routes ────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "app": "RTI-Saarthi",
        "version": "1.0.0",
        "status": "running",
        "message": "Democratizing Transparency 🇮🇳",
        "docs": "/docs"
    }


@app.post("/api/analyze")
def analyze_question(req: AnalyzeRequest):
    """Agent 1: Analyze citizen's question and extract RTI intent."""
    try:
        result = query_agent.analyze(req.question)
        return {"success": True, "data": result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"analyze failed: {str(e)}")


@app.post("/api/route")
def route_department(req: AnalyzeRequest, state: str = "Delhi"):
    """Agent 2: Find the correct department and PIO."""
    try:
        query_result = query_agent.analyze(req.question)
        routing = routing_agent.route(query_result, state)
        return {"success": True, "data": routing}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/file-rti")
def file_rti(req: RTIFilingRequest, db: Session = Depends(get_db)):
    """Main endpoint: Run all 5 agents and file RTI end-to-end."""
    try:
        query_result = query_agent.analyze(req.question)
        routing = routing_agent.route(query_result, req.user_state)

        applicant = {
            "name": req.applicant_name,
            "address": req.applicant_address,
            "mobile": req.applicant_mobile,
            "email": req.applicant_email,
            "is_bpl": req.is_bpl,
            "bpl_card_no": req.bpl_card_no
        }
        draft = drafting_agent.draft(query_result, routing, applicant)
        ref_number = generate_ref_number(db)
        filing_result = filing_agent.file(draft, routing, ref_number)
        prediction = appeal_agent.predict_success(query_result, routing)

        rti_record = RTIApplication(
            ref_number=ref_number,
            applicant_name=req.applicant_name,
            applicant_email=req.applicant_email,
            applicant_mobile=req.applicant_mobile,
            applicant_address=req.applicant_address,
            is_bpl=req.is_bpl,
            bpl_card_no=req.bpl_card_no,
            original_query=req.question,
            language=req.language,
            department=routing.get("department"),
            pio_id=routing.get("pio", {}).get("id"),
            pio_name=routing.get("pio", {}).get("pio_name"),
            pio_email=routing.get("pio", {}).get("email"),
            subject=draft.get("subject"),
            questions=json.dumps(draft.get("formal_questions", [])),
            draft_text=draft.get("full_application_text"),
            status="filed",
            filed_date=datetime.now(),
        )
        db.add(rti_record)
        db.commit()
        db.refresh(rti_record)

        return {
            "success": True,
            "ref_number": ref_number,
            "query_analysis": query_result,
            "routing": {
                "department": routing.get("department"),
                "pio_name": routing.get("pio", {}).get("pio_name"),
                "pio_email": routing.get("pio", {}).get("email"),
                "portal": routing.get("filing_url"),
                "jurisdiction": routing.get("jurisdiction")
            },
            "draft": {
                "subject": draft.get("subject"),
                "questions": draft.get("formal_questions"),
                "full_text": draft.get("full_application_text"),
                "filed_date": draft.get("filed_date"),
                "deadline_date": draft.get("deadline_date")
            },
            "filing": filing_result,
            "prediction": prediction
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RTI Filing failed: {str(e)}")


@app.get("/api/rti/{ref_number}")
def get_rti(ref_number: str, db: Session = Depends(get_db)):
    rti = db.query(RTIApplication).filter(RTIApplication.ref_number == ref_number).first()
    if not rti:
        raise HTTPException(status_code=404, detail="RTI not found")
    return {
        "success": True,
        "data": {
            "ref_number": rti.ref_number,
            "applicant_name": rti.applicant_name,
            "department": rti.department,
            "subject": rti.subject,
            "status": rti.status,
            "filed_date": rti.filed_date.isoformat() if rti.filed_date else None,
            "questions": json.loads(rti.questions) if rti.questions else [],
            "draft_text": rti.draft_text
        }
    }


@app.get("/api/rti/{ref_number}/pdf")
def download_pdf(ref_number: str, db: Session = Depends(get_db)):
    rti = db.query(RTIApplication).filter(RTIApplication.ref_number == ref_number).first()
    if not rti:
        raise HTTPException(status_code=404, detail="RTI not found")

    pdf_data = {
        "ref_number": rti.ref_number,
        "applicant_name": rti.applicant_name,
        "applicant_address": rti.applicant_address,
        "applicant_mobile": rti.applicant_mobile,
        "applicant_email": rti.applicant_email,
        "is_bpl": rti.is_bpl,
        "bpl_card_no": rti.bpl_card_no,
        "department": rti.department,
        "pio_name": rti.pio_name,
        "pio_address": "India",
        "subject": rti.subject,
        "questions": json.loads(rti.questions) if rti.questions else [],
        "filed_date": rti.filed_date.strftime("%d/%m/%Y") if rti.filed_date else "",
        "deadline_date": "",
        "draft_text": rti.draft_text
    }

    pdf_bytes = generate_rti_pdf(pdf_data)
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="RTI_{ref_number}.pdf"'}
    )


@app.get("/api/analytics")
def get_analytics(db: Session = Depends(get_db)):
    total = db.query(RTIApplication).count()
    filed = db.query(RTIApplication).filter(RTIApplication.status == "filed").count()
    return {
        "success": True,
        "data": {
            "total_rtis": total,
            "filed": filed,
            "response_rate": 72,
            "avg_response_days": 18,
            "states_covered": 28,
            "departments_mapped": 500,
            "citizens_helped": total,
            "corruption_prevented_cr": round(total * 0.05, 2)
        }
    }


@app.post("/api/check-appeal")
def check_appeal(req: CheckAppealRequest, db: Session = Depends(get_db)):
    rti = db.query(RTIApplication).filter(RTIApplication.ref_number == req.ref_number).first()
    if not rti:
        raise HTTPException(status_code=404, detail="RTI not found")

    rti_dict = {
        "ref_number": rti.ref_number,
        "status": rti.status,
        "filed_at": rti.filed_date.isoformat() if rti.filed_date else datetime.now().isoformat(),
        "department": rti.department,
        "subject": rti.subject,
        "applicant_name": rti.applicant_name,
        "appeal_filed": rti.appeal_filed
    }

    result = appeal_agent.check_and_appeal(rti_dict)
    return {"success": True, "data": result}


@app.get("/api/departments")
def get_departments():
    from pathlib import Path
    data_dir = Path(__file__).parent / "data"
    with open(data_dir / "pio_directory.json") as f:
        pios = json.load(f)
    return {"success": True, "data": pios}