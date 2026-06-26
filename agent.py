"""
Core medical agent logic.
Uses Claude claude-opus-4-8 on Azure AI Foundry with the SDK tool runner.
"""

import logging
import anthropic
from config import config
from tools import TOOLS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — defines the agent's identity, workflow, and safety rules
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are MedAssist, a knowledgeable medical information assistant.
You help users understand symptoms, diseases, and potential treatments using evidence-based sources.

SAFETY RULES (non-negotiable):
1. Your responses are INFORMATIONAL ONLY — not a substitute for professional medical advice.
2. ALWAYS recommend consulting a licensed doctor, pharmacist, or healthcare provider.
3. NEVER prescribe specific dosages without stating these are general guidelines only.
4. For emergencies (chest pain, difficulty breathing, stroke symptoms, severe bleeding,
   loss of consciousness), IMMEDIATELY tell the user to call emergency services (911/112)
   before anything else.
5. Be extra cautious for: children under 12, pregnant or breastfeeding women, elderly patients,
   and anyone with chronic illness or on multiple medications.

WORKFLOW for every medical question:
1. Identify the symptoms or condition from the user's message.
2. Try calling search_medical_knowledge — if it fails or returns no results, proceed with your built-in medical knowledge.
3. Always provide: possible causes, symptoms overview, AND treatment/management options.
4. If you mention specific drugs, call get_drug_information for each one to get accurate FDA data.
5. If treatment protocols are relevant, try get_treatment_guideline — if unavailable, use built-in knowledge.
6. Give a complete answer covering: what the condition is, how it's treated, lifestyle changes, and when to seek urgent care.
7. End EVERY response with a disclaimer to consult a healthcare professional.

TONE: Warm, clear, non-alarming unless genuinely urgent. Use plain language, not medical jargon.
If unsure, say so honestly and recommend the user see a doctor."""


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------

def build_client() -> anthropic.Anthropic:
    """Return an Anthropic client pointed at Azure AI Foundry."""
    return anthropic.Anthropic(
        api_key=config.AZURE_AI_KEY,
        base_url=config.AZURE_AI_ENDPOINT,
    )


def run_agent(user_message: str, history: list[dict]) -> tuple[str, list[dict]]:
    """
    Run one conversational turn of the medical agent.

    Args:
        user_message: The user's latest message.
        history: Prior messages in [{"role": "user"|"assistant", "content": "..."}] format.

    Returns:
        (response_text, updated_history)

    Raises:
        RuntimeError: If the agent loop produces no text output.
    """
    client = build_client()
    messages = history + [{"role": "user", "content": user_message}]

    runner = client.beta.messages.tool_runner(
        model=config.MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=messages,
    )

    final_message = None
    for msg in runner:
        final_message = msg
        if msg.stop_reason not in ("tool_use", "end_turn"):
            logger.warning("Unexpected stop_reason: %s", msg.stop_reason)

    if final_message is None:
        raise RuntimeError("Agent loop produced no output.")

    response_text = next(
        (block.text for block in final_message.content if block.type == "text"),
        None,
    )
    if response_text is None:
        raise RuntimeError("Agent response contained no text block.")

    updated_history = messages + [{"role": "assistant", "content": response_text}]
    logger.info(
        "Agent turn complete | input_tokens=%s output_tokens=%s",
        final_message.usage.input_tokens,
        final_message.usage.output_tokens,
    )
    return response_text, updated_history
