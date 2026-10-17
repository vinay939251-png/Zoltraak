# Local scripts

The current demo is deterministic and starts without the 4.66 GB Hugging Face release. When the release ZIP is downloaded, set `HF_DATASET_DIR` to its extracted folder and add a dedicated ingestion adapter that validates the release README/schema before loading records. Never treat the dataset viewer error as proof that the release is invalid; validate the actual ZIP files and encoding.

To reset demo state, delete `data/demo.json`; the server recreates it from `data/seed.json` on the next start.
