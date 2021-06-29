import os, requests, sys, pytz
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from ...models import Assessment, Question, Option

HOST_ASSETS = "https://assets.breatheco.de/apis"
API_URL = os.getenv("API_URL", "")
DATETIME_FORMAT = "%Y-%m-%d"


class Command(BaseCommand):
    help = 'Sync academies from old breathecode'

    def add_arguments(self, parser):
        parser.add_argument('entity', type=str)
        parser.add_argument(
            '--override',
            action='store_true',
            help='Delete and add again',
        )
        parser.add_argument('--limit',
                            action='store',
                            dest='limit',
                            type=int,
                            default=0,
                            help='How many to import')

    def handle(self, *args, **options):
        try:
            func = getattr(self, options['entity'], 'entity_not_found')
        except TypeError:
            print(f'Sync method for {options["entity"]} no Found!')
        func(options)

    def quiz(self, options):

        response = requests.get(f"{HOST_ASSETS}/quiz/all")
        quizzes = response.json()

        for quiz in quizzes:
            if "slug" not in quiz['info']:
                self.stdout.write(
                    self.style.ERROR(
                        f"Ignoring quiz because it does not have a slug"))
                continue

            name = 'No name yet'
            if "name" not in quiz['info']:
                self.stdout.write(
                    self.style.ERROR(
                        f"Quiz f{quiz['info']['slug']} needs a name"))
            else:
                name = quiz['info']["name"]

            a = Assessment.objects.filter(slug=quiz['info']['slug']).first()
            if a is not None:
                continue

            a = Assessment(
                slug=quiz['info']['slug'],
                lang=quiz['info']['lang'],
                title=name,
                comment=quiz['info']['main'],
            )
            a.save()

            for question in quiz["questions"]:
                q = Question(
                    title=question["q"],
                    lang=quiz['info']['lang'],
                    assessment=a,
                    question_type='SELECT',
                )
                q.save()
                for option in question["a"]:
                    o = Option(
                        title=option["option"],
                        score=int(option['correct']),
                        question=q,
                    )
                    o.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created assesment {quiz['info']['slug']}"))
