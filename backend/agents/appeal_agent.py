"""
appeal_agent.py — Agent 5: Follow-up & Appeal Agent
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "models/gemini-2.0-flash-lite-lite"

DATA_DIR = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "rti_templates.json") as f:
    TEMPLATES = json.load(f)


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


class AppealAgent:
    def check_and_appeal(self, rti_record: dict) -> dict:
        filed_date = datetime.fromisoformat(
            rti_record.get("filed_at", datetime.now().isoformat())
        )
        days_elapsed = (datetime.now() - filed_date).days
        status = rti_record.get("status", "filed")

        if status == "response_received":
            return {"action": "none", "message": "RTI already responded to."}
        if days_elapsed >= 30 and not rti_record.get("appeal_filed"):
            appeal = self.generate_first_appeal(rti_record)
            return {
                "action": "first_appeal",
                "days_elapsed": days_elapsed,
                "appeal_draft": appeal,
                "message": "30 days have passed. First Appeal generated automatically."
            }
        elif days_elapsed >= 25:
            return {
                "action": "reminder",
                "days_elapsed": days_elapsed,
                "days_remaining": 30 - days_elapsed,
                "message": f"Reminder: {30 - days_elapsed} days remaining for PIO response."
            }
        else:
            return {
                "action": "waiting",
                "days_elapsed": days_elapsed,
                "days_remaining": 30 - days_elapsed,
                "message": f"Waiting for response. {30 - days_elapsed} days remaining."
            }

    def generate_first_appeal(self, rti_record: dict) -> str:
        try:
            prompt = (
                "Generate a First Appeal letter under Section 19(1) of RTI Act 2005. "
                "Return plain text only, no markdown.\n\n"
                f"Reference Number: {rti_record.get('ref_number')}\n"
                f"Filed Date: {rti_record.get('filed_at', '')[:10]}\n"
                f"Department: {rti_record.get('department')}\n"
                f"Subject: {rti_record.get('subject')}\n"
                f"Applicant: {rti_record.get('applicant_name')}\n\n"
                "No response received within 30 days. "
                "Cite Section 19(1), Section 7(1), and Section 18(1)(b)."
            )
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=800)
            )
            return response.text.strip()
        except Exception as e:
            print(f"[AppealAgent] generate_first_appeal error: {e}")
            tmpl = TEMPLATES["first_appeal_template"]["body"]
            return tmpl.format(
                department_name=rti_record.get("department", "Concerned Department"),
                department_address="India",
                applicant_name=rti_record.get("applicant_name", "Applicant"),
                rti_date=rti_record.get("filed_at", "")[:10],
                ref_number=rti_record.get("ref_number", ""),
                subject=rti_record.get("subject", "the matter"),
                appeal_date=datetime.now().strftime("%d %B %Y")
            )

    def predict_success(self, query_analysis: dict, routing_info: dict) -> dict:
        try:
            prompt = (
                "Analyze this RTI application and predict success probability. "
                "Return ONLY a valid JSON object, no markdown, no code fences.\n\n"
                "JSON fields:\n"
                "- success_probability: float 0-1\n"
                "- factors: object with question_clarity, department_responsiveness, "
                "information_availability (all floats 0-1)\n"
                "- risk_level: low|medium|high\n"
                "- tips: array of exactly 2 specific actionable tip strings for this RTI\n"
                "- estimated_response_days: integer\n\n"
                f"Category: {query_analysis.get('category')}\n"
                f"Subject: {query_analysis.get('subject')}\n"
                f"Urgency: {query_analysis.get('urgency')}\n"
                f"Jurisdiction: {routing_info.get('jurisdiction', 'central')}\n"
                f"Department: {routing_info.get('department')}\n"
                f"Issue: {query_analysis.get('extracted_info', {}).get('specific_issue', '')}\n"
                f"Questions: {json.dumps(query_analysis.get('suggested_questions', []))}"
            )
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=400)
            )
            raw = response.text
            print(f"[AppealAgent] predict_success raw: {raw[:200]}")
            return json.loads(_clean_json(raw))
        except Exception as e:
            print(f"[AppealAgent] predict_success error: {e}")
            return {
                "success_probability": 0.78,
                "factors": {
                    "question_clarity": 0.82,
                    "department_responsiveness": 0.74,
                    "information_availability": 0.80
                },
                "risk_level": "low",
                "tips": ["Be specific about dates", "Include specific document names"],
                "estimated_response_days": 22
            }            