"""
Unit and integration tests for the Kafka Event Streaming Engine.
"""
import unittest
import shutil
import tempfile
from pathlib import Path

from data_platform.streaming.contracts import EventContractRegistry, EventContractValidationError
from data_platform.streaming.broker import KafkaBroker
from data_platform.streaming.producer import KafkaProducer
from data_platform.streaming.consumer import KafkaConsumer


class TestKafkaStreaming(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.broker = KafkaBroker(root_dir=self.test_dir)
        self.registry = EventContractRegistry()
        self.producer = KafkaProducer(broker_instance=self.broker, contract_registry=self.registry)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_contract_validation_success(self):
        valid_event = {
            "eventId": "evt-123",
            "eventType": "payment.received",
            "occurredAt": "2026-10-17T06:00:00Z",
            "ingestedAt": "2026-10-17T06:00:01Z",
            "sourceSystem": "payment-ledger",
            "correlationId": "corr-456",
            "accountId": "acct-1001",
            "amount": 250.00,
            "currency": "CAD",
            "idempotencyKey": "idemp-001"
        }
        is_valid, error = self.registry.validate(valid_event)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_contract_validation_fails_on_missing_field(self):
        invalid_event = {
            "eventId": "evt-123",
            "eventType": "payment.received",
            "sourceSystem": "payment-ledger",
            # missing correlationId, accountId, etc.
        }
        is_valid, error = self.registry.validate(invalid_event)
        self.assertFalse(is_valid)
        self.assertIn("Missing mandatory", error)

    def test_contract_validation_rejects_protected_attributes(self):
        biased_event = {
            "eventId": "evt-123",
            "eventType": "payment.received",
            "occurredAt": "2026-10-17T06:00:00Z",
            "ingestedAt": "2026-10-17T06:00:01Z",
            "sourceSystem": "payment-ledger",
            "correlationId": "corr-456",
            "accountId": "acct-1001",
            "amount": 250.00,
            "currency": "CAD",
            "idempotencyKey": "idemp-001",
            "gender": "male"  # Prohibited attribute
        }
        is_valid, error = self.registry.validate(biased_event)
        self.assertFalse(is_valid)
        self.assertIn("prohibited protected attribute", error)

    def test_producer_and_consumer_workflow(self):
        event = {
            "eventId": "evt-ptp-1",
            "eventType": "promise.created",
            "occurredAt": "2026-10-17T06:00:00Z",
            "ingestedAt": "2026-10-17T06:00:01Z",
            "sourceSystem": "promise-tracking",
            "correlationId": "corr-ptp-1",
            "accountId": "acct-1001",
            "dueDate": "2026-10-25",
            "amount": 150.00,
            "currency": "CAD"
        }
        meta = self.producer.send(event, key="acct-1001")
        self.assertEqual(meta.topic, "collections.promises")
        self.assertEqual(meta.offset, 0)

        # Consumer poll
        consumer = KafkaConsumer(group_id="test-grp", topics=["collections.promises"], broker_instance=self.broker)
        records = consumer.poll(max_records=10)
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec.value["eventId"], "evt-ptp-1")
        self.assertEqual(rec.key, "acct-1001")

        # Second poll without new messages yields 0
        records2 = consumer.poll(max_records=10)
        self.assertEqual(len(records2), 0)

    def test_partition_consistency_for_same_key(self):
        p1 = self.broker.hash_partition("collections.payments", "acct-1001")
        p2 = self.broker.hash_partition("collections.payments", "acct-1001")
        self.assertEqual(p1, p2)


if __name__ == '__main__':
    unittest.main()
