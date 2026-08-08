import requests
import json

BASE_URL = "https://interview-agent-uomx.onrender.com/api/interview"

# Simulated answers - short/closed so it moves through topics fast
answers = [
    "It's optimized for similarity search using embeddings, so it finds semantically similar items fast without scanning every row.",
    "I added a max iteration count as a safeguard, so if it hit 5 rounds without resolving, it would escalate to a human.",
    "I stored it in a shared session table so any agent could look up where the conversation left off.",
    "I used Docker Compose to containerize each service and Kubernetes to manage scaling.",
    "I set up health check endpoints and used liveness probes to restart failed containers automatically.",
    "I used structured logging with correlation IDs so I could trace a request across services.",
    "I validated all inputs with Pydantic models before they hit the LLM to prevent injection issues.",
    "The main trade-off was latency versus accuracy when choosing chunk size for retrieval.",
]

session_id = "test-emily-1"

# Start the interview
candidate = {
    "sessionId": session_id,
    "candidate": {
        "member": {
            "id": "CAND-003", "name": "Emily Chen", "jobRole": "AI Engineer",
            "yearsExperience": 6, "education": "MS Artificial Intelligence", "status": "COMPLETED"
        },
        "missions": [
            { "day": 7, "title": "Embeddings Explained", "passed": True, "attempts": 1 },
            { "day": 11, "title": "RAG End-to-End & LLM API Basics", "passed": True, "attempts": 1 },
            { "day": 13, "title": "Function Calling & Structured Outputs", "passed": True, "attempts": 1 },
            { "day": 22, "title": "Multi-Agent Orchestration", "passed": True, "attempts": 1 },
            { "day": 23, "title": "Model Context Protocol (MCP)", "passed": True, "attempts": 1 },
        ],
        "signals": { "commitDays": 31, "missionsCompleted": 31, "missionsFirstTry": 30 }
    }
}

print("=== START ===")
r = requests.post(BASE_URL, json=candidate).json()
print(json.dumps(r, indent=2))

for i, answer in enumerate(answers):
    if r.get("done"):
        break
    print(f"\n=== TURN {i+1} ===")
    r = requests.post(BASE_URL, json={"sessionId": session_id, "message": answer}).json()
    print(json.dumps(r, indent=2))

print("\n=== FINAL STATE ===")
print("Done:", r.get("done"))
if r.get("done"):
    print("Feedback keys present:", list(r.get("feedback", {}).keys()))