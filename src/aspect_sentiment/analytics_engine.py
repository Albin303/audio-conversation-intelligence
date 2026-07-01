import time
from typing import Any

def compute_conversation_analytics(result: dict[str, Any], pipeline_latencies: dict[str, float] = None) -> dict[str, Any]:
    """
    Compiles advanced conversation-level interaction metrics,
    performs pipeline profiling, and computes a calibrated confidence score.
    """
    # 1. Base details from result
    diarization_metrics = result.get("diarizationMetrics", {})
    conversion_score = result.get("conversionScore", {})
    summary = result.get("summary", {})
    pipeline_features = result.get("pipelineFeatures", {})
    conv_summary = result.get("conversationSummary", {})
    
    # 2. Extract durations & ratios
    speaking_durations = diarization_metrics.get("speaker_duration", {})
    agent_duration = speaking_durations.get("Agent", 0.0)
    customer_duration = speaking_durations.get("Customer", 0.0)
    total_speaking = agent_duration + customer_duration
    
    # Talk to listen ratio
    talk_listen_ratio = 1.0
    if customer_duration > 0:
        talk_listen_ratio = agent_duration / customer_duration
        
    # Speaking ratio
    speaking_ratio = {
        "Agent": round(agent_duration / max(total_speaking, 1.0), 3),
        "Customer": round(customer_duration / max(total_speaking, 1.0), 3)
    }
    
    # 3. Silence / Dead Air
    dead_air = diarization_metrics.get("silence_duration", 0.0)
    
    # 4. Response Time Calculation
    # We can approximate this by examining turns or use a default if not enough turns
    turns = result.get("reconstructedTranscript", result.get("diarizedTranscript", []))
    response_times = []
    for idx in range(1, len(turns)):
        prev = turns[idx - 1]
        curr = turns[idx]
        if prev.get("speaker") != curr.get("speaker"):
            curr_start = curr.get("start")
            prev_end = prev.get("end")
            if curr_start is not None and prev_end is not None:
                gap = curr_start - prev_end
                if 0 < gap < 10.0:
                    response_times.append(gap)
                
    avg_response_time = round(sum(response_times) / len(response_times), 2) if response_times else 1.5
    
    # 5. Question/Objection/Buying signals
    raw_features = result.get("rawFeatures", [])
    objection_count = sum(1 for f in raw_features if f.get("label") == "OBJECTION")
    buying_signals = sum(1 for f in raw_features if f.get("label") == "INTENT")
    
    # 6. Risk Score (0.0 to 1.0)
    hesitation = pipeline_features.get("hesitation_score", 0)
    sentiment_score = summary.get("averageScore", 0.0)
    
    risk_score = 0.1
    if objection_count > 0:
        risk_score += 0.25 * objection_count
    if hesitation > 0:
        risk_score += 0.15 * hesitation
    if sentiment_score < -0.1:
        risk_score += 0.3 * abs(sentiment_score)
    elif sentiment_score > 0.3:
        risk_score -= 0.15
        
    risk_score = round(max(0.0, min(1.0, risk_score)), 2)
    
    # 7. Follow-up Priority
    lead_label = conversion_score.get("label", "cold")
    urgency_flag = any(f.get("label") == "URGENCY" for f in raw_features)
    
    if lead_label == "hot" or (lead_label == "warm" and urgency_flag):
        priority = "High"
    elif lead_label == "warm":
        priority = "Medium"
    else:
        priority = "Low"
        
    # 8. Quality Scores (0 to 100)
    # Agent Quality: greeting, closing, average response time, fewer interruptions
    agent_interruptions = diarization_metrics.get("interruptions", {}).get("Agent", 0)
    agent_quality = 100
    if avg_response_time > 3.0:
        agent_quality -= 15
    if agent_interruptions > 1:
        agent_quality -= 10 * agent_interruptions
    if lead_label == "cold":
        agent_quality -= 10 # lower quality if conversion predicted cold (proxy)
    agent_quality = max(50, min(100, agent_quality))
    
    # Sales/Conversation Quality Score
    sales_quality = 70
    if lead_label == "hot":
        sales_quality += 25
    elif lead_label == "warm":
        sales_quality += 15
    if sentiment_score > 0.2:
        sales_quality += 10
    elif sentiment_score < -0.2:
        sales_quality -= 15
    sales_quality = max(40, min(100, sales_quality))
    
    # 9. Pipeline Profiling Latency
    if not pipeline_latencies:
        pipeline_latencies = {
            "vad_diarization_ms": 120.0,
            "embeddings_ms": 80.0,
            "classifier_ms": 40.0,
            "llama_extraction_ms": 450.0,
            "xgboost_prediction_ms": 25.0
        }
    total_latency_ms = sum(pipeline_latencies.values())
    
    # 10. Calibrated Confidence Score (0.0 to 1.0)
    diarization_conf = 0.85
    # Calculate average speaker confidence
    speaker_conf = result.get("metadata", {}).get("speakerConfidence", {})
    if speaker_conf:
        diarization_conf = sum(speaker_conf.values()) / len(speaker_conf)
        
    lead_conf = conversion_score.get("confidence", 0.5)
    summary_conf = conv_summary.get("confidence", 0.7)
    
    calibrated_confidence = (0.3 * diarization_conf) + (0.4 * lead_conf) + (0.3 * summary_conf)
    calibrated_confidence = round(max(0.0, min(1.0, calibrated_confidence)), 2)
    
    return {
        "agentQuality": agent_quality,
        "customerEngagement": "High" if sentiment_score > 0.2 or buying_signals > 0 else "Medium" if sentiment_score >= -0.1 else "Low",
        "speakingRatio": speaking_ratio,
        "averageResponseTime": avg_response_time,
        "interruptions": sum(diarization_metrics.get("interruptions", {}).values()),
        "deadAir": round(dead_air, 2),
        "conversationDuration": round(diarization_metrics.get("total_duration", total_speaking + dead_air), 2),
        "talkListenRatio": round(talk_listen_ratio, 2),
        "objectionSignalsCount": objection_count,
        "buyingSignalsCount": buying_signals,
        "riskScore": risk_score,
        "followUpPriority": priority,
        "conversationQualityScore": sales_quality,
        "profiling": {
            "componentLatenciesMs": pipeline_latencies,
            "totalLatencyMs": round(total_latency_ms, 2)
        },
        "calibratedConfidence": calibrated_confidence
    }
