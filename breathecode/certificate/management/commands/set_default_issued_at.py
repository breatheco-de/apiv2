from breathecode.certificate.models import Specialty
import os
import json
from django.core.management.base import BaseCommand
from pathlib import Path
from breathecode.admissions.models import Academy, Cohort, SpecialtyMode, Syllabus, SyllabusVersion
# from breathecode.certificate.actions import certificate_set_default_issued_at
import breathecode.certificate.actions as actions


class Command(BaseCommand):
    help = 'sets default issued_at for new certificates'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle(self, *args, **options):
        # print(1223244252)
        actions.certificate_set_default_issued_at()
