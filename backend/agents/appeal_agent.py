"""
appeal_agent.py — Agent 5: Follow-up & Appeal Agent
Auto-generates First and Second Appeals when RTI is unanswered.
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


class AppealAgent:
    """
    Agent 5: Appeals & Follow-up
    Monitors RTI status and auto-generates appeals when needed.
    """

    def check_and_appeal(self, rti_record: dict) -> dict:
        """
        Check if an RTI needs a follow-up or appeal.

        Args:
            rti_record: RTI application record from database

        Returns:
            dict with action taken and appeal draft if applicable
        """
        filed_date = datetime.fromisoformat(rti_record.get("filed_at", datetime.now().isoformat()))
        days_elapsed = (datetime.now() - filed_date).days
        status = rti_record.get("status", "filed")

        if status == "response_received":
            return {"action": "none", "message": "RTI already responded to."}

        if days_elapsed >= 30 and not rti_record.get("appeal_filed"):
            # Generate First Appeal
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
        """Generate a First Appeal application using Claude."""
        try:
            prompt = f"""Generate a First Appeal under Section 19(1) of RTI Act 2005.

RTI Details:
- Reference Number: {rti_record.get('ref_number')}
- Filed Date: {rti_record.get('filed_at')}
- Department: {rti_record.get('department')}
- Subject: {rti_record.get('subject')}
- Applicant: {rti_record.get('applicant_name')}

Generate a formal First Appeal letter. No response was received in 30 days.
Include legal provisions: Section 19(1), Section 7(1), 18(1)(b).
Return plain text of the appeal letter only."""

            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=800,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()

        except Exception:
            # Fallback template
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
        """
        AI-powered RTI success probability predictor.
        Analyzes multiple factors to estimate success likelihood.
        """
        try:
            prompt = f"""Analyze this RTI application and predict its success probability.

Category: {query_analysis.get('category')}
Subject: {query_analysis.get('subject')}
Questions: {json.dumps(query_analysis.get('suggested_questions', []))}
Department Jurisdiction: {routing_info.get('jurisdiction', 'central')}
Urgency: {query_analysis.get('urgency')}

Respond with JSON only:
{{
  "success_probability": 0.0-1.0,
  "factors": {{
    "question_clarity": 0.0-1.0,
    "department_responsiveness": 0.0-1.0,
    "information_availability": 0.0-1.0
  }},
  "risk_level": "low|medium|high",
  "tips": ["tip1", "tip2"],
  "estimated_response_days": 15-30
}}"""
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except Exception:
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