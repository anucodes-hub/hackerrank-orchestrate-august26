import os
import time
from schemas import map_level_to_action, UnifiedContext
from learning_store import LearningStore
from agents.input_router_agent import InputRouterAgent
from agents.personalization_agent import UserPersonalizationAgent
from agents.business_trust_agent import BusinessTrustAgent
from agents.continuity_agent import ConversationContinuityAgent
from agents.fatigue_agent import NotificationFatigueAgent
from agents.decision_agent import DecisionAgent
from agents.explanation_agent import ExplanationAgent
from scoring_engine import ScoringEngine
from observability import metrics_collector
from utils import get_logger

logger = get_logger("RoutingAgent")

class RoutingAgent:
    """Master Orchestrator binding specialized agents and core services into a unified AI system."""
    def __init__(self, retrieval_engine, safety_engine):
        self.retrieval_engine = retrieval_engine
        self.safety_engine = safety_engine
        self.scoring_engine = ScoringEngine()
        self.learning_store = LearningStore()

        # Specialized Agent Network
        self.input_router = InputRouterAgent()
        self.personalization_agent = UserPersonalizationAgent(self.learning_store)
        self.business_trust_agent = BusinessTrustAgent()
        self.continuity_agent = ConversationContinuityAgent()
        self.fatigue_agent = NotificationFatigueAgent()
        self.decision_agent = DecisionAgent()
        self.explanation_agent = ExplanationAgent()

    def route(self, raw_context: dict) -> dict:
        msg = raw_context["message"]
        cb_ref = raw_context.get("context_builder_ref")
        
        # 1. Payload Routing & Multimodal Signals Extraction
        multimodal_signals = self.input_router.process(msg, cb_ref)

        # 2. Directly Assemble Strongly-Typed UnifiedContext
        unified_ctx: UnifiedContext = cb_ref.build_context(msg, multimodal_signals)

        # 3. Multi-Agent Evaluation & Voting
        safety_vote = self.safety_engine.evaluate_vote(unified_ctx)
        retrieval_vote = self.retrieval_engine.evaluate_vote(unified_ctx)
        pers_vote = self.personalization_agent.evaluate(unified_ctx)
        biz_vote = self.business_trust_agent.evaluate(unified_ctx)
        cont_vote = self.continuity_agent.evaluate(unified_ctx)
        fatigue_vote = self.fatigue_agent.evaluate(unified_ctx)
        prio_vote = self.scoring_engine.evaluate_vote(unified_ctx, retrieval_vote)

        agent_votes = [
            safety_vote,
            retrieval_vote,
            pers_vote,
            biz_vote,
            cont_vote,
            fatigue_vote,
            prio_vote
        ]

        # 4. Agent Confidence Voting & Contradiction Resolution
        decision = self.decision_agent.decide(unified_ctx, agent_votes)

        # 5. Explainable Reasoning Generation
        decision.reason = self.explanation_agent.explain(decision, unified_ctx)

        # 6. Observability Logging
        metrics_collector.record_decision(
            action=decision.action,
            message_type=decision.message_type,
            confidence=decision.confidence,
            safety_trigger=safety_vote.signals.get("threat_type") if safety_vote.signals.get("safety_override") else None
        )

        return {
            "message_id": decision.message_id,
            "action": decision.action,
            "message_type": decision.message_type,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "evidence_message_ids": decision.evidence_message_ids
        }