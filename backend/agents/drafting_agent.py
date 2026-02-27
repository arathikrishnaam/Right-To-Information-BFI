"""
drafting_agent.py — Agent 3: RTI Drafting Agent
Generates a legally compliant RTI application in proper format.
"""
import json
import os
from datetime import datetime, timedelta
import anthropic
from pathlib import Path

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DATA_DIR = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "rti_templates.json") as f:
    TEMPLATES = json.load(f)


class DraftingAgent:
    """
    Agent 3: RTI Application Drafting
    Input:  Query analysis + Routing info + Applicant details
    Output: Complete, legally valid RTI application text + formal questions
    """

    SYSTEM_PROMPT = """You are a legal expert specializing in drafting Right to Information (RTI)
applications under the RTI Act 2005, India.

Your task is to generate a complete, formal RTI application.

RULES:
1. Use formal, legal language throughout.
2. Questions must be specific, clear, and answerable — avoid vague questions.
3. Include all mandatory sections as per RTI Act 2005.
4. Respond ONLY with valid JSON, no extra text.
5. Questions should not ask for opinions, only facts and documents.

OUTPUT FORMAT:
{
  "subject": "Concise subject line (max 100 chars)",
  "formal_questions": [
    "Specific Question 1 in proper RTI legal language",
    "Specific Question 2",
    "Specific Question 3",
    "Specific Question 4",
    "Specific Question 5"
  ],
  "full_application_text": "Complete RTI application as plain text with all sections",
  "relevant_sections": ["RTI Act Section X", "..."],
  "estimated_success_probability": 0.85,
  "tips": "One tip to increase success rate"
}"""

    def draft(self, query_analysis: dict, routing_info: dict, applicant: dict) -> dict:
        """
        Draft a complete RTI application.

        Args:
            query_analysis: Output from QueryAgent
            routing_info: Output from RoutingAgent
            applicant: {name, address, mobile, email, is_bpl, bpl_card_no}

        Returns:
            dict with full RTI draft
        """
        pio = routing_info.get("pio", {})
        today = datetime.now()
        deadline = today + timedelta(days=30)

        prompt = f"""Draft an RTI application with these details:

CITIZEN'S ORIGINAL QUESTION: {query_analysis.get('original_question')}
SUBJECT: {query_analysis.get('subject')}
CATEGORY: {query_analysis.get('category')}
EXTRACTED INFO: {json.dumps(query_analysis.get('extracted_info', {}), indent=2)}
SUGGESTED QUESTIONS: {json.dumps(query_analysis.get('suggested_questions', []), indent=2)}

DEPARTMENT: {pio.get('department')}
PIO NAME: {pio.get('pio_name')}
PIO ADDRESS: {pio.get('address')}

APPLICANT:
- Name: {applicant.get('name')}
- Address: {applicant.get('address')}
- Mobile: {applicant.get('mobile')}
- Email: {applicant.get('email')}
- BPL Status: {applicant.get('is_bpl', False)}
- Date: {today.strftime('%d %B %Y')}

Generate a complete formal RTI application. The full_application_text must include:
1. Addressee (To: The PIO, Department)
2. Subject line
3. Introduction paragraph with applicant identity
4. Fee clause (BPL exempt or Rs.10 paid)
5. Numbered list of specific questions
6. Request for 30-day response citing Section 7(1)
7. Transfer clause citing Section 6(3)
8. Declaration of citizenship
9. Signature block"""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=2000,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )

            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            result = json.loads(raw)
            result["filed_date"] = today.strftime("%d/%m/%Y")
            result["deadline_date"] = deadline.strftime("%d/%m/%Y")
            return result

        except Exception as e:
            # Fallback: use template
            return self._fallback_draft(query_analysis, routing_info, applicant, today, deadline)

    def _fallback_draft(self, qa, ri, applicant, today, deadline) -> dict:
        """Template-based fallback if Claude fails."""
        pio = ri.get("pio", {})
        questions = qa.get("suggested_questions", [qa.get("subject", "Please provide relevant information.")])
        q_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])

        full_text = f"""To,
The Public Information Officer,
{pio.get('department', 'Concerned Department')},
{pio.get('address', 'India')}

Subject: {qa.get('subject', 'Request for Information under RTI Act 2005')}

Sir/Madam,

I, {applicant.get('name')}, resident of {applicant.get('address')}, hereby request the following information under Section 6(1) of the Right to Information Act, 2005:

{q_text}

{"I am a BPL cardholder and am exempt from fee under Section 7(5) of the RTI Act, 2005." if applicant.get('is_bpl') else "I am enclosing the application fee of Rs. 10/- as required."}

I request that the above information be provided within 30 days as per Section 7(1) of the RTI Act, 2005. If the information is not available with your office, please transfer this application under Section 6(3) of the RTI Act, 2005.

I hereby declare that I am a citizen of India.

Yours faithfully,
{applicant.get('name')}
Date: {today.strftime('%d %B %Y')}
Mobile: {applicant.get('mobile')}
Email: {applicant.get('email')}"""

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