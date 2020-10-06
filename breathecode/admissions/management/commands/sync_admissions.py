import os, requests, sys, pytz
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from ...models import Academy, Certificate, Cohort, User, CohortUser

HOST = os.environ.get("OLD_BREATHECODE_API")
DATETIME_FORMAT="%Y-%m-%d"
class Command(BaseCommand):
    help = 'Sync academies from old breathecode'

    def add_arguments(self, parser):
        parser.add_argument('entity', type=str)
        parser.add_argument(
            '--override',
            action='store_true',
            help='Delete and add again',
        )
        parser.add_argument(
              '--limit',
               action='store',
               dest='limit',
               type=int,
               default=0,
               help='How many to import'
        )

    def handle(self, *args, **options):
        try:
            func = getattr(self,options['entity'],'entity_not_found') 
        except TypeError:
            print(f'Sync method for {options["entity"]} no Found!')
        func(options)

    def academies(self, options):

        response = requests.get(f"{HOST}/locations/")
        locations = response.json()

        for loc in locations['data']:
            aca = Academy.objects.filter(slug=loc['slug']).first()
            if aca is None:
                a = Academy(
                    slug=loc['slug'],
                    active_campaign_slug=loc['slug'],
                    name=loc['name'],
                    street_address=loc['address'],
                )
                a.save()
                self.stdout.write(self.style.SUCCESS(f"Academy {a.slug} added"))
            else:
                self.stdout.write(self.style.NOTICE(f"Academy {aca.slug} skipped"))

    def certificates(self, options):

        response = requests.get(f"{HOST}/profiles/")
        profiles = response.json()

        for pro in profiles['data']:
            cert = Certificate.objects.filter(slug=pro['slug']).first()
            if cert is None:
                cert = Certificate(
                    slug=pro['slug'],
                    name=pro['name'],
                    description=pro['description'],
                    duration_in_hours=pro['duration_in_hours'],
                    week_hours=pro['week_hours'],
                    duration_in_days=pro['duration_in_days'],
                    logo=pro['logo'],
                )
                cert.save()
                self.stdout.write(self.style.SUCCESS(f"Certificate {pro['slug']} added"))
            else:
                self.stdout.write(self.style.NOTICE(f"Certificate {pro['slug']} skipped"))

    def cohorts(self, options):

        response = requests.get(f"{HOST}/cohorts/")
        cohorts = response.json()

        for _cohort in cohorts['data']:
            co = Cohort.objects.filter(slug=_cohort['slug']).first()
            if co is None:
                try:
                    self.add_cohort(_cohort)
                    self.stdout.write(self.style.SUCCESS(f"Cohort {_cohort['slug']} added"))
                except Exception as e:
                    raise e
                    # self.stdout.write(self.style.SUCCESS(f"Error adding cohort {_cohort['slug']}: {str(e)}"))    
            else:
                try:
                    self.update_cohort(co, _cohort)
                    self.stdout.write(self.style.SUCCESS(f"Cohort found, updated the kickof date for {_cohort['slug']}"))
                except Exception as e:
                    raise e

    def students(self, options):

        if options['override']:
            User.objects.exclude(email="aalejo@gmail.com").delete()
            CohortUser.objects.all().delete()

        limit = False
        if 'limit' in options and options['limit']:
            limit = options['limit']

        response = requests.get(f"{HOST}/students/")
        students = response.json()

        total = 0
        for _student in students['data']:
            total += 1
            # if limited number of sync options
            if limit and limit > 0 and total > limit:
                self.stdout.write(self.style.SUCCESS(f"Stopped at {total} because there was a limit on the command arguments"))
                return

            user = User.objects.filter(email=_student['email']).first()
            if user is None:
                try:
                    user = self.add_student(_student)
                    self.add_student_cohorts(_student,user)
                    self.stdout.write(self.style.SUCCESS(f"User {_student['email']} added"))
                except Exception as e:
                    raise e
                    # self.stdout.write(self.style.SUCCESS(f"Error adding cohort {_cohort['slug']}: {str(e)}"))    
            else:
                self.stdout.write(self.style.NOTICE(f"User {_student['email']} skipped"))

    def add_cohort(self, _cohort):
        academy = Academy.objects.filter(slug=_cohort['location_slug']).first()
        if academy is None:
            raise CommandError(f"Academy {_cohort['location_slug']} does not exist")
        certificate = Certificate.objects.filter(slug=_cohort['profile_slug']).first()
        if certificate is None:
            raise CommandError(f"Certificate {_cohort['profile_slug']} does not exist")

        stages = {
            'finished': 'ENDED',
            'on-prework': 'PREWORK',
            'not-started': 'INACTIVE',
            'on-course': 'STARTED',
            'on-final-project': 'FINAL_PROJECT',
        }
        if _cohort['stage'] not in stages:
            raise CommandError(f"Invalid cohort stage {_cohort['stage']}")

        co = Cohort(
            slug=_cohort['slug'],
            name=_cohort['name'],
            kickoff_date= datetime.strptime(_cohort['kickoff_date'],DATETIME_FORMAT).replace(tzinfo=pytz.timezone('UTC')),
            current_day=_cohort['current_day'],
            stage=stages[_cohort['stage']],
            language=_cohort['language'],

            academy=academy,
            certificate=certificate,
        )
        if _cohort['ending_date'] is not None:
            co.ending_date = datetime.strptime(_cohort['ending_date'],DATETIME_FORMAT).replace(tzinfo=pytz.timezone('UTC'))
        co.save()

    def update_cohort(self, cohort, data):

        stages = {
            'finished': 'ENDED',
            'on-prework': 'PREWORK',
            'not-started': 'INACTIVE',
            'on-course': 'STARTED',
            'on-final-project': 'FINAL_PROJECT',
        }
        if data['stage'] not in stages:
            raise CommandError(f"Invalid cohort stage {data['stage']}")

        cohort.name = data['name']
        cohort.kickoff_date = datetime.strptime(data['kickoff_date'],DATETIME_FORMAT).replace(tzinfo=pytz.timezone('UTC')),
        cohort.current_day = data['current_day']
        cohort.stage = stages[data['stage']]
        cohort.language = data['stage']
        if data['ending_date'] is not None:
            cohort.ending_date = datetime.strptime(data['ending_date'],DATETIME_FORMAT).replace(tzinfo=pytz.timezone('UTC'))
        cohort.save()

    def add_student(self, _student):
        us = User(
            email=_student['email'],
            username=_student['email'],
            first_name=_student['first_name'],
        )
        if 'last_name' in _student and _student['last_name'] is not None and _student['last_name'] != '':
            us.last_name=_student['last_name']
        us.save()
        return us

    def add_student_cohorts(self, _student, us):
        financial_status = {
            'late': 'LATE',
            'fully_paid': 'FULLY_PAID',
            'up_to_date': 'UP_TO_DATE',
            'uknown': None,
        }
        if _student['financial_status'] not in financial_status:
            raise CommandError(f"Invalid finantial status {_student['financial_status']}")

        educational_status = {
            'under_review': 'ACTIVE',
            'currently_active': 'ACTIVE',
            'blocked': 'SUSPENDED',
            'postponed': 'POSTPONED',
            'studies_finished': 'GRADUATED',
            'student_dropped': 'DROPPED',
        }
        if _student['status'] not in educational_status:
            raise CommandError(f"Invalid educational_status {_student['status']}")

        for cohort_slug in _student['cohorts']:
            cohort = Cohort.objects.filter(slug=cohort_slug).first()
            if cohort is not None:
                cohort_user = CohortUser(
                    user=us,
                    cohort=cohort,
                    role='STUDENT',
                    finantial_status=financial_status[_student['financial_status']],
                    educational_status=educational_status[_student['status']]
                )
                cohort_user.save()
