import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import compare_runs


class ComparisonTests(unittest.TestCase):
    def test_pooled_confusion_counts(self):
        run = json.loads((compare_runs.HERE / "results/run_20261007-105656.json").read_text(encoding="utf-8"))
        summary = compare_runs.values(run["cases"])
        self.assertEqual(summary["n_cases"], 48)
        self.assertEqual(summary["tp"], run["summary"]["tp"])
        total = sum(summary[k] for k in ("tp", "fp", "fn", "tn"))
        self.assertEqual(summary["accuracy"], (summary["tp"] + summary["tn"]) / total)

    def test_missing_dataset_not_fabricated(self):
        spec = {"id": "missing", "golden": "missing.jsonl", "pred": "missing-pred.jsonl"}
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(compare_runs, "HERE", Path(directory)), patch.object(compare_runs, "RUNS", [spec]):
                with self.assertRaisesRegex(SystemExit, "Chưa có"):
                    compare_runs.main()
                self.assertFalse((Path(directory) / "results/metrics_all.json").exists())


if __name__ == "__main__":
    unittest.main()
