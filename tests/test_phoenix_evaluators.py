"""Evaluator checks that do not call a model or Phoenix."""

import unittest
from unittest.mock import patch

import pandas as pd

from action_autonomy.cli import main as action_main
from action_autonomy.evaluation import department_matches, _route_task
from action_autonomy.models import Department, RoutingDecision
from action_autonomy.phoenix_eval import get_or_create_dataset
from planning_autonomy.cli import main as planning_main
from planning_autonomy.evaluation import sop_recall


class DepartmentMatchTests(unittest.TestCase):
    def test_same_department_passes(self) -> None:
        result = department_matches(
            {"department": "billing", "reasoning": "charged twice"},
            {"expected_department": "BILLING"},
        )
        self.assertEqual(result, {"score": 1.0, "label": "PASS"})

    def test_other_department_fails(self) -> None:
        result = department_matches(
            {"department": "RETURNS", "reasoning": "send it back"},
            {"expected_department": "BILLING"},
        )
        self.assertEqual(result, {"score": 0.0, "label": "FAIL"})

    def test_missing_output_fails(self) -> None:
        result = department_matches(None, {"expected_department": "BILLING"})
        self.assertEqual(result["label"], "FAIL")


class RouteTaskTests(unittest.TestCase):
    def test_task_returns_department_and_reasoning(self) -> None:
        agent = unittest.mock.Mock()
        agent.route.return_value = RoutingDecision(
            department=Department.BILLING,
            reasoning="charged twice",
            customer_message="I was charged twice",
        )
        task = _route_task(agent)
        self.assertEqual(
            task({"customer_message": "I was charged twice"}),
            {"department": "BILLING", "reasoning": "charged twice"},
        )
        agent.route.assert_called_once_with("I was charged twice")


class SopRecallTests(unittest.TestCase):
    def test_empty_expected_set_scores_one(self) -> None:
        score = sop_recall(
            {"retrieved_sops": ["SOP_001"]},
            {"expected_sops": ""},
        )
        self.assertEqual(score, 1.0)

    def test_duplicate_labels_count_once(self) -> None:
        score = sop_recall(
            {"retrieved_sops": ["SOP_002"]},
            {"expected_sops": "SOP-002_damaged_items,SOP-002_damaged_items"},
        )
        self.assertEqual(score, 1.0)

    def test_missing_expected_sop_lowers_recall(self) -> None:
        score = sop_recall(
            {"retrieved_sops": ["SOP_006"]},
            {
                "expected_sops": (
                    "SOP-006_wrong_item_shipped,SOP-003_billing_disputes"
                )
            },
        )
        self.assertEqual(score, 0.5)


class DatasetReuseTests(unittest.TestCase):
    def test_second_lookup_does_not_upload_again(self) -> None:
        frame = pd.DataFrame({"message": ["hello"], "label": ["BILLING"]})
        stored: dict[str, object] = {}

        class Datasets:
            def get_dataset(self, *, dataset: str):
                if "value" not in stored:
                    raise ValueError(f"Dataset not found: {dataset}")
                return stored["value"]

            def create_dataset(self, **kwargs):
                stored["value"] = _Stored(len(kwargs["dataframe"]))
                stored["calls"] = stored.get("calls", 0) + 1
                return stored["value"]

        class Client:
            datasets = Datasets()

        first = get_or_create_dataset(
            Client(),
            name="action-routing-v1",
            dataframe=frame,
            input_keys=["message"],
            output_keys=["label"],
            metadata_keys=[],
            description="test",
        )
        second = get_or_create_dataset(
            Client(),
            name="action-routing-v1",
            dataframe=frame,
            input_keys=["message"],
            output_keys=["label"],
            metadata_keys=[],
            description="test",
        )
        self.assertIs(first, second)
        self.assertEqual(stored["calls"], 1)


class ScoreCommandTests(unittest.TestCase):
    def test_action_score_exits_when_phoenix_is_down(self) -> None:
        with patch(
            "action_autonomy.phoenix_eval.collector_reachable",
            return_value=False,
        ):
            with patch("action_autonomy.cli.RouterAgent.route") as route:
                with self.assertRaises(SystemExit) as caught:
                    action_main(["--prompt-name", "prompt_1"])
        self.assertIn("6006", str(caught.exception))
        route.assert_not_called()

    def test_planning_score_exits_when_phoenix_is_down(self) -> None:
        with patch(
            "action_autonomy.phoenix_eval.collector_reachable",
            return_value=False,
        ):
            with patch("planning_autonomy.cli.PlanningAgent.plan") as plan:
                with self.assertRaises(SystemExit) as caught:
                    planning_main(["--prompt-name", "prompt_1"])
        self.assertIn("does not print a local score report", str(caught.exception))
        plan.assert_not_called()

    def test_message_still_runs_without_phoenix(self) -> None:
        decision = RoutingDecision(
            department=Department.BILLING,
            reasoning="charged twice",
            customer_message="hi",
        )
        with patch(
            "action_autonomy.phoenix_eval.collector_reachable",
            return_value=False,
        ):
            with patch("action_autonomy.cli.RouterAgent.route", return_value=decision):
                code = action_main(
                    ["--prompt-name", "prompt_1", "--message", "hi"]
                )
        self.assertEqual(code, 0)


class _Stored:
    def __init__(self, count: int) -> None:
        self.count = count

    def __len__(self) -> int:
        return self.count
