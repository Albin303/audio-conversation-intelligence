import math
import os
import re
from src.aspect_sentiment.model_manager import ModelManager

# Define Agent/Customer keyword weights
AGENT_RULES = {
    "welcome to": 3,
    "how can i help you": 3,
    "good morning sir": 2,
    "good afternoon sir": 2,
    "this is": 1,
    "calling from": 2,
    "what is your budget": 3,
    "brand preference": 3,
    "what about your job": 2,
    "suggest model": 2,
    "we currently have": 2,
    "we have an offer": 3,
    "emi options": 3,
    "i can suggest": 3,
    "i will share": 2,
    "i'll share": 2,
    "both are good": 2,
    "available": 1,
    "let me suggest": 3,
    "our product": 2,
    "comes with": 2,
    "warranty": 2,
    "follow up": 2,
}

CUSTOMER_RULES = {
    "i am looking for": 3,
    "i'm looking for": 3,
    "i want to buy": 3,
    "i need": 2,
    "i want": 2,
    "my name is": 1,
    "my budget is": 3,
    "budget is around": 3,
    "under": 2,
    "within": 2,
    "inr": 2,
    "rupees": 2,
    "mostly use it for": 2,
    "for my office": 2,
    "personal use": 2,
    "programming": 2,
    "coding": 2,
    "gaming": 2,
    "not sure": 2,
    "thinking": 2,
    "maybe later": 3,
    "get back to you": 3,
    "think about it": 2,
    "too expensive": 3,
    "any discount": 2,
}

AGENT_PROTOTYPES = [
    "How can I help you today?",
    "What is your budget or brand preference?",
    "We have EMI options and discounts available.",
    "I will share the details and follow up with you.",
    "I suggest looking at these models.",
    "This device comes with a warranty."
]

CUSTOMER_PROTOTYPES = [
    "I am looking to buy a new device.",
    "My budget is around 50,000 rupees.",
    "I need it for programming and gaming.",
    "I am not sure, I will think about it and get back to you.",
    "Is there any discount on this?",
    "I want something reliable under my budget."
]

GREETING_AGENT = ["welcome to", "how can i help", "how may i assist", "may i know", "this is", "calling from"]
GREETING_CUSTOMER = ["hello", "hi", "good morning", "good afternoon", "good evening"]

CLOSING_AGENT = ["follow up", "share details", "thank you for calling", "have a nice day", "contact you"]
CLOSING_CUSTOMER = ["get back to you", "maybe later", "think about it", "let you know"]

OBJECTION_TERMS = ["too expensive", "costly", "high price", "budget limit", "not sure", "hesitant", "no emi", "decide later"]
SALES_TERMS = ["emi", "installment", "finance", "loan", "offer", "discount", "festive", "warranty", "guarantee", "recommend", "suggest", "available", "we currently have"]
BUYING_TERMS = ["i want to buy", "i am looking for", "i'm looking for", "i need", "i want", "interested in", "would like to"]


def classify_role_hybrid(
    speaker_id: str,
    text: str,
    *,
    speaker_word_count: int | None = None,
    total_word_count: int | None = None,
) -> dict:
    """
    Upgraded weighted multi-signal role classifier.
    Evaluates:
      1. Vocabulary (rules)
      2. Speaking ratio
      3. Greeting behaviour
      4. Closing behaviour
      5. Question frequency
      6. Objection language
      7. Sales language
      8. Buying language
      9. Conversation flow
      10. Semantic similarity (MiniLM)
    """
    text_lower = text.lower()
    
    # 1. Vocabulary Score
    vocab_agent = sum(weight for phrase, weight in AGENT_RULES.items() if phrase in text_lower)
    vocab_customer = sum(weight for phrase, weight in CUSTOMER_RULES.items() if phrase in text_lower)
    score_vocab = float(vocab_agent - vocab_customer)
    
    # 2. Speaking Ratio Score
    ratio = 0.0
    if speaker_word_count and total_word_count:
        ratio = speaker_word_count / max(total_word_count, 1)
    
    score_ratio = 0.0
    if ratio > 0.55:
        score_ratio = 1.5
    elif ratio < 0.45 and ratio > 0:
        score_ratio = -1.5

    # 3. Greeting Behaviour
    has_agent_greet = any(phrase in text_lower for phrase in GREETING_AGENT)
    has_cust_greet = any(phrase in text_lower for phrase in GREETING_CUSTOMER)
    score_greeting = 0.0
    if has_agent_greet:
        score_greeting += 2.0
    if has_cust_greet:
        score_greeting -= 0.5

    # 4. Closing Behaviour
    has_agent_close = any(phrase in text_lower for phrase in CLOSING_AGENT)
    has_cust_close = any(phrase in text_lower for phrase in CLOSING_CUSTOMER)
    score_closing = 0.0
    if has_agent_close:
        score_closing += 2.0
    if has_cust_close:
        score_closing -= 2.0

    # 5. Question Pattern
    question_count = text.count("?") + len(re.findall(r"\b(what|which|when|where|why|how|may i|can you|could you)\b", text_lower))
    score_questions = 0.0
    if question_count > 0:
        # Agent questions are usually discovery questions
        agent_qs = len(re.findall(r"\b(your|budget|preference|requirement|use it|looking for|may i know)\b", text_lower))
        # Customer questions are about terms/pricing/discounts
        customer_qs = len(re.findall(r"\b(discount|price|available|warranty|emi|can i|get)\b", text_lower))
        score_questions = float((0.8 * question_count) + agent_qs - (0.8 * customer_qs))

    # 6. Objection Language
    objections = sum(1 for term in OBJECTION_TERMS if term in text_lower)
    score_objections = float(-2.0 * objections)

    # 7. Sales Language
    sales = sum(1 for term in SALES_TERMS if term in text_lower)
    score_sales = float(2.0 * sales)

    # 8. Buying Language
    buying = sum(1 for term in BUYING_TERMS if term in text_lower)
    score_buying = float(-2.0 * buying)

    # 9. Conversation Flow Context
    score_flow = 0.0
    # Greeting at start, closing at end style heuristics
    first_words = " ".join(text_lower.split()[:15])
    last_words = " ".join(text_lower.split()[-15:])
    if any(phrase in first_words for phrase in GREETING_AGENT):
        score_flow += 1.5
    if any(phrase in last_words for phrase in CLOSING_AGENT):
        score_flow += 1.5
    if any(phrase in last_words for phrase in CLOSING_CUSTOMER):
        score_flow -= 1.5

    # 10. Semantic Similarity fallback
    score_similarity = 0.0
    similarity_method = "none"
    try:
        from sentence_transformers import util

        model = ModelManager().get_minilm()
        text_emb = model.encode(text, convert_to_tensor=True)
        agent_embs = model.encode(AGENT_PROTOTYPES, convert_to_tensor=True)
        customer_embs = model.encode(CUSTOMER_PROTOTYPES, convert_to_tensor=True)
        
        agent_sims = util.cos_sim(text_emb, agent_embs)
        customer_sims = util.cos_sim(text_emb, customer_embs)
        
        mean_agent_sim = float(agent_sims.mean())
        mean_customer_sim = float(customer_sims.mean())
        
        score_similarity = (mean_agent_sim - mean_customer_sim) * 5.0
        similarity_method = "minilm"
    except Exception:
        # Fallback to a zero score if MiniLM cannot be loaded (memory constraint)
        pass

    # Sum of weighted signals
    weighted_sum = (
        0.4 * score_vocab
        + 0.5 * score_ratio
        + 0.5 * score_greeting
        + 0.5 * score_closing
        + 0.3 * score_questions
        + 0.5 * score_objections
        + 0.5 * score_sales
        + 0.5 * score_buying
        + 0.4 * score_flow
        + 0.4 * score_similarity
    )

    # Compute Agent probability
    p_agent = 1.0 / (1.0 + math.exp(-0.6 * weighted_sum))
    
    # Predict role and confidence
    if p_agent >= 0.5:
        role = "Agent"
        confidence = round(p_agent, 2)
    else:
        role = "Customer"
        confidence = round(1.0 - p_agent, 2)

    # Determine explanation reasons
    reasons = []
    if role == "Agent":
        if has_agent_greet or score_greeting > 0:
            reasons.append("Greeting")
        if score_vocab > 1.5:
            reasons.append("Sales Vocabulary")
        if score_sales > 1.5:
            reasons.append("Sales Vocabulary")
        if score_questions > 1.0:
            reasons.append("Question Pattern")
        if score_ratio > 0.5:
            reasons.append("Speaking Ratio")
        if has_agent_close or score_closing > 0:
            reasons.append("Closing Behavior")
        if score_flow > 1.0:
            reasons.append("Conversation Flow")
        if score_similarity > 0.5:
            reasons.append("Semantic Similarity")
    else:  # Customer
        if score_objections < -1.0 or objections > 0:
            reasons.append("Objection Language")
        if score_buying < -1.0 or buying > 0:
            reasons.append("Buying Language")
        if score_vocab < -1.5:
            reasons.append("Buying Language")
        if score_ratio < -0.5:
            reasons.append("Speaking Ratio")
        if score_closing < -0.5 or has_cust_close:
            reasons.append("Closing Behavior")
        if score_flow < -0.5:
            reasons.append("Conversation Flow")
        if score_similarity < -0.5:
            reasons.append("Semantic Similarity")
        if score_questions < -0.5:
            reasons.append("Question Pattern")

    # Dedup and ensure reasons contains at least one item
    reasons = list(dict.fromkeys(reasons))
    if not reasons:
        reasons.append("Semantic Similarity" if score_similarity != 0 else "Sales Vocabulary" if role == "Agent" else "Buying Language")

    # Limit to top 4 reasons as requested in prompt
    reasons = reasons[:4]

    return {
        "speaker": speaker_id,
        "role": role,
        "confidence": confidence,
        "reason": reasons,
        "probability": {"Agent": round(p_agent, 3), "Customer": round(1.0 - p_agent, 3)},
        "method": "weighted_multi_signal" if similarity_method == "minilm" else "multi_signal_rules",
        "signals": {
            "vocabulary": round(score_vocab, 2),
            "ratio": round(score_ratio, 2),
            "greeting": round(score_greeting, 2),
            "closing": round(score_closing, 2),
            "questions": round(score_questions, 2),
            "objections": round(score_objections, 2),
            "sales": round(score_sales, 2),
            "buying": round(score_buying, 2),
            "flow": round(score_flow, 2),
            "similarity": round(score_similarity, 2),
        }
    }
