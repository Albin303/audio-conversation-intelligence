import re
from typing import Any
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = None

def get_analyzer() -> SentimentIntensityAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentIntensityAnalyzer()
    return _analyzer

def compute_turn_sentiment(text: str) -> float:
    """Compute VADER compound sentiment score for a turn's text."""
    analyzer = get_analyzer()
    return float(analyzer.polarity_scores(text)["compound"])

def map_sentiment_label(text: str, score: float) -> str:
    """
    Maps compound score and keywords to labels:
    Positive, Neutral, Frustrated, Interested, Ready To Buy
    """
    text_lower = text.lower()
    
    # 1. Ready To Buy indicators
    ready_to_buy_keywords = [
        "ready to buy", "will buy", "confirm the order", "take it", 
        "purchasing", "go ahead", "order now", "subscribe now", 
        "book it", "finalize this", "buy this"
    ]
    if any(kw in text_lower for kw in ready_to_buy_keywords) or (score > 0.4 and any(kw in text_lower for kw in ["buy", "purchase", "order", "take"])):
        return "Ready To Buy"
        
    # 2. Interested indicators
    interested_keywords = [
        "interested", "looking for", "how much", "tell me more", 
        "details", "options", "suggest", "recommend", "would like to"
    ]
    if any(kw in text_lower for kw in interested_keywords) or (score > 0.15 and any(kw in text_lower for kw in ["want", "need", "like"])):
        return "Interested"
        
    # 3. Frustrated indicators
    frustrated_keywords = [
        "frustrated", "annoyed", "bad", "terrible", "useless", "complaint",
        "too expensive", "costly", "unhappy", "delay", "waiting too long", 
        "poor", "dissatisfied", "disappointed", "waste"
    ]
    if any(kw in text_lower for kw in frustrated_keywords) or score < -0.15:
        return "Frustrated"
        
    # 4. General Positive / Neutral based on score
    if score > 0.15:
        return "Positive"
    elif score < -0.15:
        return "Frustrated"
    else:
        return "Neutral"

def compute_sentiment_timeline(turns: list[Any]) -> dict[str, Any]:
    """
    Computes sentiment scores and labels per turn, detects emotional transition points,
    and returns a structured sentiment timeline.
    """
    timeline_turns = []
    transitions = []
    
    if not turns:
        return {
            "turns": [],
            "transitions": [],
            "summary": {
                "startLabel": "Neutral",
                "endLabel": "Neutral",
                "trend": "Stable",
                "transitionCount": 0,
                "curveConfidence": 1.0
            }
        }
        
    for idx, turn in enumerate(turns):
        text = getattr(turn, "text", "") if not isinstance(turn, dict) else turn.get("text", "")
        speaker = getattr(turn, "speaker", "Unknown") if not isinstance(turn, dict) else turn.get("speaker", "Unknown")
        start = getattr(turn, "start", 0.0) if not isinstance(turn, dict) else turn.get("start", 0.0)
        if start is None:
            start = 0.0
        end = getattr(turn, "end", start + 1.0) if not isinstance(turn, dict) else turn.get("end", start + 1.0)
        if end is None:
            end = start + 1.0
        
        score = compute_turn_sentiment(text)
        label = map_sentiment_label(text, score)
        
        timeline_turns.append({
            "turnIndex": idx,
            "speaker": speaker,
            "text": text,
            "sentimentScore": round(score, 3),
            "sentimentLabel": label,
            "start": start,
            "end": end
        })
        
    # Detect transitions
    # Only map transitions for the customer turns (or all turns? All turns is better, but customer is primary focus)
    # Let's detect transitions across consecutive turns
    for idx in range(1, len(timeline_turns)):
        prev = timeline_turns[idx - 1]
        curr = timeline_turns[idx]
        
        if prev["sentimentLabel"] != curr["sentimentLabel"]:
            # Significant transition
            score_diff = abs(curr["sentimentScore"] - prev["sentimentScore"])
            # Confidence is scaled based on difference in scores or label severity
            # Higher diff -> higher confidence in the transition. Base confidence is 0.5.
            conf = min(1.0, 0.5 + (score_diff / 2.0))
            
            transitions.append({
                "fromIndex": prev["turnIndex"],
                "toIndex": curr["turnIndex"],
                "fromLabel": prev["sentimentLabel"],
                "toLabel": curr["sentimentLabel"],
                "fromScore": prev["sentimentScore"],
                "toScore": curr["sentimentScore"],
                "time": curr["start"],
                "confidence": round(conf, 2)
            })
            
    # Calculate Overall Summary
    start_label = timeline_turns[0]["sentimentLabel"]
    end_label = timeline_turns[-1]["sentimentLabel"]
    
    # Trend detection based on the slope of scores
    scores = [t["sentimentScore"] for t in timeline_turns]
    if len(scores) >= 2:
        # Check simple linear fit slope or start vs end
        slope = scores[-1] - scores[0]
        # Weighted towards customer sentiment
        cust_scores = [t["sentimentScore"] for t in timeline_turns if t["speaker"] == "Customer"]
        if len(cust_scores) >= 2:
            slope = cust_scores[-1] - cust_scores[0]
            
        if slope > 0.2:
            trend = "Improving"
        elif slope < -0.2:
            trend = "Declining"
        else:
            trend = "Stable"
    else:
        trend = "Stable"
        
    # Curve confidence: average turn sentiment confidence (using VADER scores absolute value as proxy or default 0.8)
    curve_conf = 0.8
    if scores:
        # If sentiment is strong (high absolute value), confidence is higher
        avg_strength = sum(abs(s) for s in scores) / len(scores)
        curve_conf = round(min(1.0, 0.6 + avg_strength), 2)
        
    return {
        "turns": timeline_turns,
        "transitions": transitions,
        "summary": {
            "startLabel": start_label,
            "endLabel": end_label,
            "trend": trend,
            "transitionCount": len(transitions),
            "curveConfidence": curve_conf
        }
    }
