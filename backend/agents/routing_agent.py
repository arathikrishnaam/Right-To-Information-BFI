"""
routing_agent.py — Agent 2: Department Routing Agent
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

DATA_DIR = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "pio_directory.json") as f:
    PIO_DIRECTORY = json.load(f)
with open(DATA_DIR / "departments.json") as f:
    DEPARTMENTS = json.load(f)

STATE_SUBJECTS = {"food_ration", "electricity", "water", "housing", "road_infrastructure"}

STATE_ALIASES = {
    "kerala": "Kerala", "thiruvananthapuram": "Kerala", "trivandrum": "Kerala",
    "kochi": "Kerala", "ernakulam": "Kerala", "kozhikode": "Kerala",
    "calicut": "Kerala", "thrissur": "Kerala", "kollam": "Kerala",
    "malappuram": "Kerala", "palakkad": "Kerala", "kannur": "Kerala",
    "kasaragod": "Kerala", "alappuzha": "Kerala", "alleppey": "Kerala",
    "wayanad": "Kerala", "idukki": "Kerala", "kottayam": "Kerala",
    "pathanamthitta": "Kerala",
    "tamil nadu": "Tamil Nadu", "tamilnadu": "Tamil Nadu",
    "chennai": "Tamil Nadu", "madras": "Tamil Nadu", "coimbatore": "Tamil Nadu",
    "madurai": "Tamil Nadu", "trichy": "Tamil Nadu", "salem": "Tamil Nadu", "tn": "Tamil Nadu",
    "karnataka": "Karnataka", "bengaluru": "Karnataka", "bangalore": "Karnataka",
    "mysuru": "Karnataka", "mysore": "Karnataka", "hubli": "Karnataka",
    "mangalore": "Karnataka", "mangaluru": "Karnataka",
    "delhi": "Delhi", "new delhi": "Delhi",
    "maharashtra": "Maharashtra", "mumbai": "Maharashtra", "pune": "Maharashtra",
    "nagpur": "Maharashtra", "thane": "Maharashtra", "nashik": "Maharashtra",
    "uttar pradesh": "Uttar Pradesh", "up": "Uttar Pradesh",
    "lucknow": "Uttar Pradesh", "noida": "Uttar Pradesh", "agra": "Uttar Pradesh",
    "kanpur": "Uttar Pradesh", "varanasi": "Uttar Pradesh", "prayagraj": "Uttar Pradesh",
    "west bengal": "West Bengal", "wb": "West Bengal",
    "kolkata": "West Bengal", "calcutta": "West Bengal",
    "rajasthan": "Rajasthan", "jaipur": "Rajasthan", "jodhpur": "Rajasthan",
    "gujarat": "Gujarat", "ahmedabad": "Gujarat", "surat": "Gujarat",
    "vadodara": "Gujarat", "rajkot": "Gujarat",
    "andhra pradesh": "Andhra Pradesh", "telangana": "Telangana",
    "hyderabad": "Telangana", "madhya pradesh": "Madhya Pradesh",
    "bhopal": "Madhya Pradesh", "indore": "Madhya Pradesh",
    "bihar": "Bihar", "patna": "Bihar",
    "punjab": "Punjab", "chandigarh": "Punjab", "amritsar": "Punjab",
    "haryana": "Haryana", "gurugram": "Haryana", "faridabad": "Haryana",
    "assam": "Assam", "guwahati": "Assam",
    "odisha": "Odisha", "bhubaneswar": "Odisha",
    "jharkhand": "Jharkhand", "ranchi": "Jharkhand",
    "uttarakhand": "Uttarakhand", "dehradun": "Uttarakhand",
    "goa": "Goa", "chhattisgarh": "Chhattisgarh", "raipur": "Chhattisgarh",
}


def _normalize_state(raw: str) -> str:
    if not raw:
        return "Delhi"
    key = raw.strip().lower()
    if key in STATE_ALIASES:
        normalized = STATE_ALIASES[key]
        print(f"[RoutingAgent] Alias: '{raw}' → '{normalized}'")
        return normalized
    title = raw.strip().title()
    if title in PIO_DIRECTORY.get("state", {}):
        return title
    for k in PIO_DIRECTORY.get("state", {}).keys():
        if k.lower() == key:
            return k
    print(f"[RoutingAgent] Unknown state '{raw}'")
    return title


class RoutingAgent:
    def route(self, query_analysis: dict, user_state: str = "Delhi") -> dict:
        category = query_analysis.get("category", "other")
        state = _normalize_state(user_state)

        # Backup: extract state from question text if state PIOs not found
        if state not in PIO_DIRECTORY.get("state", {}):
            extracted = self._extract_state_from_question(
                query_analysis.get("original_question", ""),
                query_analysis.get("extracted_info", {}).get("location", "")
            )
            if extracted:
                state = extracted

        print(f"[RoutingAgent] category={category} | state={state}")
        pio = self._find_pio(category, state)
        print(f"[RoutingAgent] → {pio.get('department')} ({pio.get('id')})")

        return {
            "pio": pio,
            "department": pio.get("department"),
            "filing_url": pio.get("portal", "https://rtionline.gov.in"),
            "category": category,
            "jurisdiction": "central" if pio.get("id", "").startswith("C") else "state",
            "filing_fee": 0 if query_analysis.get("is_bpl") else
                          DEPARTMENTS.get("filing_fee", {}).get("general", 10)
        }

    def _extract_state_from_question(self, question: str, location: str) -> str:
        combined = f"{question} {location}".lower()
        for alias, state in STATE_ALIASES.items():
            if alias in combined:
                print(f"[RoutingAgent] Found '{alias}' in question → '{state}'")
                return state
        return ""

    def _find_pio(self, category: str, state: str) -> dict:
        dept_info = DEPARTMENTS["categories"].get(category, {})
        keywords = [k.lower() for k in dept_info.get("keywords", [])]
        central_id = dept_info.get("central_pio_id")

        if category in STATE_SUBJECTS:
            state_pios = PIO_DIRECTORY.get("state", {}).get(state, [])
            print(f"[RoutingAgent] State PIOs for '{state}': {len(state_pios)}")
            if state_pios:
                for pio in state_pios:
                    cats = " ".join(c.lower() for c in pio.get("categories", []))
                    if any(kw in cats for kw in keywords) or category in cats:
                        return pio
                return state_pios[0]

        if central_id:
            for pio in PIO_DIRECTORY.get("central", []):
                if pio["id"] == central_id:
                    return pio

        for pio in PIO_DIRECTORY.get("central", []):
            cats = " ".join(c.lower() for c in pio.get("categories", []))
            if any(kw in cats for kw in keywords):
                return pio

        fallback_map = {
            "food_ration": "C009", "health": "C002", "education": "C003",
            "road_infrastructure": "C004", "postal": "C005", "income_tax": "C006",
            "employment": "C007", "lpg_petroleum": "C008", "housing": "C010",
            "railways": "C001",
        }
        fallback_id = fallback_map.get(category, "C009")
        for pio in PIO_DIRECTORY.get("central", []):
            if pio["id"] == fallback_id:
                return pio

        return PIO_DIRECTORY["central"][0]      