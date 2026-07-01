from typing import Any, Dict, List

FLOW_STAGE_KEYWORDS = {
    "GREETING": ["hello", "hi", "good morning", "good afternoon", "good evening", "hey"],
    "INTRODUCTION": ["my name is", "this is", "calling from", "work as", "am a student", "am a teacher"],
    "DISCOVERY": ["looking for", "what features", "what requirement", "your budget", "need a", "want to buy"],
    "PRODUCT_DISCUSSION": ["suggest model", "we have", "comes with", "specifications", "ram", "processor", "screen", "warranty", "available"],
    "OBJECTION_HANDLING": ["too expensive", "any discount", "not sure", "thinking", "installment", "emi", "high price", "costly"],
    "FOLLOW_UP": ["get back to you", "will follow up", "share the details", "contact you later", "call you back"],
    "CLOSING": ["thank you", "thanks for calling", "have a nice day", "goodbye", "bye"]
}

def classify_flow_stage(text: str) -> str:
    """Classify the conversation flow stage for a given turn."""
    text_lower = text.lower()
    best_stage = "START"
    max_matches = 0
    for stage, keywords in FLOW_STAGE_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > max_matches:
            max_matches = matches
            best_stage = stage
    return best_stage

def validate_and_correct_roles(turns: List[Dict[str, Any]], classifications: Dict[str, Dict[str, Any]], threshold: float = 0.85) -> Dict[str, Dict[str, Any]]:
    """
    Validate and correct speaker roles dynamically based on flow stages.
    Returns the corrected classifications dictionary.
    """
    for i, turn in enumerate(turns):
        speaker = turn.get("speaker")
        text = turn.get("text", "")
        text_lower = text.lower()
        
        cls = classifications.get(speaker)
        if not cls:
            continue
            
        # Only apply correction rules if initial confidence is below threshold
        if cls.get("confidence", 1.0) < threshold:
            stage = classify_flow_stage(text)
            
            # Correction Rule 1: Agent asking discovery questions
            if stage == "DISCOVERY" and any(q in text_lower for q in ["what", "how", "budget", "need", "preference"]):
                if "?" in text or any(kw in text_lower for kw in ["what features", "what is your", "brand preference"]):
                    cls["role"] = "Agent"
                    cls["confidence"] = 0.90
                    cls["method"] = "flow_validator_correction"
                    
            # Correction Rule 2: Customer budget/needs statements
            elif stage == "DISCOVERY" and any(kw in text_lower for kw in ["my budget", "i want", "i need", "looking for"]):
                cls["role"] = "Customer"
                cls["confidence"] = 0.90
                cls["method"] = "flow_validator_correction"
                
            # Correction Rule 3: Customer presenting objections
            elif stage == "OBJECTION_HANDLING" and any(kw in text_lower for kw in ["too expensive", "discount", "not sure", "get back to you"]):
                cls["role"] = "Customer"
                cls["confidence"] = 0.92
                cls["method"] = "flow_validator_correction"
                
            # Correction Rule 4: Agent proposing follow-up
            elif stage == "FOLLOW_UP" and any(kw in text_lower for kw in ["i will share", "i'll share", "follow up", "call you back"]):
                cls["role"] = "Agent"
                cls["confidence"] = 0.90
                cls["method"] = "flow_validator_correction"
                
            # Correction Rule 5: Agent introducing company/greetings at start of call
            elif i < 2 and stage in ["GREETING", "INTRODUCTION"] and any(kw in text_lower for kw in ["this is", "calling from", "how can i"]):
                cls["role"] = "Agent"
                cls["confidence"] = 0.95
                cls["method"] = "flow_validator_correction"
                
    return classifications
