# Grading Strategy Completion

This document explains how cohort completion, automatic graduation, and certificate eligibility are evaluated.

## Source Of Truth

The central backend service is `breathecode/admissions/services/completion.py`.

Use `evaluate_cohort_user_completion(cohort_user)` whenever code needs to know whether a student completed the cohort requirements. Do not reimplement the rules in receivers, serializers, diagnostics, certificate actions, commands, or frontend helpers.

When automatic graduation succeeds, `graduate_cohort_user_if_complete(cohort_user)` stores the successful completion result in Django cache for a short TTL. Certificate generation reads it through `get_cached_or_evaluate_cohort_user_completion(cohort_user)` to avoid recomputing completion immediately after the graduation receiver runs. If the cache is missing or stale, certificate generation recalculates completion.

The evaluator reads:

- The student's `CohortUser`.
- The cohort's `syllabus_version.json`.
- The student's `Task` rows for that cohort.

`CohortUser.history_log` is useful as a snapshot for UI and attendance, but it is not the official source for graduation or certificate eligibility.

## Syllabus Schema

The canonical schema is:

```json
{
  "grading_strategy": {
    "completion": {
      "type": "FULL_COMPLETION"
    }
  }
}
```

For partial completion:

```json
{
  "grading_strategy": {
    "completion": {
      "type": "PARTIAL_COMPLETION",
      "requirements": {
        "PROJECT": { "min_percent": 100 },
        "EXERCISE": { "min_percent": 100 }
      }
    }
  }
}
```

`completion` at the root of the syllabus JSON is also accepted as an alias, but new syllabuses should use `grading_strategy.completion`.

## Strategy Types

- `FULL_COMPLETION`: requires 100% of `PROJECT`, `EXERCISE`, `LESSON`, and `QUIZ` assets in the syllabus.
- `PARTIAL_COMPLETION`: requires only the asset types listed in `requirements`, each with its own `min_percent`.
- Legacy behavior: if no strategy exists and the syllabus has mandatory projects, completion requires 100% mandatory `PROJECT` assets.
- If no strategy exists and there are no mandatory projects, automatic graduation does not run.

## Completion Rules By Asset Type

- `PROJECT`: complete when `revision_status` is `APPROVED` or `IGNORED`.
- `EXERCISE`: complete when `revision_status` is `APPROVED` or `task_status` is `DONE`.
- `LESSON`: complete when `task_status` is `DONE`.
- `QUIZ`: complete when `task_status` is `DONE`.

The academy feature flag `certificate.auto_ignore_projects_on_delivery` is still honored. When enabled, delivered projects become `IGNORED`; the evaluator counts them as complete.

## Graduation Flow

Automatic SaaS graduation is event driven:

- `revision_status_updated` evaluates completion after project revision changes.
- `assignment_status_updated` evaluates completion when a `LESSON`, `EXERCISE`, or `QUIZ` changes to `DONE`.

Receivers must first skip students already marked `GRADUATED`, then call `evaluate_cohort_user_completion(cohort_user)` or `graduate_cohort_user_if_complete(cohort_user)`.

When completion is true, the receiver sets `CohortUser.educational_status = GRADUATED`. Existing `student_edu_status_updated` receivers then enqueue certificate generation and feedback workflows.

## Certificates

`generate_certificate()` uses the same completion evaluator, with the short-lived cached result when available. Certificate issuance still requires the previous non-completion checks:

- Student is `GRADUATED`.
- Financial status is `FULLY_PAID` or `UP_TO_DATE`.
- Cohort has a teacher.
- Cohort has a certificate specialty.
- Cohort has ended unless `never_ends` is true.

## Demo Data

Use:

```bash
python manage.py seed_grading_strategy_cohorts --clear
```

To enroll an existing user in the demo plan and cohorts:

```bash
python manage.py seed_grading_strategy_cohorts --clear --user user@example.com
```

`--user` accepts a user id, email, or username. The command creates a demo `Plan` and `CohortSet`, attaches all grading strategy cohorts to that set, enrolls the user as `STUDENT` in each cohort, and creates a demo `PlanFinancing` with those joined cohorts.

The command creates short two-day demo syllabuses and cohorts for:

- Full completion.
- Partial projects.
- Partial exercises.
- Partial projects plus exercises.
- Partial lessons plus quizzes.

