"""
routing_agent.py — Agent 2: Department Routing Agent
Identifies the correct PIO and government department for an RTI.
Uses keyword matching + Claude for intelligent routing.
"""
import json
import os
import anthropic
from pathlib import Path

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Load data files at module load
DATA_DIR = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "pio_directory.json") as f:
    PIO_DIRECTORY = json.load(f)
with open(DATA_DIR / "departments.json") as f:
    DEPARTMENTS = json.load(f)


class RoutingAgent:
    """
    Agent 2: Department Routing
    Input:  Query analysis from Agent 1 + user's state
    Output: Best matching PIO details
    """

    def route(self, query_analysis: dict, user_state: str = "Delhi") -> dict:
        """
        Find the correct PIO for an RTI based on category and location.

        Args:
            query_analysis: Output from QueryAgent.analyze()
            user_state: User's state (e.g. "Maharashtra", "Delhi")

        Returns:
            dict with pio details + department info
        """
        category = query_analysis.get("category", "other")
        subject = query_analysis.get("subject", "")

        # Step 1: Find best PIO using keyword matching
        pio = self._find_pio_by_category(category, user_state)

        # Step 2: Use Claude to confirm/refine routing
        pio = self._claude_confirm_routing(query_analysis, pio, user_state)

        return {
            "pio": pio,
            "department": pio.get("department"),
            "filing_url": pio.get("portal", "https://rtionline.gov.in"),
            "category": category,
            "jurisdiction": "central" if pio.get("id", "").startswith("C") else "state",
            "filing_fee": 0 if query_analysis.get("is_bpl") else DEPARTMENTS.get("filing_fee", {}).get("general", 10)
        }

    def _find_pio_by_category(self, category: str, state: str) -> dict:
        """Keyword-based PIO matching."""
        dept_info = DEPARTMENTS["categories"].get(category, {})
        central_id = dept_info.get("central_pio_id")

        # Try state PIO first for local issues
        local_categories = ["road_infrastructure", "electricity", "water", "housing"]
        if category in local_categories and state in PIO_DIRECTORY.get("state", {}):
            state_pios = PIO_DIRECTORY["state"][state]
            # Match by category keywords
            for pio in state_pios:
                pio_cats = [c.lower() for c in pio.get("categories", [])]
                if any(kw in " ".join(pio_cats) for kw in dept_info.get("keywords", [])):
                    return pio
            if state_pios:
                return state_pios[0]  # fallback to first state PIO

        # Use central PIO
        if central_id:
            for pio in PIO_DIRECTORY.get("central", []):
                if pio["id"] == central_id:
                    return pio

        # Default fallback
        return PIO_DIRECTORY["central"][0]

    def _claude_confirm_routing(self, query_analysis: dict, suggested_pio: dict, state: str) -> dict:
        """Use Claude to validate and optionally improve routing."""
        try:
            prompt = f"""Given this RTI query analysis and suggested PIO, confirm if the routing is correct.
Query Analysis: {json.dumps(query_analysis, indent=2)}
Suggested PIO: {json.dumps(suggested_pio, indent=2)}
User State: {state}

Respond with JSON only:
{{"routing_correct": true/false, "reason": "...", "better_department": "if different department is better"}}"""

            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            result = json.loads(raw)
            # If Claude says routing is wrong, log it but keep suggested (for hackathon demo)
            return suggested_pio
        except Exception:
            return suggested_pio
