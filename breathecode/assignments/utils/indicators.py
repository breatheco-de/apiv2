import json
from abc import ABC, abstractmethod
from datetime import datetime

# Algorithm version constant to track changes
ALGO_VERSION = 1.0  # User-defined float, update when algorithms change


# Abstract base class for indicators
class UserIndicator(ABC):
    @abstractmethod
    def calculate_step_indicator(self, step, step_metrics):
        pass

    @abstractmethod
    def calculate_global_indicator(self, step_indicators, global_metrics):
        pass


# Indicator class for user engagement
class EngagementIndicator(UserIndicator):
    def calculate_step_indicator(self, step, step_metrics):
        max_time_per_step = 3600  # 1 hour in seconds
        time_spent = step_metrics["time_spent"]
        normalized_time = min(time_spent / max_time_per_step, 1) * 100
        return round(normalized_time, 2) if step_metrics["status"] not in ["skipped", "unread"] else 0

    def calculate_global_indicator(self, step_indicators, global_metrics):
        total_time = global_metrics["total_time_on_platform"]
        num_sessions = global_metrics["num_sessions"]
        completion_rate = global_metrics["completion_rate"]
        total_interactions = global_metrics["total_interactions"]

        max_total_time = 36000  # 10 hours
        max_num_sessions = 5
        # max_completion_rate = 100
        max_interactions = 100

        norm_total_time = min(total_time / max_total_time, 1) * 100
        norm_num_sessions = min(num_sessions / max_num_sessions, 1) * 100
        norm_completion_rate = completion_rate
        norm_interactions = min(total_interactions / max_interactions, 1) * 100

        weights = {"total_time": 0.3, "num_sessions": 0.2, "completion_rate": 0.3, "interactions": 0.2}

        engagement_score = (
            (
                norm_total_time * weights["total_time"]
                + norm_num_sessions * weights["num_sessions"]
                + norm_completion_rate * weights["completion_rate"]
                + norm_interactions * weights["interactions"]
            )
            / 100
            * 100
        )

        return round(engagement_score, 2)


# Indicator class for user frustration
class FrustrationIndicator(UserIndicator):
    def calculate_step_indicator(self, step, step_metrics):
        if step_metrics["status"] == "completed":
            max_struggles = 20
            total_struggles = step_metrics["comp_struggles"] + step_metrics["test_struggles"]
            frustration = min(total_struggles / max_struggles, 1) * 100
            return round(frustration, 2)
        elif step_metrics["status"] == "attempted":
            max_time = 1800  # 30 minutes
            time_spent = step_metrics["time_spent"]
            frustration = min(time_spent / max_time, 1) * 100
            return round(frustration, 2)
        elif step_metrics["status"] == "skipped":
            return 25.0
        else:
            return 0.0

    def calculate_global_indicator(self, step_indicators, global_metrics):
        steps_not_completed = global_metrics["steps_not_completed"]
        time_on_incomplete = global_metrics["time_on_incomplete"]
        avg_comp_struggles = global_metrics["avg_comp_struggles"]
        avg_test_struggles = global_metrics["avg_test_struggles"]
        skipped_steps = global_metrics["skipped_steps"]

        max_steps_not_completed = global_metrics["total_steps"]
        max_time_on_incomplete = 18000  # 5 hours
        max_avg_comp_struggles = 10
        max_avg_test_struggles = 10
        max_skipped_steps = global_metrics["total_steps"]

        norm_steps_not_completed = (
            (steps_not_completed / max_steps_not_completed * 100) if max_steps_not_completed else 0
        )
        norm_time_on_incomplete = min(time_on_incomplete / max_time_on_incomplete, 1) * 100
        norm_avg_comp_struggles = min(avg_comp_struggles / max_avg_comp_struggles, 1) * 100
        norm_avg_test_struggles = min(avg_test_struggles / max_avg_test_struggles, 1) * 100
        norm_skipped_steps = (skipped_steps / max_skipped_steps * 100) if max_skipped_steps else 0

        weights = {
            "steps_not_completed": 0.3,
            "time_on_incomplete": 0.2,
            "avg_comp_struggles": 0.2,
            "avg_test_struggles": 0.2,
            "skipped_steps": 0.1,
        }

        frustration_score = (
            (
                norm_steps_not_completed * weights["steps_not_completed"]
                + norm_time_on_incomplete * weights["time_on_incomplete"]
                + norm_avg_comp_struggles * weights["avg_comp_struggles"]
                + norm_avg_test_struggles * weights["avg_test_struggles"]
                + norm_skipped_steps * weights["skipped_steps"]
            )
            / 100
            * 100
        )

        return round(frustration_score, 2)


# Main class to calculate user indicators
class UserIndicatorCalculator:
    def __init__(self, json_data, indicators):
        self.data = json.loads(json_data) if isinstance(json_data, str) else json_data
        self.last_interaction_at = self.parse_timestamp(self.data["last_interaction_at"])
        self.tutorial_started_at = self.parse_timestamp(self.data["tutorial_started_at"])
        self.steps = self.data["steps"]
        self.workout_session = self.data["workout_session"]
        self.indicators = indicators

    def parse_timestamp(self, ts):
        return datetime.fromtimestamp(ts / 1000)

    def calculate_step_metrics(self, step):
        status = "unread"
        time_spent = 0
        comp_struggles = 0
        test_struggles = 0

        compilations = step.get("compilations", [])
        tests = step.get("tests", [])

        if "opened_at" in step:
            opened_at = self.parse_timestamp(step["opened_at"])

            if "completed_at" in step:
                status = "completed"
                completed_at = self.parse_timestamp(step["completed_at"])
                time_spent = (completed_at - opened_at).total_seconds()

                compilations = sorted(compilations, key=lambda x: x["starting_at"])
                tests = sorted(tests, key=lambda x: x["starting_at"])

                first_success_comp = next((i for i, comp in enumerate(compilations) if comp["exit_code"] == 0), None)
                if first_success_comp is not None:
                    comp_struggles = sum(1 for comp in compilations[:first_success_comp] if comp["exit_code"] != 0)
                else:
                    comp_struggles = sum(1 for comp in compilations if comp["exit_code"] != 0)

                first_success_test = next((i for i, test in enumerate(tests) if test["exit_code"] == 0), None)
                if first_success_test is not None:
                    test_struggles = sum(1 for test in tests[:first_success_test] if test["exit_code"] != 0)
                else:
                    test_struggles = sum(1 for test in tests if test["exit_code"] != 0)
            else:
                if compilations or tests:
                    status = "attempted"
                    comp_ended_ats = [self.parse_timestamp(comp["ended_at"]) for comp in compilations]
                    test_ended_ats = [self.parse_timestamp(test["ended_at"]) for test in tests]
                    all_ended_ats = comp_ended_ats + test_ended_ats

                    if all_ended_ats:
                        last_interaction_in_step = max(all_ended_ats)
                    else:
                        last_interaction_in_step = self.last_interaction_at

                    time_spent = (last_interaction_in_step - opened_at).total_seconds()
                    time_spent = min(time_spent, 1800)  # Cap at 30 minutes

                    comp_struggles = sum(1 for comp in compilations if comp["exit_code"] != 0)
                    test_struggles = sum(1 for test in tests if test["exit_code"] != 0)
                else:
                    status = "skipped"
                    time_spent = (self.last_interaction_at - opened_at).total_seconds()
                    time_spent = min(time_spent, 1800)  # Cap at 30 minutes

        return {
            "status": status,
            "time_spent": time_spent,
            "comp_struggles": comp_struggles,
            "test_struggles": test_struggles,
        }

    def calculate_global_metrics(self):
        step_metrics = [self.calculate_step_metrics(step) for step in self.steps]
        total_steps = len(self.steps)
        num_completed = sum(1 for sm in step_metrics if sm["status"] == "completed")
        num_attempted = sum(1 for sm in step_metrics if sm["status"] == "attempted")
        num_skipped = sum(1 for sm in step_metrics if sm["status"] == "skipped")
        num_unread = sum(1 for sm in step_metrics if sm["status"] == "unread")
        completion_rate = (num_completed / total_steps) * 100 if total_steps else 0
        total_time_on_platform = (self.last_interaction_at - self.tutorial_started_at).total_seconds()
        num_sessions = len(self.workout_session)
        total_interactions = sum(len(step.get("compilations", [])) + len(step.get("tests", [])) for step in self.steps)
        steps_not_completed = num_attempted + num_skipped + num_unread
        time_on_incomplete = sum(sm["time_spent"] for sm in step_metrics if sm["status"] in ["attempted", "skipped"])
        avg_comp_struggles = sum(sm["comp_struggles"] for sm in step_metrics) / total_steps if total_steps else 0
        avg_test_struggles = sum(sm["test_struggles"] for sm in step_metrics) / total_steps if total_steps else 0

        return {
            "total_time_on_platform": total_time_on_platform,
            "num_sessions": num_sessions,
            "completion_rate": completion_rate,
            "total_interactions": total_interactions,
            "steps_not_completed": steps_not_completed,
            "time_on_incomplete": time_on_incomplete,
            "avg_comp_struggles": avg_comp_struggles,
            "avg_test_struggles": avg_test_struggles,
            "skipped_steps": num_skipped,
            "total_steps": total_steps,
        }

    def _round_metrics(self, metrics):
        return {k: round(v, 2) if isinstance(v, float) else v for k, v in metrics.items()}

    def calculate_indicators(self):
        """
        Calculate all indicators, including metrics and algo_version.

        Returns:
            dict: Structured response with algo_version, global, and step-level data.
                  - algo_version: Version of the algorithm.
                  - global:
                      - metrics: Global metrics.
                      - indicators: Global indicator scores.
                  - steps: List of steps with:
                      - slug: Step identifier.
                      - metrics: Step-specific metrics.
                      - indicators: Step-specific indicator scores.
        """
        step_metrics_list = [self.calculate_step_metrics(step) for step in self.steps]
        global_metrics = self.calculate_global_metrics()

        rounded_global_metrics = self._round_metrics(global_metrics)

        steps_results = []
        for step, sm in zip(self.steps, step_metrics_list):
            rounded_sm = self._round_metrics(sm)
            step_indicators = {"slug": step["slug"], "metrics": rounded_sm, "indicators": {}}
            for indicator in self.indicators:
                indicator_name = indicator.__class__.__name__
                step_indicators["indicators"][indicator_name] = indicator.calculate_step_indicator(step, sm)
            steps_results.append(step_indicators)

        global_indicators = {}
        for indicator in self.indicators:
            indicator_name = indicator.__class__.__name__
            step_indicators_values = [step_result["indicators"][indicator_name] for step_result in steps_results]
            global_indicators[indicator_name] = indicator.calculate_global_indicator(
                step_indicators_values, global_metrics
            )

        return {
            "algo_version": ALGO_VERSION,
            "global": {"metrics": rounded_global_metrics, "indicators": global_indicators},
            "steps": steps_results,
        }


if __name__ == "__main__":

    # Load JSON data from file
    with open("./temp/sample_learnpack_telemetry.json", "r") as file:
        json_data = file.read()

    # Create indicator instances
    indicators = [EngagementIndicator(), FrustrationIndicator()]

    # Calculate indicators
    calculator = UserIndicatorCalculator(json_data, indicators)
    results = calculator.calculate_indicators()

    print(results)
    # Print results
    # for indicator, score in results.items():
    #     print(f"{indicator}: {score}")
