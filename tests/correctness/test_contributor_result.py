import json
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
EXAMPLE = ROOT / "experiments" / "results" / "contributor_result.example.json"
SCHEMA = ROOT / "schemas" / "contributor_result.schema.json"


class ContributorResultTemplateTests(unittest.TestCase):
    def test_example_is_a_blank_estimate_not_a_model_measurement(self):
        example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

        self.assertEqual(example["schema_version"], 1)
        self.assertTrue(example["example_only"])
        self.assertEqual(example["evidence_class"], "ESTIMATED")
        self.assertFalse(example["synthetic"])
        self.assertEqual(example["quality"]["status"], "NOT_RUN")
        self.assertIsNone(example["model"]["sha256"])
        for name in schema["properties"]["metrics"]["required"]:
            self.assertIsNone(example["metrics"][name])
        self.assertEqual(
            set(example),
            set(schema["required"]),
        )

    def test_measured_guidance_requires_sha256_and_a_command(self):
        text = (ROOT / "docs" / "CONTRIBUTOR_RESULT.md").read_text(encoding="utf-8")
        self.assertIn("MEASURED", text)
        self.assertIn("ESTIMATED", text)
        self.assertIn("sha256", text)
        self.assertIn("NOT_RUN", text)
