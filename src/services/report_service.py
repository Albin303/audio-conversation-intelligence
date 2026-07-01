"""Report service — generates conversation reports."""

from __future__ import annotations

from typing import Any

from src.nexus_ai.repositories.sqlite import JobRepository


class ReportService:
    """Generates reports from job results."""

    def __init__(self) -> None:
        self.job_repository = JobRepository()

    def get_report(self, job_id: str) -> dict[str, Any] | None:
        """Return the stored result for a completed job."""
        persisted = self.job_repository.get(job_id)
        if persisted and persisted.get("status") == "completed":
            return persisted.get("result")
        return None

    def generate_report(self, job_id: str) -> dict[str, Any] | None:
        """
        Compiles a comprehensive structured report containing:
        - Executive Summary
        - Profile
        - Objections
        - Timeline
        - Stage Detection
        - Decision Trace
        - Conversation Quality Score & Analytics
        - Exportable Text Format
        """
        result = self.get_report(job_id)
        if not result:
            return None
            
        conv_summary = result.get("conversationSummary", {})
        conversion_score = result.get("conversionScore", {})
        explainability = conversion_score.get("explainability", {})
        decision_trace = conversion_score.get("decisionTrace", {})
        raw_features = result.get("rawFeatures", [])
        stages = result.get("conversationStages", [])
        timeline = result.get("sentimentTimeline", {})
        analytics = result.get("analytics", {})
        
        # 1. Executive Summary
        exec_summary = {
            "overview": conv_summary.get("overview", "No summary available."),
            "customerNeed": conv_summary.get("customerNeed", "No customer need identified."),
            "keyPoints": conv_summary.get("keyPoints", []),
            "outcome": conv_summary.get("outcome", "Pending decision."),
            "nextAction": conv_summary.get("nextAction", "No follow-up action specified."),
            "recommendation": explainability.get("Recommendation", "No recommendation provided.")
        }
        
        # 2. Customer Profile
        privacy = result.get("privacy", {})
        grouped_entities = privacy.get("grouped", {})
        customer_name = grouped_entities.get("customer_name", ["Unknown"])[0] if grouped_entities.get("customer_name") else "Unknown"
        agent_name = grouped_entities.get("agent_name", ["Unknown"])[0] if grouped_entities.get("agent_name") else "Unknown"
        job_title = grouped_entities.get("job_title", ["Not Specified"])[0] if grouped_entities.get("job_title") else "Not Specified"
        budget = grouped_entities.get("budget", ["Not Mentioned"])[0] if grouped_entities.get("budget") else "Not Mentioned"
        
        profile = {
            "customerName": customer_name,
            "agentName": agent_name,
            "jobTitle": job_title,
            "budget": budget,
            "leadScore": explainability.get("Lead Score", 50.0),
            "leadPriority": analytics.get("followUpPriority", "Medium")
        }
        
        # 3. Objections
        objections = [f.get("value") for f in raw_features if f.get("label") == "OBJECTION"]
        objection_details = {
            "totalObjections": len(objections),
            "list": objections,
            "riskScore": analytics.get("riskScore", 0.0)
        }
        
        # 4. Text Exportable formatting (markdown / plain text report)
        markdown_report = f"""# SPEECH INTELLIGENCE AND INTENT DETECTION CONVERSATION ANALYSIS REPORT
## JOB ID: {job_id}

### 1. EXECUTIVE SUMMARY
- **Overview**: {exec_summary["overview"]}
- **Customer Need**: {exec_summary["customerNeed"]}
- **Predicted Outcome**: {exec_summary["outcome"]}
- **Lead Score**: {profile["leadScore"]}% ({profile["leadPriority"]} Priority)
- **Next Action**: {exec_summary["nextAction"]}
- **AI Recommendation**: {exec_summary["recommendation"]}

### 2. CUSTOMER PROFILE
- **Customer Name**: {profile["customerName"]}
- **Agent Name**: {profile["agentName"]}
- **Job Title**: {profile["jobTitle"]}
- **Budget**: {profile["budget"]}

### 3. OBJECTIONS & RISKS
- **Total Objections**: {objection_details["totalObjections"]}
- **Objections List**: {", ".join(objections) if objections else "None"}
- **Calculated Risk Score**: {objection_details["riskScore"] * 100}%

### 4. CONVERSATION STAGES
"""
        for s in stages:
            markdown_report += f"- **Stage: {s.get('stage')}** ({s.get('startTime')}s to {s.get('endTime')}s, Confidence: {s.get('confidence')})\n"
            
        markdown_report += "\n### 5. SENTIMENT TIMELINE SUMMARY\n"
        markdown_report += f"- **Start Sentiment**: {timeline.get('summary', {}).get('startLabel', 'Neutral')}\n"
        markdown_report += f"- **End Sentiment**: {timeline.get('summary', {}).get('endLabel', 'Neutral')}\n"
        markdown_report += f"- **Overall Trend**: {timeline.get('summary', {}).get('trend', 'Stable')}\n"
        markdown_report += f"- **Curve Confidence**: {timeline.get('summary', {}).get('curveConfidence', 1.0) * 100}%\n"

        markdown_report += "\n### 6. AI DECISION TRACE (EXPLAINABILITY AUDIT)\n"
        markdown_report += f"- **XGBoost Base Contribution**: {decision_trace.get('contributions', {}).get('xgboost_contribution', 0.0)}\n"
        markdown_report += f"- **Behavioral Contribution**: {decision_trace.get('contributions', {}).get('behavioral_contribution', 0.0)}\n"
        markdown_report += f"- **Intent Contribution**: {decision_trace.get('contributions', {}).get('intent_contribution', 0.0)}\n"
        markdown_report += f"- **Emotion Contribution**: {decision_trace.get('contributions', {}).get('emotion_contribution', 0.0)}\n"
        markdown_report += f"- **Engagement Contribution**: {decision_trace.get('contributions', {}).get('engagement_contribution', 0.0)}\n"
        markdown_report += f"- **Formula Used**: `{decision_trace.get('formula')}`\n"
        
        return {
            "jobId": job_id,
            "execSummary": exec_summary,
            "profile": profile,
            "objections": objection_details,
            "stages": stages,
            "timeline": timeline,
            "analytics": analytics,
            "decisionTrace": decision_trace,
            "exportableText": markdown_report.strip()
        }


report_service = ReportService()
