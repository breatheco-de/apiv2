from breathecode.feedback.models import Answer, Survey


def set_default_survey_title_and_template_slug():
    surveys = Survey.objects.all()
    updated_count = 0

    for survey in surveys:
        # Get the first answer for the survey
        first_answer = Answer.objects.filter(survey=survey).first()

        if first_answer:
            # Set the survey title based on the first answer's title
            if not survey.title:
                survey.title = first_answer.title or f"Survey {first_answer.id}"

            # Set the survey template_slug based on the first answer's question_by_slug
            if not survey.template_slug:
                survey.template_slug = first_answer.question_by_slug or "default-template"

            survey.save()
            updated_count += 1

    print(f"Updated {updated_count} surveys with default title and template_slug.")


# Run the function
set_default_survey_title_and_template_slug()
