"""
Unit and integration tests for the PySpark-style Lakehouse Batch Pipeline.
"""
import unittest
import shutil
import tempfile
from pathlib import Path

from data_platform.lakehouse.dataframe import spark, SparkDataFrame
from data_platform.lakehouse.raw_zone import RawZoneManager
from data_platform.lakehouse.silver_zone import SilverZoneManager
from data_platform.lakehouse.golden_zone import GoldenZoneManager
from data_platform.lakehouse.runner import LakehousePipelineRunner


class TestSparkLakehouse(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.raw_mgr = RawZoneManager(self.test_dir)
        self.silver_mgr = SilverZoneManager(self.test_dir)
        self.golden_mgr = GoldenZoneManager(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_spark_dataframe_operations(self):
        data = [
            {"id": "1", "name": "Alice", "score": 85, "dept": "Risk"},
            {"id": "2", "name": "Bob", "score": 92, "dept": "Collections"},
            {"id": "3", "name": "Charlie", "score": 78, "dept": "Collections"},
        ]
        df = spark.createDataFrame(data)
        self.assertEqual(df.count(), 3)

        # Select & filter
        filtered = df.filter("score > 80").select("name", "score")
        self.assertEqual(filtered.count(), 2)

        # Group By Agg
        grouped = df.groupBy("dept").agg({"score": "mean"})
        self.assertEqual(grouped.count(), 2)

    def test_raw_to_silver_and_dlq(self):
        raw_records = [
            {"id": "acct-1", "customerId": "cust-1", "overdueBalance": "150.25", "dpd": 32, "dnc": False},
            {"id": "acct-2", "customerId": "cust-2", "overdueBalance": 500.0, "dpd": 15, "dnc": True},
            # Missing ID -> goes to DLQ
            {"overdueBalance": 200.0, "dpd": 10}
        ]

        raw_df = self.raw_mgr.ingest_records("loan-servicing", raw_records)
        self.assertEqual(raw_df.count(), 3)

        clean_silver, dlq_silver = self.silver_mgr.process_raw_accounts(raw_df)
        self.assertEqual(clean_silver.count(), 2)
        self.assertEqual(dlq_silver.count(), 1)

    def test_silver_to_golden_aggregation(self):
        clean_accounts = [
            {"account_id": "acct-1", "customer_id": "cust-1", "overdue_balance": 150.0, "total_balance": 200.0, "dpd": 30, "contact_count_7d": 2, "dnc": False, "hardship": False, "dispute": False, "_source_system": "loan-servicing"},
            {"account_id": "acct-2", "customer_id": "cust-1", "overdue_balance": 350.0, "total_balance": 500.0, "dpd": 45, "contact_count_7d": 1, "dnc": False, "hardship": False, "dispute": False, "_source_system": "credit-card"},
            {"account_id": "acct-3", "customer_id": "cust-2", "overdue_balance": 100.0, "total_balance": 100.0, "dpd": 10, "contact_count_7d": 0, "dnc": True, "hardship": True, "dispute": False, "_source_system": "loan-servicing"},
        ]
        silver_df = spark.createDataFrame(clean_accounts)

        c360_df = self.golden_mgr.build_golden_customer_360(silver_df)
        self.assertEqual(c360_df.count(), 2)  # 2 distinct customers

        c1 = [c for c in c360_df.collect() if c["golden_customer_id"] == "cust-1"][0]
        self.assertEqual(c1["account_count"], 2)
        self.assertEqual(c1["total_overdue_balance"], 500.0)
        self.assertEqual(c1["max_dpd"], 45)

        # Feature Store
        feat_df = self.golden_mgr.build_feature_store(silver_df)
        self.assertEqual(feat_df.count(), 3)


if __name__ == '__main__':
    unittest.main()
