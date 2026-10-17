"""
Bridge between Django operational models and the Data Platform (Kafka & Spark Lakehouse).
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .streaming.producer import KafkaProducer
from .streaming.contracts import registry
from .streaming.broker import broker
from .lakehouse.runner import pipeline_runner

producer = KafkaProducer(broker_instance=broker, contract_registry=registry)


def publish_payment_event(payment, event_type: str = "payment.received") -> Optional[Any]:
    """Publishes a payment event to Kafka topic collections.payments."""
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        if event_type == "payment.received":
            pay_date = getattr(payment, 'date', getattr(payment, 'payment_date', None))
            occurred = pay_date.isoformat() if hasattr(pay_date, 'isoformat') else str(pay_date or now_iso)
            idemp_key = getattr(payment, "event_id", getattr(payment, "idempotency_key", f"idemp-{uuid.uuid4().hex[:8]}"))
            payload = {
                "eventId": f"evt-{uuid.uuid4().hex[:12]}",
                "eventType": "payment.received",
                "occurredAt": occurred,
                "ingestedAt": now_iso,
                "sourceSystem": "payment-ledger",
                "correlationId": f"corr-{uuid.uuid4().hex[:8]}",
                "accountId": str(getattr(payment, 'account_id', payment.get('account_id') if isinstance(payment, dict) else 'acct-1001')),
                "amount": float(getattr(payment, 'amount', payment.get('amount', 0.0) if isinstance(payment, dict) else 0.0)),
                "currency": getattr(payment, "currency", "CAD"),
                "idempotencyKey": str(idemp_key)
            }
        else:
            payload = {
                "eventId": f"evt-{uuid.uuid4().hex[:12]}",
                "eventType": "payment.reversed",
                "occurredAt": now_iso,
                "ingestedAt": now_iso,
                "sourceSystem": "payment-ledger",
                "correlationId": f"corr-{uuid.uuid4().hex[:8]}",
                "paymentId": str(getattr(payment, "id", payment)),
                "reason": "NSF_INSUFFICIENT_FUNDS"
            }
        return producer.send(payload, key=payload.get("accountId") or payload.get("paymentId"))
    except Exception as e:
        print(f"[Kafka Warning] Failed to publish {event_type}: {e}")
        return None


def publish_promise_event(promise, event_type: str = "promise.created") -> Optional[Any]:
    """Publishes a promise-to-pay event to Kafka topic collections.promises."""
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        if event_type == "promise.created":
            payload = {
                "eventId": f"evt-{uuid.uuid4().hex[:12]}",
                "eventType": "promise.created",
                "occurredAt": now_iso,
                "ingestedAt": now_iso,
                "sourceSystem": "promise-tracking",
                "correlationId": f"corr-{uuid.uuid4().hex[:8]}",
                "accountId": str(getattr(promise, "account_id", promise.get("account_id") if isinstance(promise, dict) else "acct-1001")),
                "dueDate": str(getattr(promise, "due_date", promise.get("due_date") if isinstance(promise, dict) else now_iso[:10])),
                "amount": float(getattr(promise, "amount", promise.get("amount", 0.0) if isinstance(promise, dict) else 0.0)),
                "currency": getattr(promise, "currency", "CAD")
            }
        else:
            payload = {
                "eventId": f"evt-{uuid.uuid4().hex[:12]}",
                "eventType": "promise.updated",
                "occurredAt": now_iso,
                "ingestedAt": now_iso,
                "sourceSystem": "promise-tracking",
                "correlationId": f"corr-{uuid.uuid4().hex[:8]}",
                "promiseId": str(getattr(promise, "id", promise)),
                "status": str(getattr(promise, "status", "FULFILLED"))
            }
        return producer.send(payload, key=payload.get("accountId") or payload.get("promiseId"))
    except Exception as e:
        print(f"[Kafka Warning] Failed to publish {event_type}: {e}")
        return None


def trigger_spark_batch_job() -> Dict[str, Any]:
    """Executes a full Lakehouse batch pipeline run."""
    return pipeline_runner.run_pipeline()
