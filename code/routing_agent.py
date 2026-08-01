import os
import json
from config import WEIGHTS, THRESHOLDS
from utils import get_logger, retry_api
import google.generativeai as genai

logger = get_logger("RoutingAgent")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

class RoutingAgent:
    def __init__(self, retrieval_engine, safety_engine):
        self.retrieval = retrieval_engine
        self.safety = safety_engine

    def compute_priority_score(self, context):
        """Computes a dynamic priority score from 0.0 (mute) to 1.0 (notify)."""
        score = 0.50  # Neutral baseline
        
        msg = context["message"]
        user_stats = context.get("user_stats") or {}
        biz_ctx = context.get("business_context") or {}
        grp_ctx = context.get("group_context") or {}
        daily_load = context.get("daily_load", 0)

        # 1. Conversation type weighting
        if msg.get("conversation_type") == "personal":
            score += WEIGHTS["conversation_personal"]
            
        # Apply reply rate / dismissal rate adjustments
        reply_rate = user_stats.get("reply_rate", 0.0)
        dismiss_rate = user_stats.get("dismissal_rate", 0.0)
        
        score += reply_rate * WEIGHTS["reply_rate_multiplier"]
        score += dismiss_rate * WEIGHTS["dismissal_rate_penalty"]

        # 2. Business Account Relationship
        biz_hist = biz_ctx.get("user_history") or {}
        if biz_hist:
            if biz_hist.get("has_opted_out"):
                score += WEIGHTS["opt_out_penalty"]
            dismissals = biz_hist.get("dismissed_count", 0)
            if dismissals > 2:
                score -= min(0.30, dismissals * 0.10)
            if biz_hist.get("recent_orders_count", 0) > 0 or biz_hist.get("recent_payments_count", 0) > 0:
                score += WEIGHTS["has_recent_interactions"]

        # 3. Frequently Forwarded Penalty
        fwd_count = msg.get("forwarded_count", 0)
        if fwd_count > 0:
            score -= min(0.35, fwd_count * 0.08)

        # 4. Notification Fatigue / DND / Quiet Hours Adjustment
        if daily_load > 40:
            score += WEIGHTS["high_daily_load_penalty"]
        if context.get("dnd_active"):
            score -= 0.20  # Additional DND dampening for non-essential notifications

        return max(0.0, min(1.0, score))

    def route(self, context):
        msg = context["message"]
        user_id = msg["user_id"]
        msg_text = str(msg.get("message_text", "") or "").strip()
        media_text = str(context.get("media_text", "") or "").strip()
        full_text = f"{msg_text} {media_text}".strip()

        evidence_ids = self.retrieval.find_evidence(msg, user_id, top_k=2)

        # 1. Run Safety Guardrails First
        safety_decision = self.safety.evaluate(context)
        if safety_decision:
            safety_decision["evidence_message_ids"] = evidence_ids
            return safety_decision

        # 2. Edge Case: Empty Text & Missing Media
        if not full_text:
            return {
                "action": "digest",
                "message_type": "unknown",
                "reason": "Message contains empty text and no media transcript.",
                "confidence": 0.50,
                "evidence_message_ids": evidence_ids
            }

        # 3. Dynamic LLM Reasoning & Context Analysis if Gemini API Key is available
        if GEMINI_API_KEY:
            from config import DEBUG_GEMINI
            if DEBUG_GEMINI:
                print(f"[DEBUG GEMINI] Routing message: {full_text[:100]}...")
                llm_decision = self._route_llm(full_text, context)
                print(f"[DEBUG GEMINI] Route decision: {llm_decision}")
                if llm_decision and isinstance(llm_decision, dict) and "action" in llm_decision and "message_type" in llm_decision:
                    llm_decision["evidence_message_ids"] = evidence_ids
                    try:
                        llm_decision["confidence"] = round(float(llm_decision.get("confidence", 0.80)), 2)
                    except ValueError:
                        llm_decision["confidence"] = 0.80
                    return llm_decision
            else:
                try:
                    llm_decision = self._route_llm(full_text, context)
                    if llm_decision and isinstance(llm_decision, dict) and "action" in llm_decision and "message_type" in llm_decision:
                        llm_decision["evidence_message_ids"] = evidence_ids
                        # Ensure confidence and format matches schema
                        try:
                            llm_decision["confidence"] = round(float(llm_decision.get("confidence", 0.80)), 2)
                        except ValueError:
                            llm_decision["confidence"] = 0.80
                        return llm_decision
                except Exception as e:
                    logger.warning(f"Failed to use LLM routing decision: {e}. Falling back to local scoring engine.")

        # 4. Fallback Dynamic Scoring Mode (Config-driven)
        priority_score = self.compute_priority_score(context)

        # Fallback keyword checks for high-priority payment / urgent signals
        lower_full_text = full_text.lower()
        if any(term in lower_full_text for term in ["otp", "verification code", "credited", "debited", "paid"]):
            return {
                "action": "notify",
                "message_type": "payment",
                "reason": "High-priority financial or authentication trigger.",
                "confidence": 0.95,
                "evidence_message_ids": evidence_ids
            }

        if any(term in lower_full_text for term in ["urgent", "emergency", "asap", "call me now"]):
            return {
                "action": "notify",
                "message_type": "urgent",
                "reason": "Time-sensitive keyword detected in text/media transcript.",
                "confidence": 0.92,
                "evidence_message_ids": evidence_ids
            }

        if priority_score >= THRESHOLDS["notify"]:
            action = "notify"
            m_type = "personal" if msg.get("conversation_type") == "personal" else "business_update"
            reason = "High contextual priority and user engagement score."
        elif priority_score <= THRESHOLDS["digest"]:
            action = "mute"
            m_type = "promotion" if msg.get("conversation_type") == "business" else "forward"
            reason = "Low priority score due to history of dismissals or high forwarding."
        else:
            action = "digest"
            m_type = "promotion" if "sale" in lower_full_text or "off" in lower_full_text else "business_update"
            if msg.get("forwarded_count", 0) > 2:
                m_type = "forward"
            reason = "Standard notification batched into daily digest."

        return {
            "action": action,
            "message_type": m_type,
            "reason": reason,
            "confidence": round(priority_score, 2),
            "evidence_message_ids": evidence_ids
        }

    @retry_api(max_retries=3, delay=1.0)
    def _route_llm(self, text, context):
        """Invoke Gemini 1.5 Flash to perform contextual and personalized routing."""
        try:
            from config import MODEL_NAME
            model = genai.GenerativeModel(MODEL_NAME)
            
            # Formulate user preference profile to contextualize
            user_stats = context.get("user_stats") or {}
            msg = context["message"]
            
            user_context = (
                f"User stats: reply_rate={user_stats.get('reply_rate', 0)}, "
                f"dismissal_rate={user_stats.get('dismissal_rate', 0)}. "
                f"Conversation type: {context.get('conversation_type')}. "
                f"Is DND active for user right now? {context.get('dnd_active')}. "
                f"Forwarded count: {msg.get('forwarded_count', 0)}."
            )

            prompt = (
                f"You are an AI WhatsApp Notification Router. Decide the best routing action for this message:\n"
                f"1. notify: interrupt the user now (only for urgent updates, same-day events, direct user questions, payments, OTPs, or immediate family/work updates).\n"
                f"2. digest: batch for later (for standard group updates, greetings, coupons/promotions user likes, cinema tickets, general business updates).\n"
                f"3. mute: suppress low-value notifications, spam, unwanted promotions, repeatedly forwarded chains.\n\n"
                f"User Profile Context:\n{user_context}\n\n"
                f"Message Content:\n\"{text}\"\n\n"
                f"Allowed message_type values:\n"
                f"['personal', 'urgent', 'event', 'payment', 'business_update', 'promotion', 'greeting', 'forward', 'spam', 'scam', 'unknown']\n\n"
                f"Return JSON format matching the schema exactly:\n"
                f"{{\n"
                f"  \"action\": \"notify\" | \"digest\" | \"mute\",\n"
                f"  \"message_type\": \"...\",\n"
                f"  \"reason\": \"...\",\n"
                f"  \"confidence\": 0.0 to 1.0\n"
                f"}}\n"
            )
            
            response = model.generate_content(prompt)
            raw_text = response.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()
            return json.loads(raw_text)
        except Exception as e:
            logger.error(f"Error performing LLM routing decision: {e}")
            return None