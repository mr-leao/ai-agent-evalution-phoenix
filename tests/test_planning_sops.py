"""Checks for planning_autonomy that do not call a model."""

import os
import unittest
from unittest.mock import patch

from action_autonomy.config import REPO_ROOT

from planning_autonomy.config import PlanningSettings
from planning_autonomy.evaluation import load_test_cases, recall
from planning_autonomy.prompts.judge import parse_alignment
from planning_autonomy.sops import (
    get_index,
    normalize_sop_name,
    parse_expected_sops,
)


class SopIdTests(unittest.TestCase):
    def test_filename_and_csv_label_share_a_number(self) -> None:
        self.assertEqual(normalize_sop_name("SOP-001_standard_returns"), "SOP_001")
        self.assertEqual(
            normalize_sop_name("sop_001_standard_returns.txt"),
            "SOP_001",
        )

    def test_duplicate_labels_count_once(self) -> None:
        parsed = parse_expected_sops(
            "SOP-002_damaged_items,SOP-002_damaged_items"
        )
        self.assertEqual(recall(parsed, ("SOP_002_DAMAGED_ITEMS",)), 1.0)

    def test_empty_expected_set_scores_one(self) -> None:
        self.assertEqual(recall((), ("SOP_001",)), 1.0)

    def test_missing_expected_sop_lowers_recall(self) -> None:
        expected = parse_expected_sops(
            "SOP-006_wrong_item_shipped,SOP-003_billing_disputes"
        )
        self.assertEqual(recall(expected, ("SOP_006",)), 0.5)


class SopIndexTests(unittest.TestCase):
    def test_index_retrieves_the_requested_count(self) -> None:
        index = get_index(str(REPO_ROOT / "data" / "sops"))
        hits = index.retrieve(
            "I bought a jacket last month, but it's too big. Can I return it?",
            "RETURNS",
            top_k=2,
        )
        self.assertEqual(len(hits), 2)
        self.assertEqual(len({hit.sop_id for hit in hits}), 2)
        for hit in hits:
            self.assertTrue(normalize_sop_name(hit.sop_id).startswith("SOP_"))
            self.assertLessEqual(len(hit.excerpt), 2000)
            self.assertGreater(hit.score, 0)


class CaseFileTests(unittest.TestCase):
    def test_v1_csv_is_rejected(self) -> None:
        path = REPO_ROOT / "data" / "v1_test_cases.csv"
        with self.assertRaises(ValueError) as caught:
            load_test_cases(path)
        self.assertIn("expected_sops", str(caught.exception))

    def test_v2_csv_loads(self) -> None:
        frame = load_test_cases(REPO_ROOT / "data" / "v2_test_cases.csv")
        self.assertEqual(len(frame), 22)


class SettingsTests(unittest.TestCase):
    def test_plan_and_judge_models_do_not_replace_the_router_model(self) -> None:
        env = {
            "LLM_MODEL": "router-model",
            "LLM_BASE_URL": "http://localhost:11434/v1",
            "LLM_API_KEY": "ollama",
            "LLM_PLAN_MODEL": "plan-model",
            "LLM_JUDGE_MODEL": "judge-model",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = PlanningSettings.from_env()
        self.assertEqual(settings.connection.model, "router-model")
        self.assertEqual(settings.plan_model, "plan-model")
        self.assertEqual(settings.judge_model, "judge-model")
        self.assertTrue(settings.plan_model_pinned)
        self.assertTrue(settings.judge_model_pinned)


class JudgeParseTests(unittest.TestCase):
    def test_class_line(self) -> None:
        self.assertEqual(parse_alignment("CLASS: good\nREASONING: covers it"), "good")

    def test_missing_class_is_partial(self) -> None:
        self.assertEqual(parse_alignment("looks fine"), "partial")


if __name__ == "__main__":
    unittest.main()
