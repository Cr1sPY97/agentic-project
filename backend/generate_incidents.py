import requests
import random
import time
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000/api/v1"

INCIDENT_TYPES = [
    ("payment-service", "database timeout", "DatabaseTimeout", "PostgreSQL connection timeout on payment insert"),
    ("payment-service", "payment failure", "PaymentGatewayError", "Stripe API returned 502 Bad Gateway"),
    ("auth-service", "authentication failure", "AuthFailure", "Redis cache miss causing spike in DB auth queries"),
    ("api-gateway", "API timeout", "GatewayTimeout", "Upstream service taking too long to respond"),
    ("user-service", "high latency", "HighLatency", "Response time exceeded 5 seconds on /api/users"),
    ("search-service", "service unavailable", "ServiceUnavailable", "Elasticsearch cluster is red"),
    ("background-worker", "memory exhaustion", "OOMKilled", "Worker process exceeded 2GB memory limit"),
    ("api-gateway", "rate limiting", "RateLimitExceeded", "Client exceeded 1000 req/s limit")
]

ENVIRONMENTS = ["production", "staging"]

def generate_incident():
    service, error_desc, error_type, message = random.choice(INCIDENT_TYPES)
    
    payload = {
        "service": service,
        "environment": random.choice(ENVIRONMENTS),
        "error_type": error_type,
        "message": message,
        "endpoint": f"/api/{service.split('-')[0]}s",
        "response_time": round(random.uniform(0.1, 10.5), 2),
        "metadata": {
            "region": random.choice(["us-east-1", "eu-west-1", "ap-south-1"]),
            "cpu_usage": round(random.uniform(40, 99), 1)
        }
    }
    
    try:
        # Assuming you have a user or bypass auth for local generation
        # If auth is required, you need to login and pass the token
        response = requests.post(f"{BASE_URL}/incidents/", json=payload)
        print(f"Generated incident: {response.status_code}")
    except Exception as e:
        print(f"Failed to generate incident: {e}")

if __name__ == "__main__":
    print("Generating sample incidents...")
    for _ in range(10):
        generate_incident()
        time.sleep(1)
