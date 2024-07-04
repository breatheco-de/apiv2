from breathecode.certificate.models import Specialty
import os
import json
from django.core.management.base import BaseCommand
from pathlib import Path
from breathecode.admissions.models import Academy, Cohort, SyllabusSchedule, Syllabus, SyllabusVersion


def db_backup_bucket():
    return os.getenv("DB_BACKUP_BUCKET")


class Command(BaseCommand):
    help = "Delete duplicate cohort users imported from old breathecode"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def handle(self, *args, **options):
        self.get_backups()
        self.fix_certificates()
        self.fix_syllabus()
        self.fix_specialties()
        self.fix_cohorts()

    def print_debug_info(self):
        from pprint import pprint

        if self.cohorts:
            print("")
            print("cohorts")
            pprint(self.cohorts[0])

        if self.syllabus:
            del self.syllabus[0]["json"]
            print("")
            print("syllabus")
            pprint(self.syllabus[0])

        if self.certificates:
            print("")
            print("certificates")
            pprint(self.certificates[0])

        if self.specialties:
            print("")
            print("specialties")
            pprint(self.specialties[0])

    def get_root_path(self):
        if not hasattr(self, "root_path"):
            self.root_path = Path(os.getcwd())

        return self.root_path

    def get_backups(self):
        self.cohorts = self.get_json_model_from_bucket("admissions", "cohort")
        self.syllabus = self.get_json_model_from_bucket("admissions", "syllabus")
        self.certificates = self.get_json_model_from_bucket("admissions", "certificate")
        self.specialties = self.get_json_model_from_bucket("certificate", "specialty")

    def get_json_model_from_bucket(self, module_name, model_name):
        from breathecode.services import Storage

        storage = Storage()

        file_name = f"{module_name}.{model_name.lower()}.json"
        print("--->", db_backup_bucket(), file_name)
        file = storage.file(db_backup_bucket(), file_name)
        content = file.download()

        return json.loads(content)

    # def seed_env_db(self):
    #     Cohort.objects.all().delete()
    #     for cohort in self.cohorts:
    #         del cohort['id']
    #         del cohort['syllabus_id']
    #         new_cohort = Cohort(**cohort)
    #         new_cohort.save()
    #         cohort['id'] = new_cohort.id

    def get_json_model_from_backup(self, root_path, module_name, model_name):
        with open(root_path / "backup" / f"{module_name}.{model_name.lower()}.json", "r") as file:
            result = json.load(file)

        return result

    def fix_cohorts(self):
        cohort_instances = {}

        for cohort in self.cohorts:
            if not cohort["syllabus_id"]:
                continue

            syllabus = [x for x in self.syllabus if x["id"] == cohort["syllabus_id"]]

            syllabus[0]["certificate_id"]

            certificates = [x for x in self.certificates if x["id"] == syllabus[0]["certificate_id"]]

            version = syllabus[0]["version"]
            slug = certificates[0]["slug"]

            x = Cohort.objects.filter(id=cohort["id"]).first()
            x.syllabus_version = self.syllabus_version_instances[f"{slug}.v{version}"]
            x.save()

        self.cohort_instances = cohort_instances

    def fix_specialties(self):
        specialty_instances = {}

        for specialty in self.specialties:
            syllabus = [
                self.syllabus_instances[x["slug"]] for x in self.certificates if x["id"] == specialty["certificate_id"]
            ]

            if syllabus:
                syllabus = syllabus[0]
            else:
                syllabus = None

            specialty_instances[specialty["id"]] = Specialty.objects.filter(id=specialty["id"]).first()

            if syllabus:
                specialty_instances[specialty["id"]].syllabus = syllabus
                specialty_instances[specialty["id"]].save()

        self.specialty_instances = specialty_instances

    def fix_certificates(self):
        SyllabusSchedule.objects.all().delete()
        Syllabus.objects.all().delete()

        syllabus_instances = {}

        for certificate in self.certificates:
            syllabus_versions = [x for x in self.syllabus if certificate["id"] == x["certificate_id"]]
            kwargs = {}
            if syllabus_versions:
                kwargs = {
                    "academy_owner": None,
                    "private": syllabus_versions[0]["private"],
                    "github_url": syllabus_versions[0]["github_url"],
                }

                academy_id = syllabus_versions[0]["academy_owner_id"]
                if academy_id:
                    kwargs["academy_owner"] = Academy.objects.filter(id=academy_id).first()

            syllabus = Syllabus(
                slug=certificate["slug"],
                name=certificate["name"],
                duration_in_hours=certificate["duration_in_hours"],
                duration_in_days=certificate["duration_in_days"],
                week_hours=certificate["week_hours"],
                logo=certificate["logo"],
                **kwargs,
            )
            syllabus.save()

            syllabus_instances[certificate["slug"]] = syllabus

        self.syllabus_instances = syllabus_instances

    def fix_syllabus(self):
        SyllabusSchedule.objects.all().delete()
        SyllabusVersion.objects.all().delete()

        syllabus_version_instances = {}

        for certificate in self.certificates:
            syllabus_versions = [x for x in self.syllabus if certificate["id"] == x["certificate_id"]]

            for syllabus_version in syllabus_versions:
                x = SyllabusVersion(
                    version=syllabus_version["version"],
                    json=syllabus_version["json"],
                    syllabus=self.syllabus_instances[certificate["slug"]],
                )
                x.save()

                key = f'{certificate["slug"]}.v{syllabus_version["version"]}'
                syllabus_version_instances[key] = x

        self.syllabus_version_instances = syllabus_version_instances
