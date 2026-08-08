from flask import Flask, request, jsonify
import json, os, random
from dotenv import load_dotenv
import requests
from flask import render_template

load_dotenv()
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = [
    "google/gemma-4-26b-a4b-it:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "openai/gpt-oss-20b:free",
]

def call_llm(messages, temperature=0.7, max_tokens=400):
    last_error = None
    for model in MODELS:
        try:
            resp = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "messages": messages,
                      "temperature": temperature, "max_tokens": max_tokens},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            last_error = e
            continue
    raise RuntimeError(f"All models failed: {last_error}")

# ---- Load curriculum once at startup ----
with open("data/curriculum.json") as f:
    CURRICULUM = json.load(f)

DAY_LOOKUP = {d["day"]: d for d in CURRICULUM["days"]}

MIN_QUESTIONS = 8
MIN_DAYS = 4
MAX_QUESTIONS = 12

SESSIONS = {}

def score_mission(m):
    """Higher score = more worth probing in the interview."""
    if m.get("skipped"):
        return 3
    attempts = m.get("attempts", 1)
    if attempts >= 4:
        return 2.5
    if attempts >= 2:
        return 1.5
    return 1  # first-try pass — still worth occasional depth-check

def build_topic_queue(candidate):
    missions = candidate["missions"]
    scored = sorted(missions, key=score_mission, reverse=True)
    queue = []
    for m in scored:
        day_info = DAY_LOOKUP.get(m["day"], {})
        queue.append({
            "day": m["day"],
            "title": m.get("title", day_info.get("title", "")),
            "skipped": m.get("skipped", False),
            "attempts": m.get("attempts", None),
            "objectives": day_info.get("objectives", []),
        })
    return queue

def system_prompt(candidate):
    member = candidate["member"]
    return (
        f"You are conducting a real, spoken-style technical interview for a "
        f"{member['jobRole']} candidate named {member['name']} who completed a "
        f"31-day AI engineering cohort. Ask ONE question at a time. Be conversational, "
        f"not robotic. CRITICAL: Before writing your question, first restate to yourself "
        f"(silently, do not output this) exactly what the candidate just claimed. Your "
        f"question must directly probe THAT specific claim — do not pivot to a related but "
        f"different concept. If they mention a specific tool, technique, or decision, ask "
        f"about that exact thing, not something adjacent. Reference their actual wording "
        f"when possible. Vary difficulty based on how much they struggled (more attempts or "
        f"a skipped topic = probe deeper on fundamentals; first-try passes = ask about edge "
        f"cases or trade-offs). Never repeat a question. Keep each question under 3 sentences."
    )

def generate_next_question(session):
    topic_queue = session["topic_queue"]
    if not topic_queue:
        messages = [{"role": "system", "content": system_prompt(session["candidate"])}]
        messages += session["history"]
        messages.append({"role": "user", "content": (
            "[INTERNAL] All specific curriculum topics for this candidate have been covered. "
            "Ask one final broader question about their overall approach to building production AI "
            "systems, or a synthesis question connecting two things they've already discussed."
        )})
        return call_llm(messages)

    topic = topic_queue.pop(0)
    session["days_covered"].add(topic["day"])

    status = "SKIPPED this topic entirely" if topic["skipped"] else f"passed in {topic['attempts']} attempt(s)"
    topic_context = (
        f"Ask about Day {topic['day']}: '{topic['title']}'. "
        f"Key objectives: {', '.join(topic['objectives'][:3]) or 'general understanding'}. "
        f"Candidate status: {status}."
    )

    messages = [{"role": "system", "content": system_prompt(session["candidate"])}]
    messages += session["history"]
    messages.append({"role": "user", "content": f"[INTERNAL] {topic_context} Generate the next interview question now."})

    return call_llm(messages)

def generate_followup(session, candidate_answer):
    messages = [{"role": "system", "content": system_prompt(session["candidate"])}]
    messages += session["history"]
    messages.append({"role": "user", "content": candidate_answer})
    messages.append({"role": "user", "content": (
        "[INTERNAL] Ask ONE natural follow-up question that digs deeper into what "
        "the candidate just said. Respond with ONLY the question, nothing else."
    )})
    return call_llm(messages)

def generate_feedback(session):
    messages = [{"role": "system", "content": (
        "You are summarizing a technical interview you just conducted. Based on the "
        "full conversation, produce structured feedback as JSON with EXACTLY these keys: "
        '"summary" (string), "strengths" (array of strings), "gaps" (array of strings), '
        '"next" (array of actionable next steps). Return ONLY valid JSON, no markdown fences.'
    )}]
    messages += session["history"]
    messages.append({"role": "user", "content": "[INTERNAL] Generate the final structured feedback now."})

    raw = call_llm(messages, temperature=0.3, max_tokens=600).strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"summary": raw[:300], "strengths": [], "gaps": [], "next": []}

@app.route("/api/interview", methods=["POST"])
def interview():
    try:
        data = request.get_json(force=True)
        session_id = data.get("sessionId")
        if not session_id:
            return jsonify({"error": "sessionId is required"}), 400

        # --- START ---
        if "candidate" in data and session_id not in SESSIONS:
            candidate = data["candidate"]
            SESSIONS[session_id] = {
                "candidate": candidate,
                "history": [],
                "topic_queue": build_topic_queue(candidate),
                "days_covered": set(),
                "questions_asked": 0,
            }
            session = SESSIONS[session_id]
            first_question = generate_next_question(session)
            session["history"].append({"role": "assistant", "content": first_question})
            session["questions_asked"] += 1

            member = candidate["member"]
            welcome = f"Welcome, {member['name']}. Let's begin your interview.\n\n{first_question}"
            return jsonify({"reply": welcome, "done": False})

        # --- TURN ---
        if session_id not in SESSIONS:
            return jsonify({"error": "Unknown sessionId. Start the interview first."}), 400

        session = SESSIONS[session_id]
        message = data.get("message", "")
        session["history"].append({"role": "user", "content": message})

        effective_min_days = min(MIN_DAYS, len(session["candidate"]["missions"]))
        ready_to_end = (
            (session["questions_asked"] >= MIN_QUESTIONS and len(session["days_covered"]) >= effective_min_days)
            or session["questions_asked"] >= MAX_QUESTIONS
        )

        if ready_to_end:
            feedback = generate_feedback(session)
            return jsonify({"reply": "Interview completed.", "done": True, "feedback": feedback})

        if session["topic_queue"] and random.random() > 0.4:
            next_q = generate_next_question(session)
        else:
            next_q = generate_followup(session, message)

        session["history"].append({"role": "assistant", "content": next_q})
        session["questions_asked"] += 1
        return jsonify({"reply": next_q, "done": False})

    except Exception as e:
        return jsonify({"error": "Something went wrong processing the interview.", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)