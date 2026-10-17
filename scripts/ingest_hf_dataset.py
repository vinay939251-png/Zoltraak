#!/usr/bin/env python
"""Hugging Face Maple Collections Dataset Ingestion Utility.

Reference: https://huggingface.co/datasets/nuxsh/maple-collections-hackathon

Usage:
    python scripts/ingest_hf_dataset.py --dir /path/to/extracted/release
    python scripts/ingest_hf_dataset.py --dry-run
"""
import sys
import os
from pathlib import Path

# Setup Django environment
project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / 'backend'
sys.path.insert(0, str(backend_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    args = sys.argv[1:]
    call_command('ingest_hf', *args)
