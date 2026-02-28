"""
drafting_agent.py — Agent 3: RTI Drafting Agent
"""
import json
import os
import re
from datetime import datetime, timedelta
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


class DraftingAgent:
    def draft(self, query_analysis: dict, routing_info: dict, applicant: dict) -> dict:
        pio = routing_info.get("pio", {})
        today = datetime.now()
        deadline = today + timedelta(days=30)

        fee_clause = (
            "I am a BPL cardholder and am exempt from the application fee under Section 7(5) of the RTI Act, 2005."
            if applicant.get("is_bpl")
            else "I am enclosing the application fee of Rs. 10/- as required under the RTI Act, 2005."
        )

        prompt = (
            "You are a senior legal expert specializing in RTI Act 2005, India.\n"
            "Draft a complete, formal RTI application and return ONLY a valid JSON object.\n"
            "NO markdown, NO code fences, NO extra text.\n\n"
            "JSON fields:\n"
            "- subject: formal subject line under 100 chars, specific to the issue\n"
            "- formal_questions: array of exactly 5 RTI questions — each must be a complete formal "
            "legal sentence specific to the citizen's actual issue. Include dates, locations, "
            "document names. Never write generic questions.\n"
            "- full_application_text: complete RTI letter as plain text (see format below)\n"
            "- relevant_sections: array of applicable RTI/other Act sections\n"
            "- estimated_success_probability: float 0.0-1.0\n"
            "- tips: one specific actionable tip for this particular RTI\n\n"
            f"CITIZEN ISSUE: {query_analysis.get('original_question')}\n"
            f"SUBJECT: {query_analysis.get('subject')}\n"
            f"CATEGORY: {query_analysis.get('category')}\n"
            f"LOCATION: {query_analysis.get('extracted_info', {}).get('location', 'Not specified')}\n"
            f"TIME PERIOD: {query_analysis.get('extracted_info', {}).get('time_period', 'as mentioned')}\n"
            f"SPECIFIC ISSUE: {query_analysis.get('extracted_info', {}).get('specific_issue', '')}\n\n"
            f"DEPARTMENT: {pio.get('department')}\n"
            f"PIO NAME: {pio.get('pio_name')}\n"
            f"PIO ADDRESS: {pio.get('address')}\n\n"
            f"APPLICANT NAME: {applicant.get('name')}\n"
            f"APPLICANT ADDRESS: {applicant.get('address')}\n"
            f"MOBILE: {applicant.get('mobile')}\n"
            f"EMAIL: {applicant.get('email')}\n"
            f"DATE: {today.strftime('%d %B %Y')}\n"
            f"FEE CLAUSE: {fee_clause}\n\n"
            "full_application_text FORMAT (plain text, no JSON inside):\n"
            "To,\n"
            "The Public Information Officer,\n"
            "[Department Name],\n"
            "[Address]\n\n"
            "Subject: [specific subject]\n\n"
            "Sir/Madam,\n\n"
            "I, [Name], a citizen of India residing at [Address], hereby submit this application "
            "under Section 6(1) of the Right to Information Act, 2005 to seek the following "
            "information from your office:\n\n"
            "[Numbered questions — specific, formal, legal language]\n\n"
            "[Fee clause]\n\n"
            "I request that the above information be furnished within 30 days as mandated under "
            "Section 7(1) of the RTI Act, 2005. Should the information not pertain to your "
            "office, kindly transfer this application to the concerned authority under Section "
            "6(3) of the RTI Act, 2005.\n\n"
            "I hereby declare that I am a citizen of India.\n\n"
            "Yours faithfully,\n"
            "[Name]\n"
            "Date: [Date]\n"
            "Mobile: [Mobile]\n"
            "Email: [Email]"
        )

        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=2500
                )
            )
            raw = response.text
            print(f"[DraftingAgent] Raw response: {raw[:300]}...")
            cleaned = _clean_json(raw)
            result = json.loads(cleaned)
            result["filed_date"] = today.strftime("%d/%m/%Y")
            result["deadline_date"] = deadline.strftime("%d/%m/%Y")
            print(f"[DraftingAgent] Subject: {result.get('subject')}")
            return result

        except Exception as e:
            print(f"[DraftingAgent] Error: {e}, using fallback")
            return self._fallback_draft(query_analysis, routing_info, applicant, today, deadline)

    def _fallback_draft(self, qa, ri, applicant, today, deadline) -> dict:
        pio = ri.get("pio", {})
        questions = qa.get("suggested_questions", [])
        if not questions:
            questions = [qa.get("subject", "Please provide relevant information.")]
        q_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
        fee = (
            "I am a BPL cardholder and am exempt from fee under Section 7(5) of the RTI Act, 2005."
            if applicant.get("is_bpl")
            else "I am enclosing the application fee of Rs. 10/- as required."
        )
        full_text = (
            f"To,\n"
            f"The Public Information Officer,\n"
            f"{pio.get('department', 'Concerned Department')},\n"
            f"{pio.get('address', 'India')}\n\n"
            f"Subject: {qa.get('subject', 'Request for Information under RTI Act 2005')}\n\n"
            f"Sir/Madam,\n\n"
            f"I, {applicant.get('name')}, a citizen of India residing at "
            f"{applicant.get('address')}, hereby submit this application under Section 6(1) "
            f"of the Right to Information Act, 2005 to seek the following information:\n\n"
            f"{q_text}\n\n"
            f"{fee}\n\n"
            f"I request that the above information be furnished within 30 days as mandated "
            f"under Section 7(1) of the RTI Act, 2005. Should the information not pertain to "
            f"your office, kindly transfer this application to the concerned authority under "
            f"Section 6(3) of the RTI Act, 2005.\n\n"
            f"I hereby declare that I am a citizen of India.\n\n"
            f"Yours faithfully,\n"
            f"{applicant.get('name')}\n"
            f"Date: {today.strftime('%d %B %Y')}\n"
            f"Mobile: {applicant.get('mobile')}\n"
            f"Email: {applicant.get('email')}"
        )
        return {
            "subject": qa.get("subject", "Request for Information"),
            "formal_questions": questions,
            "full_application_text": full_text,
            "relevant_sections": ["Section 6(1) RTI Act 2005", "Section 7(1) RTI Act 2005"],
            "estimated_success_probability": 0.75,
            "tips": "Be specific about dates and locations in your query.",
            "filed_date": today.strftime("%d/%m/%Y"),
            "deadline_date": deadline.strftime("%d/%m/%Y")
        }        