"""
filing_agent.py — Agent 4: Filing & Tracking Agent
Simulates RTI portal submission and manages tracking.
In production: integrate with rtionline.gov.in API / Selenium automation.
"""
import random
import string
from datetime import datetime, timedelta


class FilingAgent:
    """
    Agent 4: Filing & Tracking
    Input:  Complete RTI draft + routing info
    Output: Reference number, acknowledgment, tracking status
    """

    def file(self, draft: dict, routing_info: dict, ref_number: str) -> dict:
        """
        Simulate filing the RTI on government portal.

        In a real implementation this would:
        1. Navigate to rtionline.gov.in or state portal
        2. Fill the form using Selenium/Playwright
        3. Upload the generated PDF
        4. Pay fee online
        5. Capture acknowledgment number

        For the hackathon demo, we simulate this process.
        """
        portal = routing_info.get("filing_url", "https://rtionline.gov.in")
        dept = routing_info.get("department", "Government Department")

        # Simulate acknowledgment number (real: capture from portal response)
        ack_no = self._generate_ack_number()
        filing_date = datetime.now()
        deadline = filing_date + timedelta(days=30)

        return {
            "ref_number": ref_number,
            "acknowledgment_number": ack_no,
            "portal": portal,
            "department": dept,
            "status": "filed",
            "filed_at": filing_date.isoformat(),
            "deadline": deadline.isoformat(),
            "deadline_formatted": deadline.strftime("%d %B %Y"),
            "tracking_url": f"{portal}/track/{ack_no}",
            "reminders_set": True,
            "next_action": f"Check status on Day 25 ({(filing_date + timedelta(days=25)).strftime('%d %B %Y')})",
            "message": f"RTI successfully filed! Your reference number is {ref_number}. You should receive a response by {deadline.strftime('%d %B %Y')}."
        }

    def check_status(self, ref_number: str) -> dict:
        """
        Check the status of a filed RTI.
        In production: poll the government portal API.
        For demo: return simulated status.
        """
        # Simulate different statuses for demo
        statuses = [
            {"status": "filed", "message": "RTI filed and dispatched to PIO", "progress": 20},
            {"status": "acknowledged", "message": "Acknowledged by PIO office", "progress": 40},
            {"status": "under_process", "message": "Being processed by the department", "progress": 60},
            {"status": "response_ready", "message": "Response being prepared", "progress": 80},
        ]
        return random.choice(statuses)

    def _generate_ack_number(self) -> str:
        """Generate a realistic acknowledgment number."""
        year = datetime.now().year
        num = ''.join(random.choices(string.digits, k=8))
        return f"DOPT{year}{num}"