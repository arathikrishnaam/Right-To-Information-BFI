"""
query_agent.py — Agent 1: Query Understanding Agent
Converts a citizen's plain-language question into structured data.
Supports Hindi and English via Claude Sonnet.
"""
import json
import os
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


class QueryAgent:
    """
    Agent 1: Query Understanding
    Input:  Raw citizen question (any Indian language / English)
    Output: Structured JSON with extracted intent, category, location, time_period
    """

    SYSTEM_PROMPT = """You are an expert RTI (Right to Information) assistant in India.
Your job is to analyze a citizen's question and extract structured information for filing an RTI.

IMPORTANT RULES:
1. Respond ONLY with valid JSON, no extra text.
2. If the question is in Hindi or other Indian languages, understand it and respond in English JSON.
3. Extract the core information need, not the emotion or frustration.
4. Identify the government department likely responsible.
5. Suggest 3-5 specific, legally appropriate RTI questions.

OUTPUT FORMAT (strict JSON):
{
  "original_question": "...",
  "detected_language": "hindi|english|mixed|other",
  "translated_question": "English translation if not English",
  "subject": "One-line subject for RTI application",
  "category": "road_infrastructure|food_ration|electricity|water|education|health|employment|housing|railways|income_tax|lpg_petroleum|postal|other",
  "extracted_info": {
    "what_is_needed": "specific info being sought",
    "time_period": "time period if mentioned, else 'last 3 years'",
    "location": "specific location if mentioned",
    "specific_issue": "the specific problem or question"
  },
  "suggested_questions": [
    "Question 1 in formal RTI language",
    "Question 2 in formal RTI language",
    "Question 3 in formal RTI language"
  ],
  "urgency": "low|medium|high",
  "is_valid_rti": true,
  "invalid_reason": "if not valid, explain why"
}"""

    def analyze(self, citizen_question: str) -> dict:
        """
        Analyze citizen's question and extract structured RTI information.

        Args:
            citizen_question: Raw question from citizen (Hindi/English)

        Returns:
            dict with extracted information
        """
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=1000,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": f"Citizen's question: {citizen_question}"
                    }
                ]
            )

            raw = response.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            return json.loads(raw)

        except json.JSONDecodeError as e:
            return {
                "original_question": citizen_question,
                "detected_language": "unknown",
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
                "error": str(e)
            }
        except Exception as e:
            raise RuntimeError(f"Query Agent failed: {str(e)}")
