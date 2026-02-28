"""
query_agent.py — Agent 1: Query Understanding Agent
"""
import json
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "models/gemini-2.0-flash-lite-lite"


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _fallback_response(citizen_question: str, error: str = "") -> dict:
    print(f"[QueryAgent] Using fallback. Reason: {error}")
    return {
        "original_question": citizen_question,
        "detected_language": "english",
        "subject": "Request for Government Information",
        "category": "other",
        "extracted_info": {
            "what_is_needed": citizen_question,
            "time_period": "last 3 years",
            "location": "Not specified",
            "specific_issue": citizen_question
        },
        "suggested_questions": [
            f"Please provide complete information regarding: {citizen_question}",
            "Please provide the names and designations of officials responsible for the matter.",
            "Please provide copies of relevant documents, orders, and correspondence related to the matter."
        ],
        "urgency": "medium",
        "is_valid_rti": True,
        "error": error
    }


SYSTEM_PROMPT = """You are an expert RTI (Right to Information) assistant in India.
Analyze the citizen's question and return ONLY a valid JSON object.
NO markdown, NO code fences, NO extra text before or after.

JSON fields required:
- original_question: string (exact citizen input)
- detected_language: hindi|english|mixed|other
- translated_question: English translation if not English, else same as original
- subject: concise formal one-line subject for the RTI application (e.g. "Status of Ration Card Application - June 2024, Thiruvananthapuram")
- category: exactly one of [road_infrastructure, food_ration, electricity, water, education, health, employment, housing, railways, income_tax, lpg_petroleum, postal, other]
- extracted_info: object with:
    - what_is_needed: specific information being sought
    - time_period: time period mentioned or "last 3 years"
    - location: specific city/district/state mentioned
    - specific_issue: the core problem in one sentence
- suggested_questions: array of exactly 5 specific formal RTI questions written as complete sentences in legal language, directly about the citizen's actual issue — NOT generic placeholders
- urgency: low|medium|high
- is_valid_rti: true|false
- invalid_reason: empty string if valid

CATEGORY RULES:
- ration card, PDS, food grain, BPL card → food_ration
- road, pothole, bridge, highway → road_infrastructure
- electricity, meter, power bill → electricity
- water, pipeline, tanker → water
- train, railway, IRCTC → railways

QUESTION RULES:
- Questions must be specific to the citizen's actual complaint
- Include dates, locations, and document names where relevant
- Use formal RTI legal language
- Example for ration card: "Please provide the current status of ration card application submitted in June 2024 at [location], along with the application reference number."
- Never write generic questions like "Please provide complete information regarding: [original question]"
"""


class QueryAgent:
    def analyze(self, citizen_question: str) -> dict:
        try:
            prompt = f"{SYSTEM_PROMPT}\n\nCitizen question: {citizen_question}"
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1500
                )
            )
            raw = response.text
            print(f"[QueryAgent] Raw response: {raw[:300]}...")
            cleaned = _clean_json(raw)
            result = json.loads(cleaned)
            print(f"[QueryAgent] category={result.get('category')} | subject={result.get('subject')}")
            return result

        except json.JSONDecodeError as e:
            print(f"[QueryAgent] JSON error: {e} | raw was: {raw[:400]}")
            return _fallback_response(citizen_question, f"JSON parse error: {e}")
        except Exception as e:
            print(f"[QueryAgent] Error: {e}")
            return _fallback_response(citizen_question, str(e))            