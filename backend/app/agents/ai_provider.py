from abc import ABC, abstractmethod
from typing import Dict, Any

class AIProvider(ABC):
    @abstractmethod
    def analyze_severity(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def analyze_root_cause(self, incident_data: Dict[str, Any], historical_data: list) -> Dict[str, Any]:
        pass

    @abstractmethod
    def correlate_incidents(self, incident_data: Dict[str, Any], previous_incidents: list) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def generate_remediation(self, incident_data: Dict[str, Any], root_cause_data: Dict[str, Any]) -> list:
        pass

class MockAIProvider(AIProvider):
    def analyze_severity(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "severity": "HIGH",
            "confidence": 0.91,
            "reason": "Database timeout affecting payment processing (Mocked)"
        }

    def analyze_root_cause(self, incident_data: Dict[str, Any], historical_data: list) -> Dict[str, Any]:
        return {
            "root_cause": "Database connection pool exhaustion",
            "confidence": 0.87,
            "reasoning": "Repeated connection timeout errors combined with high response latency (Mocked)"
        }

    def correlate_incidents(self, incident_data: Dict[str, Any], previous_incidents: list) -> Dict[str, Any]:
        return {
            "related": len(previous_incidents) > 0,
            "confidence": 0.82 if previous_incidents else 0.0,
            "reasoning": "Found similar incidents in the past 24 hours (Mocked)" if previous_incidents else "No related incidents found"
        }
    
    def generate_remediation(self, incident_data: Dict[str, Any], root_cause_data: Dict[str, Any]) -> list:
        return [
            {
                "action": "Check PostgreSQL connection pool usage",
                "priority": 1,
                "reasoning": "Root cause points to pool exhaustion",
                "approved": 0,
                "executed": 0
            },
            {
                "action": "Increase connection pool only after verifying connection leaks",
                "priority": 2,
                "reasoning": "Standard remediation for pool exhaustion",
                "approved": 0,
                "executed": 0
            }
        ]

# Default to MockAIProvider for now
def get_ai_provider() -> AIProvider:
    return MockAIProvider()
