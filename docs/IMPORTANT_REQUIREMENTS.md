# Important Requirements to Keep in Mind

## Database Setup
- **Local Docker:** DB will be spun up using Docker locally on the laptop
- **Action:** I will provide Docker setup steps when we reach Phase A-P1
- **Container:** PostgreSQL will run inside a Docker container

## Conversation Flow
- **MAX_QUESTIONS = 8** (default from config)
- After 8 questions, the conversation stops and response is generated
- No new questions asked after the limit
- This is a hard stop for the intake phase

## Speech-to-Speech Interface
- **NO CHAT INTERFACE:** Should NOT look like a chat app
- **Doctor-like interface:** Like talking to a real doctor (voice-to-voice)
- **Visual:** Should be a clean voice interface, not chat bubbles
- **Reference:** Think of it like a phone call or in-person consultation

## Guardrails
- **Topic restriction:** AI should NOT answer unrelated questions
- **Example:** If patient asks "what is Oops called Oops?" (unrelated medical topic), AI should redirect to medical intake
- **Implementation:** Add topic detection and refusal/redirect logic
- **Guardrail location:** In the conversation orchestrator (Phase A-P5)

## Language Detection & Switching
- **Dynamic language detection:** If patient changes language mid-conversation (e.g., Hindi → English), AI should detect and adapt
- **Auto-switch:** AI should change its response language to match the patient's current language
- **Implementation:** Language detection on every utterance, then route to appropriate LLM/TTS
- **Languages supported:** Hindi, Hinglish, English, Marwari (with glossary)

## Speech-to-Speech Provider Options
**Evaluating:**
1. **Sarvam AI** - Indian-focused, good for Hindi/Hinglish/Marwari
2. **11 Labs** - High quality, more general purpose

**Recommendation:** Will evaluate both in Phase A-P5 (Voice Backend) based on:
- Latency (p50/p95)
- Word-error-rate on Hindi/Hinglish/Marwari
- Cost
- Red-flag recall
- Marwari support quality

**Decision:** Will run bake-off tests and choose based on measured results

---

## Implementation Notes

### Guardrails Implementation (Phase A-P3)
- Add topic classifier before generating AI response
- If topic is unrelated: "I can only help with medical intake. Please tell me about your symptoms."
- Log refused questions for audit

### Language Switching Implementation (Phase A-P5)
- Run language detection on every ASR transcript
- Update session language state
- Route subsequent questions to appropriate language model
- Switch TTS voice to matched language

### Docker DB Setup (Phase A-P1)
Will provide steps like:
```bash
docker run --name synapse-db \
  -e POSTGRES_PASSWORD=your_password \
  -e POSTGRES_DB=synapse \
  -p 5432:5432 \
  -d postgres:16
```

---

## Priority Order
1. Phase A-P0: Stabilise backend (current)
2. Phase A-P1: Postgres + Auth (with Docker setup)
3. Phase A-P2: Queue backend
4. Phase A-P3: Clinical safety (guardrails here)
5. Phase A-P5: Voice backend (language switching + provider evaluation)
