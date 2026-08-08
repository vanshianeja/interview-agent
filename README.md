# AI Interview Agent

A conversational AI agent that conducts realistic, multi-turn technical interviews based on a candidate's actual learning history from the AI Cohort curriculum.

**Live demo:** https://interview-agent-uomx.onrender.com
**Built for:** ABTalks Vibe Code Hackathon (Problem Statement 2)

## What it does

Given a candidate's completed/skipped missions and attempt counts across a 31-day AI curriculum, the agent conducts a natural, adaptive technical interview:

- Prioritizes topics the candidate struggled with (skipped topics or multiple attempts) for deeper probing
- Asks genuine follow-up questions anchored to the candidate's specific answers, not scripted questions
- Covers at least 4 different curriculum days across a minimum of 8 questions
- Produces structured feedback at the end: summary, strengths, gaps, and actionable next steps

## Architecture

- **Backend:** Flask, single `/api/interview` endpoint handling both interview start and each conversation turn
- **LLM:** OpenRouter API with multi-model fallback (tries multiple free models in sequence if one fails)
- **State:** In-memory session store keyed by `sessionId` (per hackathon spec — no persistent DB required)
- **Frontend:** Minimal single-page chat UI (vanilla JS, no framework) served via Flask's `render_template`

## Running locally

```bash
git clone https://github.com/vanshianeja/interview-agent.git
cd interview-agent
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

Create a `.env` file:
OPENROUTER_API_KEY=your_key_here

Run:
```bash
python app.py
```

Visit `http://127.0.0.1:5000`

## AI usage

See [PROMPTS.md](./PROMPTS.md) for the full log of AI-assisted development.