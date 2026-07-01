import json
import os
import hashlib
import httpx
import asyncio
from pathlib import Path
from typing import Any


from dotenv import load_dotenv
import re

# ================================
# CONFIG
# ================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env.local")

MODEL = os.getenv("LLAMA_MODEL", "llama-3.3-70b-versatile")
BASE_URL = os.getenv("LLAMA_API_URL", "https://api.groq.com/openai/v1")
BASE_URL = BASE_URL.removesuffix("/chat/completions").rstrip("/")
CHAT_COMPLETIONS_URL = f"{BASE_URL}/chat/completions"

BRAND_TERMS = [
    "samsung",
    "iphone",
    "apple",
    "oneplus",
    "vivo",
    "oppo",
    "xiaomi",
    "redmi",
    "realme",
    "dell",
    "hp",
    "lenovo",
    "acer",
    "asus",
    "lg",
    "sony",
]
PRODUCT_TERMS = ["phone", "mobile", "cell", "cell phone", "laptop", "tv", "ac", "refrigerator"]
FEATURE_TERMS = [
    "camera",
    "battery",
    "display",
    "storage",
    "ram",
    "processor",
    "performance",
    "charging",
    "video",
]
BUDGET_RX = re.compile(
    r"\b(?:budget(?:\s+is)?|under|within|around|price|cost)\s*(?:is|of|:)?\s*(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(k|lakh|lakhs)?\b",
    re.IGNORECASE,
)
MONEY_RX = re.compile(r"\b(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(k|lakh|lakhs)?\b", re.IGNORECASE)
ENUM_LABELS = {
    "INTENT",
    "URGENCY",
    "DECISION_STAGE",
    "URGENCY_LEVEL",
    "PRICE_SENSITIVITY",
    "BRAND_LOYALTY",
    "FOLLOW_UP_PROBABILITY",
    "EMOTIONAL_CONFIDENCE",
    "COMPETITOR",
    "DECISION_MAKER",
    "ESCALATION_REQUEST",
    "FOLLOW_UP_REQUEST",
    "DELAY_SIGNAL",
    "PRICE_DISCUSSION",
    "BUDGET_DISCUSSION",
}
ENUM_EVIDENCE = {
    "INTENT": ("buy", "purchase", "want", "need", "interested", "looking for"),
    "URGENCY": ("today", "tomorrow", "week", "month", "urgent", "immediately", "later"),
    "URGENCY_LEVEL": ("today", "tomorrow", "week", "month", "urgent", "immediately", "later"),
    "DECISION_STAGE": ("consider", "compare", "thinking", "decide", "ready", "later", "follow up"),
    "PRICE_SENSITIVITY": ("price", "budget", "cost", "expensive", "cheap", "discount"),
    "BRAND_LOYALTY": ("brand", "prefer", "always use", "loyal"),
    "FOLLOW_UP_PROBABILITY": ("follow up", "call back", "get back", "later", "contact"),
    "EMOTIONAL_CONFIDENCE": ("sure", "definitely", "maybe", "not sure", "confident"),
    "COMPETITOR": ("apple", "samsung", "oneplus", "dell", "hp", "lenovo", "acer", "asus", "macbook", "brand", "vs", "compare"),
    "DECISION_MAKER": ("boss", "father", "spouse", "wife", "husband", "myself", "partner", "manager", "decision"),
    "ESCALATION_REQUEST": ("manager", "supervisor", "escalate", "higher up", "talk to"),
    "FOLLOW_UP_REQUEST": ("call", "email", "get back", "send", "brochure", "details"),
    "DELAY_SIGNAL": ("later", "next week", "postpone", "after", "next month", "think"),
    "PRICE_DISCUSSION": ("price", "cost", "discount", "emi", "installment", "charge", "rupees", "inr", "₹"),
    "BUDGET_DISCUSSION": ("budget", "limit", "max", "under", "within", "around"),
}


def _normalize_money(amount: str, suffix: str | None = None) -> str:
    value = float(amount.replace(",", ""))
    suffix = (suffix or "").lower()
    if suffix == "k":
        value *= 1000
    elif suffix in {"lakh", "lakhs"}:
        value *= 100000
    return str(int(value)) if value.is_integer() else str(value)


def _append_unique(features, value, label):
    clean_value = str(value).strip()
    if not clean_value:
        return
    key = (clean_value.lower(), label)
    existing = {
        (str(f.get("value", f.get("name", ""))).strip().lower(), str(f.get("label", "")))
        for f in features
    }
    if key not in existing:
        features.append({"value": clean_value, "name": clean_value, "label": label})


def rule_based_features(text):
    """Local safety net for sales facts LLaMA often misses in noisy transcripts."""
    text_lower = text.lower()
    features = []

    for term in PRODUCT_TERMS:
        if re.search(rf"\b{re.escape(term)}s?\b", text_lower):
            canonical = "phone" if term in {"mobile", "cell", "cell phone"} else term
            _append_unique(features, canonical, "PRODUCT")

    for term in BRAND_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", text_lower):
            _append_unique(features, "iPhone" if term == "iphone" else term.title(), "BRAND")

    for term in FEATURE_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", text_lower):
            _append_unique(features, term, "FEATURE")

    for match in BUDGET_RX.finditer(text):
        _append_unique(features, _normalize_money(match.group(1), match.group(2)), "BUDGET")

    if any(term in text_lower for term in ["looking for", "i want", "i need", "interested"]):
        _append_unique(features, "Interested", "INTENT")
    if any(term in text_lower for term in ["consider", "thinking", "not sure", "maybe"]):
        _append_unique(features, "Considering", "DECISION_STAGE")
    if any(term in text_lower for term in ["teacher", "student", "business", "job", "profession"]):
        _append_unique(features, "Work/personal use", "USE_CASE")
    if any(term in text_lower for term in ["expensive", "costly", "discount", "cheap", "low budget", "price sensitive"]):
        _append_unique(features, "High", "PRICE_SENSITIVITY")
    elif any(term in text_lower for term in ["premium", "best model", "top model"]):
        _append_unique(features, "Low", "PRICE_SENSITIVITY")

    return features


CACHE_DIR = PROJECT_ROOT / "data" / "cache" / "llama"

async def call_llama(messages):
    api_key = os.getenv("LLAMA_API_KEY")
    if not api_key:
        raise ValueError(
            f"Set LLAMA_API_KEY in your environment or in {PROJECT_ROOT / '.env.local'}"
        )

    # Serialize messages to generate a stable cache key
    serialized = json.dumps(messages, sort_keys=True)
    cache_key = hashlib.md5(serialized.encode("utf-8")).hexdigest()
    
    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    # Check disk cache
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    payload = {
        "model": MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": messages
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "aspect-sentiment-client/1.0",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(CHAT_COMPLETIONS_URL, json=payload, headers=headers, timeout=90.0)
            response.raise_for_status()
            res_json = response.json()
            
            # Write to disk cache
            try:
                cache_file.write_text(json.dumps(res_json), encoding="utf-8")
            except Exception:
                pass
                
            return res_json
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            raise RuntimeError(f"Groq API HTTP {exc.response.status_code}: {detail}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Groq API connection error: {exc}") from exc



# ================================
# PROMPT
# ================================

SYSTEM_PROMPT = "You are an expert AI that extracts structured sales data."
SUMMARY_SYSTEM_PROMPT = "You are an expert sales call summarizer. Return concise STRICT JSON only."

def build_prompt(text):
    return f"""
Extract structured sales features.

Return JSON:
{{
  "features": [
    {{
      "value": "Exact semantic value (e.g., 'RTX 4050', '85000', 'Considering')",
      "label": "PRODUCT|BRAND|BUDGET|FEATURE|INTENT|URGENCY|DECISION_STAGE|USE_CASE|OBJECTION|URGENCY_LEVEL|OBJECTION_TYPE|PRICE_SENSITIVITY|BRAND_LOYALTY|FOLLOW_UP_PROBABILITY|EMOTIONAL_CONFIDENCE|COMPETITOR|DECISION_MAKER|ESCALATION_REQUEST|FOLLOW_UP_REQUEST|DELAY_SIGNAL|PRICE_DISCUSSION|BUDGET_DISCUSSION"
    }}
  ]
}}

CRITICAL RULES:
- Extract literal, semantic values, NOT schema names. (e.g., Extract "RTX 4050", NOT "graphics card". Extract "85000", NOT "Budget").
- For BUDGET, extract ONLY the actual numerical amount (e.g., "85000").
- For DECISION_STAGE, strictly use one of: Awareness, Exploring, Evaluating, Considering, Comparing Alternatives, Budget Discussion, Negotiation, Near Purchase, Purchase Delayed, Follow-up Required, Ready to Purchase, Converted, Dropped.
- For INTENT, strictly use one of: Low Interest, Curious, Warm Lead, Interested, High Interest, Strong Buying Intent, Comparison Shopper, Price Sensitive, Hesitant Buyer, Ready to Purchase.
- For OBJECTION, extract explicit reasons for hesitation (e.g., "too expensive", "no EMI").
- For other customer signals like URGENCY_LEVEL, OBJECTION_TYPE, PRICE_SENSITIVITY, BRAND_LOYALTY, FOLLOW_UP_PROBABILITY, EMOTIONAL_CONFIDENCE, provide concise descriptive values.
- For COMPETITOR, extract competitor brands mentioned (e.g., "HP", "Lenovo", "Dell", "MacBook").
- For DECISION_MAKER, extract who makes the decision (e.g., "self", "father", "spouse", "boss").
- For ESCALATION_REQUEST, extract if the customer requests a manager or escalation (e.g., "wants manager", "escalation requested").
- For FOLLOW_UP_REQUEST, extract follow-up request details (e.g., "call tomorrow", "email brochure").
- For DELAY_SIGNAL, extract reasons for delay or post-ponement (e.g., "decide after holiday", "next week").
- For PRICE_DISCUSSION, extract terms related to price talk (e.g., "discount inquiry", "emi options pricing").
- For BUDGET_DISCUSSION, extract terms related to budget limits (e.g., "under 50k", "strict budget").
- If not relevant → return empty list.

Input:
{text}

Output:
"""


def build_summary_prompt(transcript: str, customer_text: str = "", agent_text: str = ""):
    return f"""
Summarize this sales call or customer conversation for a CRM dashboard.

Return JSON:
{{
  "Conversation Summary": "2-3 sentence overview of the conversation and customer interests",
  "Key Moments": ["list of key events or turn points in the call"],
  "Important Quotes": ["2-3 significant direct or indirect quotes showing intent/objection"],
  "Action Items": ["list of next steps for the agent"],
  "Risks": ["list of any potential risks, objections, or reasons the deal might drop"],
  "Recommendations": ["list of recommendations to move the lead forward"],
  "overview": "2 sentence plain-English summary of what happened",
  "customerNeed": "main customer requirement or interest",
  "keyPoints": ["3 to 5 important facts, preferences, objections, offers, or decisions"],
  "outcome": "current call outcome or decision status",
  "nextAction": "best next step for the sales agent",
  "confidence": 0.0
}}

Rules:
- Do not invent facts.
- Keep each field concise.
- Use customer-safe language and avoid exposing private personal details.
- confidence must be a number between 0 and 1.
- If there is not enough context, say so clearly in the values.

Full transcript:
{transcript}

Customer-only transcript:
{customer_text}

Agent-only transcript:
{agent_text}

Output:
"""

# ================================
# PRE-CHECK (Layer 1: Quick Intent Detection)
# ================================

def is_relevant(text):
    text = text.lower().strip()
    
    # Layer 3 filters: Catch empty, garbage, or pure greetings early
    words = text.split()
    if len(words) < 3:
        return False  # Too short
        
    alnum_ratio = sum(c.isalnum() for c in text) / max(len(text), 1)
    if alnum_ratio < 0.5:
        return False  # Garbage input
        
    pure_greetings = ["hi", "hello", "hey", "how are you", "good morning", "good afternoon", "testing"]
    if any(text == g for g in pure_greetings):
        return False  # Just a greeting

    # Layer 1: Force LLaMA for meaningful conversations using Weighted Scoring
    score = 0
    
    # 1. Product conversations
    products = ["laptop", "tv", "phone", "ac", "refrigerator", "samsung", "apple", "lg", "sony", "device", "machine", "software", "service"]
    if any(p in text for p in products): score += 3
    
    # 2. Budget discussions & Numbers
    budget = ["price", "cost", "budget", "how much", "expensive", "cheap", "offer", "discount", "deal"]
    if any(b in text for b in budget): score += 2
    if any(char.isdigit() for char in text): score += 1
    
    # 3. Buying intent
    buying_intent = ["buy", "purchase", "want", "need", "looking", "interested", "recommend", "suggest", "options"]
    if any(i in text for i in buying_intent): score += 3
    
    # 4. Comparisons
    comparisons = ["better", "compare", "difference", "vs", "versus", "which one"]
    if any(c in text for c in comparisons): score += 2
    
    # 5. EMI / Payment
    payments = ["emi", "installment", "finance", "loan", "card", "cash", "payment"]
    if any(p in text for p in payments): score += 2
    
    # 6. Hesitation
    hesitation = ["not sure", "thinking", "maybe", "later", "wait", "consider"]
    if any(h in text for h in hesitation): score += 1
    
    # 7. Contextual depth
    if len(words) > 15: score += 2
    if len(words) > 30: score += 2
        
    # Threshold: If score >= 3, it's a serious conversation requiring LLaMA 3
    return score >= 3

# ================================
# POST-PROCESSING
# ================================

def fix_labels(features):
    fixed = []

    for f in features:
        raw_val = f.get("value", f.get("name", ""))
        name = str(raw_val).lower()
        label = f.get("label", "")

        if any(x in name for x in ["day", "week", "month", "tomorrow", "today"]):
            if "warranty" not in name and "subscription" not in name:
                label = "URGENCY"

        if name in ["coding", "gaming", "office work", "daily use", "programming", "editing"]:
            label = "USE_CASE"

        # LLaMA is usually accurate, so we only override to BUDGET if it clearly contains
        # currency terms or if the LLaMA label is completely wrong.
        currency_markers = ['$', '₹', 'rs', 'rupees', 'budget', 'price', 'cost', 'under']
        if any(c in name for c in currency_markers):
            if not any(x in name for x in ["rtx", "ryzen", "intel", "amd", "gb", "tb"]):
                label = "BUDGET"
            
        # Fix specific common tech components that might get mislabeled
        if any(x in name for x in ["rtx", "ryzen", "intel", "amd", "geforce", "nvidia", "ram", "gb", "tb", "ssd", "warranty"]):
            if label not in ["PRODUCT", "BRAND"]:
                label = "FEATURE"

        f["label"] = label
        f["name"] = raw_val
        f["value"] = raw_val
        fixed.append(f)

    return fixed


def _feature_is_grounded(feature, text):
    value = str(feature.get("value", feature.get("name", ""))).strip()
    label = str(feature.get("label", "")).upper()
    if not value or not label:
        return False
    text_lower = text.lower()
    value_lower = value.lower()
    if label in ENUM_LABELS:
        return any(marker in text_lower for marker in ENUM_EVIDENCE.get(label, ()))
    if value_lower in text_lower:
        return True

    if label == "BUDGET":
        normalized_value = re.sub(r"\D", "", value)
        for match in BUDGET_RX.finditer(text):
            normalized_budget = re.sub(r"\D", "", _normalize_money(match.group(1), match.group(2)))
            if normalized_value == normalized_budget:
                return True
        return False

    meaningful_words = [
        word
        for word in re.findall(r"[a-z0-9]+", value_lower)
        if len(word) >= 3 and word not in {"the", "and", "with", "for"}
    ]
    return bool(meaningful_words) and all(
        re.search(rf"\b{re.escape(word)}\b", text_lower) for word in meaningful_words
    )


def merge_rule_features(llama_features, text):
    features = [
        feature
        for feature in fix_labels(llama_features or [])
        if _feature_is_grounded(feature, text)
    ]
    for feature in rule_based_features(text):
        _append_unique(features, feature.get("value", ""), feature.get("label", "FEATURE"))
    return features

# ================================
# SENTIMENT
# ================================

_sentiment_analyzer = None

def get_sentiment(text):
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        _sentiment_analyzer = SentimentIntensityAnalyzer()
    return _sentiment_analyzer.polarity_scores(text)["compound"]

# ================================
# FEATURE ENGINEERING
# ================================

def derive_features(text, features):
    text_lower = text.lower()

    # ======================
    # CONFIDENCE (IMPROVED)
    # ======================
    if any(w in text_lower for w in ["definitely", "sure", "will buy", "confirm"]):
        confidence = 0.9
    elif any(w in text_lower for w in ["probably"]):
        confidence = 0.7
    elif any(w in text_lower for w in ["maybe", "not sure", "thinking"]):
        confidence = 0.3
    else:
        confidence = 0.5

    # ======================
    # HESITATION (STRONG FIX)
    # ======================
    hesitation_words = ["maybe", "thinking", "not sure", "later", "wait", "consider"]
    hesitation = sum(1 for w in hesitation_words if w in text_lower)

    # 🔥 EXTRA: Delay signal (VERY IMPORTANT)
    delay_flag = 0
    if any(w in text_lower for w in ["later", "get back", "think about", "not now"]):
        delay_flag = 1
        hesitation += 2   # increase hesitation strongly

    # ======================
    # COUNTS
    # ======================
    brands = [f for f in features if f["label"] == "BRAND"]
    feats = [f for f in features if f["label"] == "FEATURE"]

    # ======================
    # INTERACTION LENGTH
    # ======================
    length = len(text.split())
    if length < 50:
        interaction = 1
    elif length < 120:
        interaction = 2
    else:
        interaction = 3

    # ======================
  
    # ======================
    # Penalize confidence if hesitation high
    if hesitation >= 2:
        confidence = max(0.2, confidence - 0.3)

    return {
        "confidence_score": confidence,
        "hesitation_score": hesitation,
        "delay_flag": delay_flag,   # 🔥 NEW FEATURE
        "brand_count": len(brands),
        "feature_count": len(feats),
        "interaction_length": interaction
    }

# ================================
# MAIN PIPELINE
# ================================

async def process_text(text):

    if not is_relevant(text):
        print("⚠️ Out-of-context input")
        return None

    try:
        response = await call_llama(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(text)}
            ]
        )

        content = response["choices"][0]["message"]["content"]
        data = json.loads(content)

        features = merge_rule_features(data.get("features", []), text)

        sentiment = get_sentiment(text)
        derived = derive_features(text, features)

        return {
            "raw_features": features,
            "sentiment_score": sentiment,
            **derived
        }

    except Exception as e:
        print("API Error:", e)
        return None


def _fallback_summary(transcript: str, customer_text: str = "", agent_text: str = ""):
    source = " ".join((customer_text or transcript).split())
    lower = source.lower()

    need = "Customer requirement is not clear from the conversation."
    for product in PRODUCT_TERMS:
        if re.search(rf"\b{re.escape(product)}s?\b", lower):
            need = f"Customer is interested in a {product}."
            break

    budget = None
    for match in BUDGET_RX.finditer(source):
        budget = _normalize_money(match.group(1), match.group(2))
        break

    key_points = []
    if need:
        key_points.append(need)
    if budget:
        key_points.append(f"Budget mentioned: {budget}.")
    if any(term in lower for term in ["not sure", "maybe", "thinking", "later", "get back"]):
        key_points.append("Customer showed hesitation or delayed the decision.")
    if any(term in (agent_text or transcript).lower() for term in ["offer", "discount", "emi"]):
        key_points.append("Agent discussed an offer, discount, or EMI option.")

    if not key_points:
        key_points.append("Conversation has limited sales detail.")

    outcome = "Follow-up required" if any(term in lower for term in ["later", "get back", "think about"]) else "Conversation analyzed"
    next_action = "Follow up with the customer and address the main requirement or objection."

    overview = source[:220] + ("..." if len(source) > 220 else "") if source else "No conversation text was available to summarize."

    # Phase 3: New summary fields fallback
    conv_summary = overview
    key_moments = key_points
    important_quotes = [
        f'"{sentence.strip()}"'
        for sentence in re.split(r"[.!?]", source)
        if any(term in sentence.lower() for term in ["buy", "need", "want", "budget", "expensive"])
    ][:2]
    action_items = [next_action]
    risks = []
    if any(term in lower for term in ["expensive", "costly", "not sure", "think about it"]):
        risks.append("Price sensitivity or buyer hesitation detected.")
    recommendations = ["Address any objections regarding price or features and present EMI/financing options if available."]

    return {
        "Conversation Summary": conv_summary,
        "Key Moments": key_moments,
        "Important Quotes": important_quotes,
        "Action Items": action_items,
        "Risks": risks,
        "Recommendations": recommendations,
        "overview": overview,
        "customerNeed": need,
        "keyPoints": key_points[:5],
        "outcome": outcome,
        "nextAction": next_action,
        "confidence": 0.45,
        "provider": "local-fallback",
    }


async def summarize_conversation(transcript: str, customer_text: str = "", agent_text: str = ""):
    clean_transcript = " ".join(transcript.split())
    if not clean_transcript:
        return _fallback_summary(clean_transcript, customer_text, agent_text)

    try:
        response = await call_llama(
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": build_summary_prompt(clean_transcript, customer_text, agent_text)},
            ]
        )
        content = response["choices"][0]["message"]["content"]
        data = json.loads(content)

        key_points = data.get("keyPoints", data.get("Key Moments", []))
        if not isinstance(key_points, list):
            key_points = [str(key_points)]

        confidence = data.get("confidence", 0.7)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.7

        return {
            "Conversation Summary": str(data.get("Conversation Summary") or data.get("overview") or "").strip(),
            "Key Moments": [str(item).strip() for item in data.get("Key Moments", key_points) if str(item).strip()][:5],
            "Important Quotes": [str(item).strip() for item in data.get("Important Quotes", []) if str(item).strip()][:5],
            "Action Items": [str(item).strip() for item in data.get("Action Items", [data.get("nextAction")]) if str(item).strip()][:5],
            "Risks": [str(item).strip() for item in data.get("Risks", []) if str(item).strip()][:5],
            "Recommendations": [str(item).strip() for item in data.get("Recommendations", []) if str(item).strip()][:5],
            # Keep original keys for backward compatibility
            "overview": str(data.get("overview") or data.get("Conversation Summary") or "").strip() or "Summary was generated, but no overview was returned.",
            "customerNeed": str(data.get("customerNeed") or "").strip() or "Customer requirement is not clear from the conversation.",
            "keyPoints": [str(item).strip() for item in key_points if str(item).strip()][:5],
            "outcome": str(data.get("outcome") or "").strip() or "Outcome not clearly stated.",
            "nextAction": str(data.get("nextAction") or "").strip() or "Follow up with the customer.",
            "confidence": confidence,
            "provider": f"llama:{MODEL}",
        }
    except Exception as e:
        print("Summary API Error:", e)
        return _fallback_summary(clean_transcript, customer_text, agent_text)


def detect_conversation_stages(turns: list[Any]) -> list[dict[str, Any]]:
    """
    Detects the stage of each segment of the conversation.
    Stages: Opening -> Discovery -> Pricing -> Negotiation -> Closing
    Uses phrase triggers and position-based structural context.
    """
    if not turns:
        return []

    # 1. Define phrase patterns for each stage
    stage_patterns = {
        "Opening": re.compile(
            r"\b(hello|hi|hey|morning|afternoon|evening|welcome|this is|calling from|how can i help|how may i help|how assist)\b",
            re.IGNORECASE,
        ),
        "Discovery": re.compile(
            r"\b(looking for|need|want|interested|budget|brand|preference|requirement|use case|programming|gaming|features|specifications|specs|models|suggest)\b",
            re.IGNORECASE,
        ),
        "Pricing": re.compile(
            r"\b(price|cost|how much|charges|emi|installment|discounts?|offers?|rupees|inr|₹|finance|rate|monthly)\b",
            re.IGNORECASE,
        ),
        "Negotiation": re.compile(
            r"\b(expensive|costly|high|budget limit|not sure|thinking|maybe later|get back|think about|competitor|dell|hp|lenovo|samsung|macbook|compare|but|reason|objection)\b",
            re.IGNORECASE,
        ),
        "Closing": re.compile(
            r"\b(thank you|thanks|bye|goodbye|have a nice day|follow up|share details|send email|contact details|call back)\b",
            re.IGNORECASE,
        ),
    }

    num_turns = len(turns)
    turn_stages = []

    for idx, turn in enumerate(turns):
        text = getattr(turn, "text", "") if not isinstance(turn, dict) else turn.get("text", "")
        text_lower = text.lower()

        # Calculate keyword match score for each stage
        scores = {stage: len(pattern.findall(text_lower)) for stage, pattern in stage_patterns.items()}

        # Incorporate positional/structural bias
        rel_pos = idx / max(num_turns - 1, 1)

        if rel_pos <= 0.2:
            scores["Opening"] += 2.0
            scores["Discovery"] += 0.5
        elif rel_pos <= 0.5:
            scores["Discovery"] += 2.0
            scores["Pricing"] += 0.5
            scores["Opening"] += 0.2
        elif rel_pos <= 0.75:
            scores["Pricing"] += 2.0
            scores["Negotiation"] += 1.0
            scores["Discovery"] += 0.5
        elif rel_pos <= 0.9:
            scores["Negotiation"] += 2.0
            scores["Pricing"] += 0.5
            scores["Closing"] += 0.5
        else:
            scores["Closing"] += 2.0
            scores["Negotiation"] += 0.5

        # Select stage with the highest score
        detected_stage = max(scores, key=scores.get)
        turn_stages.append(detected_stage)

    # 2. Smooth the stages to form contiguous segments (avoid too much jumping)
    smoothed_stages = list(turn_stages)
    for idx in range(1, num_turns - 1):
        if turn_stages[idx - 1] == turn_stages[idx + 1] and turn_stages[idx] != turn_stages[idx - 1]:
            smoothed_stages[idx] = turn_stages[idx - 1]

    # Ensure monotonic or logical flow alignment (avoid random jump back to Opening late in the call)
    for idx in range(num_turns):
        rel_pos = idx / max(num_turns - 1, 1)
        if rel_pos > 0.7 and smoothed_stages[idx] in ["Opening", "Discovery"]:
            smoothed_stages[idx] = "Negotiation" if rel_pos <= 0.9 else "Closing"

    # 3. Group turns into segments
    segments = []
    if num_turns == 0:
        return segments

    current_stage = smoothed_stages[0]
    start_idx = 0
    start_time = getattr(turns[0], "start", 0.0) if not isinstance(turns[0], dict) else turns[0].get("start", 0.0)
    if start_time is None:
        start_time = 0.0

    for idx in range(1, num_turns):
        stage = smoothed_stages[idx]
        if stage != current_stage:
            prev_end = getattr(turns[idx - 1], "end", None) if not isinstance(turns[idx - 1], dict) else turns[idx - 1].get("end", None)
            end_time = prev_end if prev_end is not None else (start_time + 1.0)
            
            segment_turns = turns[start_idx:idx]
            conf = sum(getattr(t, "confidence", 0.8) or 0.8 if not isinstance(t, dict) else t.get("confidence", 0.8) or 0.8 for t in segment_turns) / len(segment_turns)

            segments.append({
                "stage": current_stage,
                "startIndex": start_idx,
                "endIndex": idx - 1,
                "startTime": start_time,
                "endTime": end_time,
                "confidence": round(conf, 2)
            })
            
            current_stage = stage
            start_idx = idx
            next_start = getattr(turns[idx], "start", None) if not isinstance(turns[idx], dict) else turns[idx].get("start", None)
            start_time = next_start if next_start is not None else end_time

    # Add the final segment
    last_end = getattr(turns[-1], "end", None) if not isinstance(turns[-1], dict) else turns[-1].get("end", None)
    end_time = last_end if last_end is not None else (start_time + 1.0)
    
    segment_turns = turns[start_idx:]
    conf = sum(getattr(t, "confidence", 0.8) or 0.8 if not isinstance(t, dict) else t.get("confidence", 0.8) or 0.8 for t in segment_turns) / len(segment_turns)
    segments.append({
        "stage": current_stage,
        "startIndex": start_idx,
        "endIndex": num_turns - 1,
        "startTime": start_time,
        "endTime": end_time,
        "confidence": round(conf, 2)
    })

    return segments


# ================================
# TEST
# ================================

if __name__ == "__main__":
    text = "Start. Hi, I want a laptop under 60,000. Sure. What will you mainly use it for? Programming and basic gaming. Do you have any brand performance like Dell HP or Lenovo? Not really. Just something reliable. Oh, okay. I can suggest a Dell Inspired on and a Lenovo idea part in that range. Both are good for programming. Okay, but I'm not sure if I should buy now. We currently have an offer and the EMA options available. I think about it and get back to you later. Okay, sure. I'll share the details with you. Thank you"

    result = asyncio.run(process_text(text))

    print("\nFinal Output:")
    print(json.dumps(result, indent=2))
