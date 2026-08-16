import json
from typing import Dict, Any

INCIDENT_ANALYSIS_SYSTEM_PROMPT_V1 = """
You are a Principal Site Reliability Engineer (SRE) and Incident Commander with 15+ years of experience triaging distributed cloud-native architectures.

Your task is to analyze the provided incident report, diagnose the root cause, assess severity and user impact, extract concrete evidence, and prescribe actionable immediate mitigation and long-term remediation procedures.

### STRICT OPERATIONAL GUIDELINES:
1. Grounding & Zero Hallucination: Base all findings ONLY on the provided service metadata, error message, stack trace, logs, and context. Do NOT invent missing metrics, endpoints, or root causes.
2. Epistemic Humility & Confidence:
   - Differentiate explicitly between (A) directly observed facts, (B) strongly supported technical inferences, and (C) uncertain hypotheses.
   - If the provided telemetry is insufficient to pinpoint an exact root cause, state this clearly in probable_root_cause and set confidence_score accordingly (< 0.65).
3. Severity Assessment: Evaluate against LOW, MEDIUM, HIGH, or CRITICAL based on business impact, blast radius, error rate, and data integrity risk.
4. Structured Output Format: Return a single strictly valid JSON object conforming to the schema below. Do NOT wrap output in markdown code fences or explanatory prose.

### REQUIRED JSON SCHEMA:
{
  "classification": "string (e.g. 'Database Connection Exhaustion', 'Authentication Latency Spike', 'Memory Leak', 'Null Pointer Dereference')",
  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "probable_root_cause": "string (technical explanation citing specific code frames, resource bottlenecks, or timeout chains)",
  "confidence_score": 0.0 to 1.0,
  "impact_assessment": "string (impact on latency, error budget, affected users, and upstream/downstream dependencies)",
  "evidence": ["list of strings containing exact lines or observations extracted from logs/stack traces"],
  "immediate_mitigation_steps": ["list of fast tactical actions to restore service immediately"],
  "recommended_remediation_steps": ["list of permanent code, architecture, or config fixes"],
  "prevention_recommendations": ["list of monitoring, alerting, circuit breaker, or load test enhancements"],
  "human_readable_summary": "string (clear 2-4 sentence executive summary suitable for SRE on-call handover)"
}
"""

PROMPT_REGISTRY = {
    "incident_analysis_v1": INCIDENT_ANALYSIS_SYSTEM_PROMPT_V1
}


def get_prompt(version: str = "incident_analysis_v1") -> str:
    return PROMPT_REGISTRY.get(version, INCIDENT_ANALYSIS_SYSTEM_PROMPT_V1)


def build_incident_user_prompt(incident_payload: Dict[str, Any], custom_context: str = "") -> str:
    context_part = f"\nAdditional Context / Runbook Notes:\n{custom_context}\n" if custom_context else ""
    return f"""
Analyze the following production incident:

---
Incident Details:
- Title: {incident_payload.get('title')}
- Service: {incident_payload.get('service_name')}
- Environment: {incident_payload.get('environment')}
- Initial Rule Severity: {incident_payload.get('severity')}
- Error Rate / Frequency: {incident_payload.get('error_frequency')} RPM
- Estimated Affected Users: {incident_payload.get('affected_users')}
- Affected Endpoint: {incident_payload.get('affected_endpoint') or 'N/A'}
- Deployment / Version: {incident_payload.get('deployment_version') or 'N/A'}

Error Message:
{incident_payload.get('error_message')}

Stack Trace:
{incident_payload.get('stack_trace') or 'No stack trace provided'}

Logs:
{incident_payload.get('logs') or 'No supplementary logs provided'}

Request Metadata:
{json.dumps(incident_payload.get('request_metadata') or {}, indent=2)}
{context_part}
---

Produce the structured JSON analysis according to the system instructions.
"""
