"""Analysis service — manages the full analysis pipeline."""

from __future__ import annotations

import csv
import json
import os
import re
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.aspect_sentiment.diarization import DiarizationResult, diarize_text
from src.aspect_sentiment.conversation_reconstruction import reconstruct_conversation
from src.aspect_sentiment.follow_up_alerts import (
    detect_follow_up_alerts,
    save_follow_up_alerts,
)
from src.aspect_sentiment.sentiment_timeline import compute_sentiment_timeline
from src.aspect_sentiment.analytics_engine import compute_conversation_analytics
from src.aspect_sentiment.llama_extraction import (
    derive_features,
    detect_conversation_stages,
    get_sentiment,
    process_text,
    rule_based_features,
    summarize_conversation,
)
from src.aspect_sentiment.privacy import (
    COMPANY_RX,
    CUSTOMER_PHONE_RX,
    EMAIL_RX,
    PHONE_RX,
    PrivacyResult,
    extract_and_redact_pii,
)
from src.aspect_sentiment.schemas import PipelineStage
from src.nexus_ai.core.paths import AUDIO_UPLOADS_DIR, ensure_runtime_dirs
from src.nexus_ai.repositories.sqlite import ConversationRepository
from src.ml.predictor import (
    CONVERSION_MODEL_PATH,
    MODEL_FEATURES_PATH,
    get_model_features,
    load_model_metrics,
    predict_with_trained_model,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
TRANSCRIPT_CSV_PATHS = [
    REPO_ROOT / "data" / "raw" / "transcripts.csv",
]
TRANSCRIPT_CSV_FIELDS = [
    "file_name", "text", "language", "duration_s", "timestamp",
    "products", "brands", "budget", "features", "intent",
    "decision_stage", "use_case", "objections", "sentiment",
    "confidence_score", "hesitation_score", "delay_flag",
    "conversion_label", "conversion_probability", "conversion_prediction",
    "model_accuracy", "model_precision", "model_recall", "model_f1",
    "xgboost_base_probability", "intent_score", "behavioral_score",
    "emotion_score", "engagement_score", "extraction_provider",
    "pii_redaction_count", "raw_features_json",
]
TRANSCRIPT_CSV_LOCK = threading.Lock()
CONVERSATION_REPOSITORY = ConversationRepository()

MONEY_CONTEXT_RX = re.compile(
    r"\b(?P<context>budget|salary|earning|income|pay|price|cost)\b"
    r"[^.?!]{0,80}?"
    r"(?P<currency>rs\.?|inr|₹)?\s*"
    r"(?<![A-Za-z])(?P<amount>[0-9][0-9,]*(?:\.\d+)?)"
    r"\s*(?P<suffix>k|lakh|lakhs)?"
    r"(?![\d,])"
    r"(?!\s*(?:gb|tb|ram|ssd|inch)\b)",
    re.IGNORECASE,
)
BUDGET_AMOUNT_RX = re.compile(
    r"\b(?:my\s+budget(?:\s+is)?|budget\s+(?:is|of)|"
    r"(?:hoping|want|need|trying)\s+to\s+(?:stay|keep\s+it)\s+(?:at|around|under|within)|"
    r"(?:stay|keep\s+it)\s+(?:at|around|under|within))"
    r"[^.?!]{0,30}?"
    r"(?P<currency>rs\.?|inr|₹)?\s*"
    r"(?<![A-Za-z])(?P<amount>[0-9][0-9,]*(?:\.\d+)?)"
    r"\s*(?P<suffix>k|lakh|lakhs)?"
    r"(?![\d,])"
    r"(?!\s*(?:gb|tb|ram|ssd|inch)\b)",
    re.IGNORECASE,
)
SELF_INTRO_RX = re.compile(
    r"\b(?i:my name is|i am|i'm|this is)\s+(?P<name>[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*){0,2})(?=\b|[.,!?])"
)
GREETING_RX = re.compile(
    r"\b(?:hi|hello|good morning|good afternoon)\s+(?P<name>[A-Z][A-Za-z]+)\b",
    re.IGNORECASE,
)
OCCUPATION_RX = re.compile(
    r"\b(?:i am|i'm|working as|work as)\s+(?:an?\s+)?"
    r"(?P<job>teacher|student|engineer|doctor|developer|manager|salesperson|consultant|designer)\b",
    re.IGNORECASE,
)
PRODUCT_NAME_TERMS = {
    "iphone", "samsung", "galaxy", "ultra", "pro", "max", "plus",
    "s25", "s24", "laptop", "phone", "mobile", "tv", "ac",
    "refrigerator", "washing", "machine",
}
NON_PERSON_NAME_TERMS = {
    "interested", "looking", "earning", "teacher", "student",
    "calling", "sure", "here", "product", "service",
    "proposal", "quotation", "pricing",
}


class AnalysisService:
    """Orchestrates the full analysis pipeline: diarization, PII, extraction,
    sentiment, scoring, follow-up alerts, and persistence."""

    # ------------------------------------------------------------------
    # Public helpers called by routes / worker
    # ------------------------------------------------------------------

    @staticmethod
    def bundled_ffmpeg_path() -> str | None:
        for ffmpeg_dir in REPO_ROOT.glob("ffmpeg-*"):
            candidate = ffmpeg_dir / "bin" / "ffmpeg.exe"
            if candidate.exists():
                return str(candidate)
        return shutil.which("ffmpeg")

    @staticmethod
    def get_transcriber() -> Any:
        _transcriber: Any | None = None

        def _inner() -> Any:
            nonlocal _transcriber
            if _transcriber is None:
                if os.getenv("USE_GROQ_WHISPER", "true").lower() == "true":
                    from src.aspect_sentiment.groq_audio import GroqCloudTranscriber
                    _transcriber = GroqCloudTranscriber()
                else:
                    from src.aspect_sentiment.audio import WhisperTranscriber
                    _transcriber = WhisperTranscriber()
            return _transcriber

        return _inner

    @staticmethod
    def completed_stage(id: str, title: str, detail: str) -> PipelineStage:
        return PipelineStage(id=id, title=title, status="completed", detail=detail)

    # ------------------------------------------------------------------
    # Analysis pipeline
    # ------------------------------------------------------------------

    @staticmethod
    def fallback_extraction(text: str) -> dict[str, Any]:
        features = rule_based_features(text)
        sentiment = get_sentiment(text)
        derived = derive_features(text, features)
        return {
            "raw_features": features,
            "sentiment_score": sentiment,
            **derived,
            "extraction_provider": "local-fallback",
        }

    @staticmethod
    def pii_payload(
        privacy: PrivacyResult,
        extra_entities: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        grouped: dict[str, list[str]] = {}
        unique_entities: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for entity in privacy.entities:
            key = (entity.type, str(entity.value).lower().strip())
            if key not in seen:
                seen.add(key)
                unique_entities.append({
                    "type": entity.type,
                    "value": entity.value,
                    "source": entity.source,
                    "start": entity.start,
                    "end": entity.end,
                })
                grouped.setdefault(entity.type, []).append(entity.value)

        for entity in extra_entities or []:
            key = (entity["type"], str(entity["value"]).lower().strip())
            if key not in seen:
                seen.add(key)
                unique_entities.append({
                    "type": entity["type"],
                    "value": entity["value"],
                    "source": entity.get("source", "local"),
                    "start": entity.get("start"),
                    "end": entity.get("end"),
                })
                grouped.setdefault(entity["type"], []).append(entity["value"])

        # Normalize phone aliases across grouped dictionary
        phone_values = []
        for alias in ("customer_number", "phone", "mobile", "contact_phone", "contact_number", "phone_number", "mobile_number"):
            for v in grouped.get(alias, []):
                if v and v not in phone_values:
                    phone_values.append(v)
        if phone_values:
            for alias in ("customer_number", "phone", "mobile", "contact_phone", "contact_number", "phone_number", "mobile_number"):
                grouped[alias] = list(dict.fromkeys(grouped.get(alias, []) + phone_values))

        return {
            "entities": unique_entities,
            "grouped": grouped,
            "redactionCount": privacy.redaction_count,
            "provider": privacy.provider,
        }

    @staticmethod
    def transcript_payload(diarization: DiarizationResult) -> list[dict[str, Any]]:
        return [
            {
                "speaker": turn.speaker,
                "rawSpeaker": turn.raw_speaker,
                "text": turn.text,
                "start": turn.start,
                "end": turn.end,
                "confidence": turn.confidence,
                "overlap": turn.overlap,
                "warnings": turn.warnings,
            }
            for turn in diarization.turns
        ]

    @staticmethod
    def summarize_customer_behavior(
        customer_text: str,
        extraction: dict[str, Any],
        conversation_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raw_features = extraction.get("raw_features", [])
        text_lower = customer_text.lower()
        
        # 1. Intent Signals
        intent_signals = sum(1 for f in raw_features if f.get("label") == "INTENT")
        buying_intent_terms = ["buy", "purchase", "want", "need", "looking for", "interested in"]
        intent_signals += sum(1 for term in buying_intent_terms if term in text_lower)
        
        # 2. Hesitation Score
        hesitation_score = extraction.get("hesitation_score", 0)
        if hesitation_score == 0:
            hesitation_terms = ["maybe", "thinking", "not sure", "later", "wait", "consider", "think about it"]
            hesitation_score = sum(1 for term in hesitation_terms if term in text_lower)
            
        # 3. Urgency Signals
        urgency_signals = sum(1 for f in raw_features if f.get("label") in ["URGENCY", "URGENCY_LEVEL"])
        urgency_terms = ["today", "tomorrow", "this week", "immediately", "urgent", "asap", "now"]
        urgency_signals += sum(1 for term in urgency_terms if term in text_lower)

        return {
            "focus": "customer-only",
            "intentSignals": intent_signals,
            "hesitationScore": hesitation_score,
            "urgencySignals": urgency_signals,
            "objectionSignals": len(
                [f for f in raw_features if f.get("label") == "OBJECTION"]
            ),
            "wordCount": len(customer_text.split()),
            "privacySafe": True,
        }

    @staticmethod
    def privacy_safe_csv_text(result: dict[str, Any], fallback_text: str) -> str:
        turns = result.get("diarizedTranscript")
        if isinstance(turns, list) and turns:
            safe_turns: list[str] = []
            for turn in turns:
                if not isinstance(turn, dict):
                    continue
                speaker = str(turn.get("speaker") or "Speaker")
                turn_text = str(turn.get("text") or "").strip()
                if not turn_text:
                    continue
                if speaker == "Customer":
                    turn_text = extract_and_redact_pii(turn_text).cleaned_text
                safe_turns.append(f"{speaker}: {turn_text}")
            if safe_turns:
                return " ".join(safe_turns)
        return str(result.get("customerBehavioralTranscript") or result.get("transcript") or fallback_text)

    async def run_pipeline(
        self,
        text: str,
        source_name: str,
        source_type: str,
        started: float,
        diarization: DiarizationResult | None = None,
        transcription_confidence: float | None = None,
        whisper_model: str | None = None,
        language: str | None = None,
    ) -> dict[str, Any]:
        """Execute the full analysis pipeline and return the response payload."""
        t_start_internal = time.perf_counter()
        
        t0 = time.perf_counter()
        diarized = diarization or diarize_text(text)
        reconstruction = reconstruct_conversation(diarized)
        t_diarization = (time.perf_counter() - t0) * 1000
        
        reconstructed_diarization = DiarizationResult(
            turns=reconstruction.turns,
            speaker_map=diarized.speaker_map,
            provider=f"{diarized.provider}+reconstructed",
            speaker_confidence=diarized.speaker_confidence,
            warnings=list(dict.fromkeys([*diarized.warnings, *reconstruction.metadata.warnings])),
        )
        customer_text = reconstructed_diarization.customer_text or text
        agent_text = reconstructed_diarization.agent_text
        privacy = extract_and_redact_pii(customer_text)
        local_entities = self.local_structured_entities(text, diarized)
        llama_text = privacy.cleaned_text

        t0 = time.perf_counter()
        extraction = await process_text(llama_text)
        if extraction is None:
            extraction = self.fallback_extraction(llama_text)
        extraction["privacy_redaction_count"] = privacy.redaction_count
        extraction["analysis_scope"] = "customer_only"
        conversation_summary = await summarize_conversation(
            transcript=" ".join(text.split()),
            customer_text=llama_text,
            agent_text=agent_text,
        )
        t_llama = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        prediction = predict_with_trained_model(extraction, llama_text, agent_text)
        t_xgb = (time.perf_counter() - t0) * 1000
        
        raw_features = extraction.get("raw_features", [])
        sentiment_score = float(extraction.get("sentiment_score", 0))

        audio_quality = None
        if transcription_confidence is not None:
            if transcription_confidence >= 0.82:
                quality_label = "Good"
            elif transcription_confidence >= 0.65:
                quality_label = "Fair"
            else:
                quality_label = "Poor"
            audio_quality = {
                "label": quality_label,
                "confidence": transcription_confidence,
                "language": language,
                "whisperModel": whisper_model,
            }

        def get_sentiment_label(score: float, txt: str) -> str:
            txt_lower = txt.lower()
            if any(w in txt_lower for w in ["confusing", "too many options", "don't know"]):
                return "Confused"
            if any(w in txt_lower for w in ["love", "amazing", "exactly what i need", "perfect"]):
                return "Emotionally Engaged"
            if any(w in txt_lower for w in ["maybe", "not sure", "thinking", "think about it"]):
                return "Hesitant"
            if score > 0.6:
                return "Very Positive"
            if score > 0.2:
                return "Positive"
            if score > 0.05:
                return "Mildly Positive"
            if score < -0.2:
                return "Negative"
            return "Neutral"

        dominant = get_sentiment_label(sentiment_score, llama_text)
        privacy_info = self.pii_payload(privacy, local_entities)
        detected_follow_ups = await detect_follow_up_alerts(
            customer_text=llama_text,
            diarization=diarized,
            privacy_payload=privacy_info,
        )
        follow_up_alerts = save_follow_up_alerts(
            detected_follow_ups,
            source_name=source_name,
            source_type=source_type,
        )

        products = [
            {
                "name": feature.get("name", ""),
                "entityType": feature.get("label", "FEATURE"),
                "sentiment": dominant,
                "score": sentiment_score,
                "confidence": extraction.get("confidence_score", 0.5),
                "mentions": 1,
                "context": feature.get("label", "Feature"),
            }
            for feature in raw_features
        ]

        partial_result = {
            "diarizationMetrics": diarized.metrics,
            "diarizedTranscript": self.transcript_payload(diarized),
            "reconstructedTranscript": self.transcript_payload(reconstructed_diarization),
            "conversationStages": detect_conversation_stages(reconstructed_diarization.turns),
            "sentimentTimeline": compute_sentiment_timeline(reconstructed_diarization.turns),
            "summary": {
                "positive": 100 if dominant == "positive" else 0,
                "negative": 100 if dominant == "negative" else 0,
                "neutral": 100 if dominant == "neutral" else 0,
                "dominant": dominant,
                "averageScore": sentiment_score,
                "totalProducts": len(raw_features),
            },
            "conversionScore": {
                "probability": prediction["probability"],
                "label": prediction["label"],
                "confidence": round(abs(prediction["probability"] - 0.5) * 2, 2),
                "features": extraction,
                "model": CONVERSION_MODEL_PATH.name,
                "explainability": prediction.get("explainability"),
                "decisionTrace": prediction.get("decisionTrace"),
            },
            "pipelineFeatures": extraction,
            "conversationSummary": conversation_summary,
            "rawFeatures": raw_features,
            "metadata": {
                "speakerConfidence": diarized.speaker_confidence,
            }
        }

        pipeline_latencies = {
            "vad_diarization_ms": round(max(1.0, t_diarization * 0.5), 2),
            "embeddings_ms": round(max(1.0, t_diarization * 0.3), 2),
            "classifier_ms": round(max(1.0, t_diarization * 0.2), 2),
            "llama_extraction_ms": round(max(1.0, t_llama), 2),
            "xgboost_prediction_ms": round(max(1.0, t_xgb), 2)
        }

        analytics = compute_conversation_analytics(partial_result, pipeline_latencies)

        return {
            "transcript": text,
            "diarizationMetrics": diarized.metrics,
            "diarizedTranscript": partial_result["diarizedTranscript"],
            "reconstructedTranscript": partial_result["reconstructedTranscript"],
            "conversationStages": partial_result["conversationStages"],
            "sentimentTimeline": partial_result["sentimentTimeline"],
            "analytics": analytics,
            "calibratedConfidence": analytics["calibratedConfidence"],
            "customerTranscript": customer_text,
            "customerBehavioralTranscript": llama_text,
            "agentTranscript": agent_text,
            "privacy": privacy_info,
            "followUpAlerts": follow_up_alerts,
            "customerBehaviorSummary": self.summarize_customer_behavior(llama_text, extraction, conversation_summary),
            "conversationSummary": conversation_summary,
            "normalizedText": " ".join(text.split()),
            "rawFeatures": raw_features,
            "pipelineFeatures": extraction,
            "products": products,
            "summary": partial_result["summary"],
            "conversionScore": partial_result["conversionScore"],
            "audioQuality": audio_quality,
            "prediction": prediction,
            "metadata": {
                "sourceType": source_type,
                "sourceName": source_name,
                "processingMs": int((time.perf_counter() - started) * 1000),
                "extractionProvider": extraction.get("extraction_provider", "llama"),
                "modelFeatures": len(get_model_features()),
                "diarizationProvider": diarized.provider,
                "speakerConfidence": diarized.speaker_confidence,
                "diarizationWarnings": diarized.warnings,
                "reconstruction": {
                    "confidence": reconstruction.metadata.confidence,
                    "warnings": reconstruction.metadata.warnings,
                    "fallbackUsed": reconstruction.metadata.fallback_used,
                    "modelUsed": reconstruction.metadata.model_used,
                    "processingMs": reconstruction.metadata.processing_time_ms,
                    "mergedFragments": reconstruction.metadata.merged_fragments,
                    "overlapTurns": reconstruction.metadata.overlap_turns,
                },
                "analysisScope": "customer_only_privacy_safe",
                "piiRedactionCount": privacy.redaction_count,
                "transcriptionConfidence": transcription_confidence,
                "whisperModel": whisper_model,
                "language": language,
            },
            "pipeline": [
                self.completed_stage("diarization", "Speaker diarization",
                                    f"Transcript separated with {diarized.provider}").model_dump(),
                self.completed_stage("reconstruction", "Conversation reconstruction",
                                    f"{reconstruction.metadata.merged_fragments} fragment(s) merged").model_dump(),
                self.completed_stage("privacy", "Local PII extraction",
                                    f"{privacy.redaction_count} sensitive item(s) redacted before LLaMA").model_dump(),
                self.completed_stage("llama", "Customer-only LLaMA extraction",
                                    "Structured sales features extracted from cleaned customer speech").model_dump(),
                self.completed_stage("follow-up-alerts", "Follow-up alert detection",
                                    f"{len(follow_up_alerts)} alert(s) saved").model_dump(),
                self.completed_stage("model", "Customer-weighted conversion model",
                                    "Hybrid conversion model executed").model_dump(),
            ],
        }

    # ------------------------------------------------------------------
    # Local entity extraction (regex-based, no ML)
    # ------------------------------------------------------------------

    @staticmethod
    def _valid_money_amount(amount: str, suffix: str | None, currency: str | None) -> bool:
        try:
            value = float(AnalysisService.normalize_money(amount, suffix))
        except ValueError:
            return False
        return value >= 100 or bool(suffix) or bool(currency)

    @staticmethod
    def normalize_money(amount: str, suffix: str | None = None) -> str:
        value = float(amount.replace(",", ""))
        suffix = (suffix or "").lower()
        if suffix == "k":
            value *= 1000
        elif suffix in {"lakh", "lakhs"}:
            value *= 100000
        return str(int(value)) if value.is_integer() else str(value)

    @staticmethod
    def _valid_person_name(value: str) -> bool:
        clean = value.strip().strip(".,!?")
        if not clean or any(ch.isdigit() for ch in clean):
            return False
        parts = [part.lower() for part in clean.split()]
        if any(part in NON_PERSON_NAME_TERMS or part in PRODUCT_NAME_TERMS for part in parts):
            return False
        return all(part[:1].isalpha() for part in parts)

    @staticmethod
    def _append_entity(
        entities: list[dict[str, Any]],
        entity_type: str,
        value: str,
        source: str,
    ) -> None:
        clean = value.strip().strip(".,!?")
        if not clean:
            return
        if entity_type in {"customer_name", "agent_name"} and not AnalysisService._valid_person_name(clean):
            return
        opposite_type = "agent_name" if entity_type == "customer_name" else "customer_name"
        if entity_type in {"customer_name", "agent_name"}:
            if any(
                item["type"] == opposite_type and item["value"].lower() == clean.lower()
                for item in entities
            ):
                return
        key = (entity_type, clean.lower())
        if key not in {(item["type"], item["value"].lower()) for item in entities}:
            entities.append({"type": entity_type, "value": clean, "source": source, "start": None, "end": None})

    @staticmethod
    def local_structured_entities(text: str, diarization: DiarizationResult) -> list[dict[str, Any]]:
        entities: list[dict[str, Any]] = []

        for match in BUDGET_AMOUNT_RX.finditer(text):
            if AnalysisService._valid_money_amount(
                match.group("amount"), match.group("suffix"), match.group("currency")
            ):
                AnalysisService._append_entity(
                    entities,
                    "budget",
                    AnalysisService.normalize_money(match.group("amount"), match.group("suffix")),
                    "local-regex",
                )

        for match in MONEY_CONTEXT_RX.finditer(text):
            context = match.group("context").lower()
            if not AnalysisService._valid_money_amount(
                match.group("amount"), match.group("suffix"), match.group("currency")
            ):
                continue
            amount = AnalysisService.normalize_money(match.group("amount"), match.group("suffix"))
            entity_type = (
                "budget"
                if context == "budget"
                else "product_price" if context in {"price", "cost"} else "income"
            )
            AnalysisService._append_entity(entities, entity_type, amount, "local-regex")

        for sentence in re.split(r"(?<=[.!?])\s+", text):
            lower = sentence.lower()
            if any(term in lower for term in ["earning", "income", "salary", "per month"]):
                for match in re.finditer(
                    r"(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(k|lakh|lakhs)?",
                    sentence,
                    re.IGNORECASE,
                ):
                    AnalysisService._append_entity(
                        entities,
                        "income",
                        AnalysisService.normalize_money(match.group(1), match.group(2)),
                        "local-regex",
                    )

        for turn in diarization.turns:
            if turn.speaker == "Customer":
                for match in SELF_INTRO_RX.finditer(turn.text):
                    candidate = match.group("name")
                    if candidate.lower() not in {
                        "looking", "earning", "teacher", "interested", "calling", "sure", "here"
                    }:
                        AnalysisService._append_entity(entities, "customer_name", candidate, "speaker-regex")
                for match in GREETING_RX.finditer(turn.text):
                    candidate = match.group("name")
                    if candidate.lower() not in {"sir", "madam", "maam", "ma'am", "there"}:
                        AnalysisService._append_entity(entities, "agent_name", candidate, "speaker-regex")
                for match in OCCUPATION_RX.finditer(turn.text):
                    AnalysisService._append_entity(entities, "job_title", match.group("job"), "speaker-regex")
            elif turn.speaker == "Agent":
                for match in SELF_INTRO_RX.finditer(turn.text):
                    candidate = match.group("name")
                    if candidate.lower() not in {"calling", "sure", "here", "just"}:
                        AnalysisService._append_entity(entities, "agent_name", candidate, "speaker-regex")
                for match in GREETING_RX.finditer(turn.text):
                    candidate = match.group("name")
                    if candidate.lower() not in {"sir", "madam", "maam", "ma'am", "there"}:
                        AnalysisService._append_entity(entities, "customer_name", candidate, "speaker-regex")

        # Fallback regex extraction for contact fields across full transcript
        for match in EMAIL_RX.finditer(text):
            AnalysisService._append_entity(entities, "email", match.group(0).strip(), "local-regex")

        for match in CUSTOMER_PHONE_RX.finditer(text):
            val = match.group(1).strip() if match.lastindex else match.group(0).strip()
            AnalysisService._append_entity(entities, "customer_number", val, "local-regex")

        for match in PHONE_RX.finditer(text):
            val = match.group(1).strip() if match.lastindex else match.group(0).strip()
            AnalysisService._append_entity(entities, "phone", val, "local-regex")

        for match in COMPANY_RX.finditer(text):
            val = match.group(1).strip() if match.lastindex else match.group(0).strip()
            AnalysisService._append_entity(entities, "company_name", val, "local-regex")

        return entities

    # ------------------------------------------------------------------
    # CSV persistence
    # ------------------------------------------------------------------

    @staticmethod
    def _csv_join(values: list[str]) -> str:
        unique = []
        for value in values:
            clean = str(value or "").strip()
            if clean and clean.lower() not in {item.lower() for item in unique}:
                unique.append(clean)
        return ", ".join(unique)

    @staticmethod
    def csv_feature_columns(result: dict[str, Any]) -> dict[str, Any]:
        raw_features = result.get("rawFeatures")
        if not isinstance(raw_features, list):
            raw_features = []

        by_label: dict[str, list[str]] = {}
        for feature in raw_features:
            if not isinstance(feature, dict):
                continue
            label = str(feature.get("label") or "FEATURE").upper()
            value = str(feature.get("name") or feature.get("value") or "").strip()
            if value:
                by_label.setdefault(label, []).append(value)

        pipeline_features = result.get("pipelineFeatures") if isinstance(result.get("pipelineFeatures"), dict) else {}
        summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
        conversion = result.get("conversionScore") if isinstance(result.get("conversionScore"), dict) else {}
        prediction = result.get("prediction") if isinstance(result.get("prediction"), dict) else {}
        debug_metrics = prediction.get("debug_metrics") if isinstance(prediction.get("debug_metrics"), dict) else {}
        metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
        model_metrics = load_model_metrics()

        return {
            "products": AnalysisService._csv_join(by_label.get("PRODUCT", [])),
            "brands": AnalysisService._csv_join(by_label.get("BRAND", [])),
            "budget": AnalysisService._csv_join(by_label.get("BUDGET", [])),
            "features": AnalysisService._csv_join(by_label.get("FEATURE", [])),
            "intent": AnalysisService._csv_join(by_label.get("INTENT", [])),
            "decision_stage": AnalysisService._csv_join(by_label.get("DECISION_STAGE", [])),
            "use_case": AnalysisService._csv_join(by_label.get("USE_CASE", [])),
            "objections": AnalysisService._csv_join(by_label.get("OBJECTION", []) + by_label.get("OBJECTION_TYPE", [])),
            "sentiment": summary.get("dominant", ""),
            "confidence_score": pipeline_features.get("confidence_score", ""),
            "hesitation_score": pipeline_features.get("hesitation_score", ""),
            "delay_flag": pipeline_features.get("delay_flag", ""),
            "conversion_label": conversion.get("label", ""),
            "conversion_probability": conversion.get("probability", ""),
            "conversion_prediction": prediction.get("prediction", ""),
            "model_accuracy": model_metrics.get("accuracy", ""),
            "model_precision": model_metrics.get("precision", ""),
            "model_recall": model_metrics.get("recall", ""),
            "model_f1": model_metrics.get("f1", ""),
            "xgboost_base_probability": debug_metrics.get("xgboost_base", ""),
            "intent_score": debug_metrics.get("intent_score", ""),
            "behavioral_score": debug_metrics.get("behavioral_score_scaled", ""),
            "emotion_score": debug_metrics.get("emotion_score", ""),
            "engagement_score": debug_metrics.get("engagement_score", ""),
            "extraction_provider": metadata.get(
                "extractionProvider", pipeline_features.get("extraction_provider", "")
            ),
            "pii_redaction_count": metadata.get(
                "piiRedactionCount", pipeline_features.get("privacy_redaction_count", "")
            ),
            "raw_features_json": json.dumps(raw_features, ensure_ascii=True),
        }

    @staticmethod
    def ensure_transcript_csv_schema(csv_path: Path) -> None:
        if not csv_path.exists() or csv_path.stat().st_size == 0:
            return
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames == TRANSCRIPT_CSV_FIELDS:
                return
            rows = list(reader)
        upgraded_rows = [
            {field: row.get(field, "") for field in TRANSCRIPT_CSV_FIELDS} for row in rows
        ]
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TRANSCRIPT_CSV_FIELDS)
            writer.writeheader()
            writer.writerows(upgraded_rows)

    def append_transcript_csv(
        self,
        *,
        source_name: str,
        text: str,
        result: dict[str, Any] | None = None,
        language: str | None = None,
        duration_s: float | None = None,
    ) -> None:
        cleaned_text = " ".join(text.split())
        if not cleaned_text:
            return

        row = {
            "file_name": source_name,
            "text": cleaned_text,
            "language": language or "",
            "duration_s": duration_s if duration_s is not None else "",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            **self.csv_feature_columns(result or {}),
        }

        with TRANSCRIPT_CSV_LOCK:
            for csv_path in TRANSCRIPT_CSV_PATHS:
                csv_path.parent.mkdir(parents=True, exist_ok=True)
                self.ensure_transcript_csv_schema(csv_path)
                needs_header = not csv_path.exists() or csv_path.stat().st_size == 0
                with csv_path.open("a", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=TRANSCRIPT_CSV_FIELDS)
                    if needs_header:
                        writer.writeheader()
                    writer.writerow(row)

    def append_transcript_sqlite(
        self,
        *,
        source_name: str,
        source_type: str,
        text: str,
        result: dict[str, Any] | None = None,
        language: str | None = None,
        duration_s: float | None = None,
    ) -> None:
        cleaned_text = " ".join(text.split())
        if not cleaned_text:
            return

        created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        CONVERSATION_REPOSITORY.create(
            conversation_id=str(uuid.uuid4()),
            source_name=source_name,
            source_type=source_type,
            transcript=cleaned_text,
            language=language,
            duration_s=duration_s,
            metadata={
                "summary": (result or {}).get("summary", {}),
                "conversionScore": (result or {}).get("conversionScore", {}),
                "pipelineFeatures": (result or {}).get("pipelineFeatures", {}),
            },
            created_at=created_at,
        )

    @staticmethod
    def explain_prediction(row: Any) -> list[str]:
        def value(column: str, default: int | float = 0) -> int | float:
            if column not in row.columns:
                return default
            return row[column].values[0]

        reasons: list[str] = []
        if value("confidence_score") > 0.6:
            reasons.append("Customer shows buying intent")
        if value("hesitation_score") >= 2:
            reasons.append("Customer is hesitant")
        if value("delay_flag") == 1:
            reasons.append("Customer postponed decision")
        if value("sentiment_score") > 0.3:
            reasons.append("Positive sentiment")
        if not reasons:
            reasons.append("Limited buying signals detected")
        return reasons


# Module-level convenience instance
analysis_service = AnalysisService()
