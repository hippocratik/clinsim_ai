"""
Patient dialogue prompts for RAG-grounded simulation.

CRITICAL DESIGN RULES:
- Patient ONLY speaks from retrieved context chunks.
- Patient NEVER volunteers information not asked about.
- Patient NEVER knows their diagnosis.
- Patient answers in first person, in plain lay language.
- If context doesn't cover the question, patient says "I'm not sure" or "I don't know".
"""

PATIENT_SYSTEM_PROMPT = """You are simulating a patient in a clinical encounter for medical resident training.

CRITICAL RULES — follow every rule exactly:
1. You ONLY answer based on the CONTEXT provided. Do NOT invent symptoms, history, or findings.
2. Speak in first person as the patient. Use simple, non-medical language.
3. You do NOT know your diagnosis. If asked directly, say "I don't know, that's why I'm here."
4. Volunteer NOTHING. Only answer what the trainee explicitly asks.
5. If the context does not contain information relevant to the question, say "I'm not sure" or "I don't really know."
6. Keep answers concise — 1 to 3 sentences unless the trainee asks for more detail.
7. Express appropriate emotion (pain, anxiety, confusion) consistent with the presenting complaint.
8. Never break character. Never acknowledge that you are an AI or that this is a simulation.

Your goal is to respond authentically as a patient based strictly on the provided context."""

PATIENT_USER_TEMPLATE = """## Patient Context (use ONLY this information to answer)

{context_chunks}

---

## Conversation History

{conversation_history}

---

## Trainee's Question

{trainee_question}

Respond as the patient. Use only the context above."""


# Chunk types to prioritise by question category
_QUESTION_ROUTING: dict[str, list[str]] = {
    "symptoms": ["presenting_complaint", "hpi"],
    "history": ["pmh", "hpi"],
    "medications": ["medications"],
    "exam": ["physical_exam"],
    "labs": ["labs"],
    "social": ["hpi", "pmh"],
    "family": ["pmh"],
    "pain": ["presenting_complaint", "hpi"],
    "onset": ["presenting_complaint", "hpi"],
    "allergy": ["medications", "pmh"],
    "default": ["presenting_complaint", "hpi", "pmh", "physical_exam"],
}

_KEYWORD_MAP: dict[str, str] = {
    # symptoms / chief complaint
    "pain": "pain",
    "hurt": "pain",
    "ache": "pain",
    "symptom": "symptoms",
    "feel": "symptoms",
    "feeling": "symptoms",
    "describe": "symptoms",
    # history
    "history": "history",
    "before": "history",
    "past": "history",
    "previous": "history",
    "condition": "history",
    "diagnos": "history",
    # medications
    "medic": "medications",
    "drug": "medications",
    "pill": "medications",
    "tablet": "medications",
    "prescription": "medications",
    "take": "medications",
    # allergy
    "allerg": "allergy",
    # social / lifestyle
    "smoke": "social",
    "drink": "social",
    "alcohol": "social",
    "work": "social",
    "live": "social",
    # onset / timing
    "when": "onset",
    "start": "onset",
    "began": "onset",
    "long": "onset",
    # family
    "family": "family",
    "parent": "family",
    "sibling": "family",
    "relative": "family",
}


def classify_question(question: str) -> list[str]:
    """
    Map a trainee question to relevant chunk types for retrieval.

    Returns a list of chunk_type strings in priority order.
    """
    q_lower = question.lower()
    for keyword, category in _KEYWORD_MAP.items():
        if keyword in q_lower:
            return _QUESTION_ROUTING.get(category, _QUESTION_ROUTING["default"])
    return _QUESTION_ROUTING["default"]


def format_context_chunks(chunks) -> str:
    """Format retrieved RAG chunks into a readable context block."""
    if not chunks:
        return "(No relevant context retrieved)"
    lines = []
    for chunk in chunks:
        if hasattr(chunk, "chunk_type"):
            chunk_type = chunk.chunk_type
            content = chunk.content
        else:
            chunk_type = chunk.get("chunk_type", "unknown")
            content = chunk.get("content", "")
        lines.append(f"[{chunk_type.upper()}]\n{content}")
    return "\n\n".join(lines)


def format_conversation_history(chat_history: list) -> str:
    """Format chat history for inclusion in the prompt. Supports both ChatMessage objects and dicts."""
    if not chat_history:
        return "(No previous conversation)"
    lines = []
    for msg in chat_history[-10:]:  # last 10 messages for context window efficiency
        if hasattr(msg, "role"):
            role = msg.role
            content = msg.content
        elif isinstance(msg, dict):
            role = msg.get("role", "")
            content = msg.get("content", "")
        else:
            role = ""
            content = ""
        speaker = "Trainee" if role == "trainee" else "Patient"
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


def build_patient_prompt(
    chunks,
    chat_history: list,
    trainee_question: str
) -> str:
    """Build the full user prompt for patient dialogue."""
    return PATIENT_USER_TEMPLATE.format(
        context_chunks=format_context_chunks(chunks),
        conversation_history=format_conversation_history(chat_history),
        trainee_question=trainee_question,
    )