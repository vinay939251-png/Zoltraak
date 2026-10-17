"""
Django management command to execute the Lakehouse batch transformation pipeline (Spark equivalent).
Usage: python manage.py run_spark_pipeline
"""
from django.core.management.base import BaseCommand
from data_platform.lakehouse.runner import pipeline_runner


class Command(BaseCommand):
    help = "Executes the Raw -> Silver -> Golden Lakehouse batch data transformation pipeline."

    def add_arguments(self, parser):
        parser.add_argument(
            '--partition-date',
            type=str,
            help='Partition date (YYYY-MM-DD) to process',
            default=None
        )

    def handle(self, *args, **options):
        partition_date = options.get('partition_date')
        self.stdout.write(self.style.NOTICE("Starting PySpark-style Lakehouse Batch Pipeline..."))
        manifest = pipeline_runner.run_pipeline(partition_date=partition_date)

        self.stdout.write(self.style.SUCCESS(
            f"Successfully completed Lakehouse Batch Job [{manifest['job_id']}] in {manifest['duration_ms']}ms"
        ))
        self.stdout.write(f"  Raw Ingested:        {manifest['zones']['raw']['records_ingested']} records")
        self.stdout.write(f"  Silver Cleansed:     {manifest['zones']['silver']['cleansed_records']} records (DLQ: {manifest['zones']['silver']['dlq_records']})")
        self.stdout.write(f"  Golden Customer 360: {manifest['zones']['golden']['customer_360_records']} records")
        self.stdout.write(f"  Features Derived:    {manifest['zones']['golden']['features_derived']} records")
