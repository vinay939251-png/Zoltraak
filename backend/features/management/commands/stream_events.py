"""
Django management command to stream and process events via the Kafka Event Streaming Engine.
Usage:
  python manage.py stream_events --publish-seed
  python manage.py stream_events --consume --group-id analytics-group
"""
from django.core.management.base import BaseCommand
from data_platform.streaming.producer import KafkaProducer
from data_platform.streaming.consumer import KafkaConsumer
from data_platform.streaming.contracts import registry
from data_platform.streaming.broker import broker
from payments.models import Payment
from promises.models import PromiseToPay
from accounts.models import Account


class Command(BaseCommand):
    help = "Publishes or consumes event streams via the Kafka Partitioned Commit Log Engine."

    def add_arguments(self, parser):
        parser.add_argument('--publish-seed', action='store_true', help='Publish events from existing database records to Kafka topics')
        parser.add_argument('--consume', action='store_true', help='Poll and consume messages from Kafka topics')
        parser.add_argument('--group-id', type=str, default='collections-processor', help='Consumer group identifier')
        parser.add_argument('--max-records', type=int, default=50, help='Maximum messages to consume')

    def handle(self, *args, **options):
        producer = KafkaProducer(broker_instance=broker, contract_registry=registry)

        if options.get('publish_seed'):
            self.stdout.write(self.style.NOTICE("Streaming database records into Kafka topics..."))
            published_count = 0

            # 1. Payments
            for p in Payment.objects.all():
                try:
                    meta = producer.send({
                        "eventId": f"evt-pay-{p.id}",
                        "eventType": "payment.received",
                        "occurredAt": p.date.isoformat(),
                        "ingestedAt": p.created_at.isoformat(),
                        "sourceSystem": "payment-ledger",
                        "correlationId": f"corr-{p.id}",
                        "accountId": str(p.account_id),
                        "amount": float(p.amount),
                        "currency": p.currency,
                        "idempotencyKey": p.event_id
                    })
                    published_count += 1
                except Exception as e:
                    self.stderr.write(f"Error publishing payment {p.id}: {e}")

            # 2. Promises
            for pr in PromiseToPay.objects.all():
                try:
                    meta = producer.send({
                        "eventId": f"evt-ptp-{pr.id}",
                        "eventType": "promise.created",
                        "occurredAt": pr.created_at.isoformat(),
                        "ingestedAt": pr.created_at.isoformat(),
                        "sourceSystem": "promise-tracking",
                        "correlationId": f"corr-pr-{pr.id}",
                        "accountId": str(pr.account_id),
                        "dueDate": str(pr.due_date),
                        "amount": float(pr.amount),
                        "currency": pr.currency
                    })
                    published_count += 1
                except Exception as e:
                    self.stderr.write(f"Error publishing promise {pr.id}: {e}")

            self.stdout.write(self.style.SUCCESS(f"Published {published_count} events to Kafka topics."))
            telemetry = broker.get_topic_telemetry()
            self.stdout.write(f"Total messages across all topics: {telemetry['total_messages']}")

        if options.get('consume'):
            group_id = options.get('group_id')
            self.stdout.write(self.style.NOTICE(f"Polling Kafka topics with Consumer Group '{group_id}'..."))
            consumer = KafkaConsumer(
                group_id=group_id,
                topics=["collections.payments", "collections.promises"],
                broker_instance=broker
            )
            records = consumer.poll(max_records=options.get('max_records'))
            self.stdout.write(self.style.SUCCESS(f"Consumed {len(records)} messages:"))
            for r in records:
                self.stdout.write(f"  [{r.topic} | P{r.partition} | Offset {r.offset}] Event: {r.value.get('eventType')} (Key: {r.key})")
