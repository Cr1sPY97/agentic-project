import json
import re
from typing import Dict, Any
from app.schemas.analysis import AIAnalysisStructuredOutput
from app.core.logging import get_logger

logger = get_logger("app.ai.parser")


def extract_json_from_text(raw_text: str) -> str:
    """Strip markdown code fences and extraneous text surrounding the JSON object."""
    text = raw_text.strip()
    
    # Check for ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no fences, find outermost { and }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()

    return text


def parse_structured_ai_response(raw_text: str) -> AIAnalysisStructuredOutput:
    """
    Parse and strictly validate raw LLM text against the Pydantic schema.
    Raises ValueError with descriptive context if validation fails.
    """
    cleaned_json_str = extract_json_from_text(raw_text)
    try:
        data = json.loads(cleaned_json_str)
    except json.JSONDecodeError as exc:
        logger.error(f"JSON decode failed on AI response: {exc}. Cleaned string was: {cleaned_json_str[:200]}")
        raise ValueError(f"AI response is not valid JSON: {str(exc)}") from exc

    if not isinstance(data, dict):
        raise ValueError("AI response must be a JSON object, not a primitive or array.")

    # Normalize list fields if model returned string or None
    for list_field in [
        "evidence",
        "immediate_mitigation_steps",
        "recommended_remediation_steps",
        "prevention_recommendations",
    ]:
        val = data.get(list_field)
        if isinstance(val, str):
            data[list_field] = [val]
        elif val is None:
            data[list_field] = []

    # Ensure confidence score is within 0.0 - 1.0 bounds
    conf = data.get("confidence_score")
    if conf is not None:
        try:
            data["confidence_score"] = max(0.0, min(1.0, float(conf)))
        except (ValueError, TypeError):
            data["confidence_score"] = 0.50

    try:
        validated = AIAnalysisStructuredOutput.model_validate(data)
        return validated
    except Exception as exc:
        logger.error(f"Pydantic schema validation failed for AI output: {exc}")
        raise ValueError(f"AI response failed schema validation: {str(exc)}") from exc
