from django.core.management.base import BaseCommand
from breathecode.admissions.models import Academy
from ...actions import run_script
from ...models import MonitorScript, Application


class Command(BaseCommand):
    help = "Sync academies from old breathecode"

    def add_arguments(self, parser):
        parser.add_argument("path", type=str)

    def mock_application(self):

        academy = Academy.objects.filter(slug="fake-sample-academy-delete-me-wililii").first()
        if academy is None:
            academy = Academy(slug="fake-sample-academy-delete-me-wililii")
            academy.save()
        if academy.application_set.count() == 0:
            app = Application(academy=academy)
            app.save()

        return academy.application_set.first()

    def handle(self, *args, **options):
        if options["path"] is None:
            print("Please specify the script path")
        script_slug = options["path"].split(".")[0]
        application = self.mock_application()

        print("Attempting to run script: " + self.style.WARNING(script_slug))
        print("Academy for this test is set to: " + self.style.WARNING(application.academy.slug))
        script = MonitorScript.objects.filter(script_slug=script_slug).first()
        if script is None:
            script = MonitorScript(script_slug=script_slug, application=application)
        result = run_script(script)

        self.stdout.write(self.style.SUCCESS("The script was tested with the following outcome:"))

        stdout = result["text"]
        del result["text"]
        del result["slack_payload"]

        if "details" in result:
            del result["details"]

        print("Details: ", result)
        print("\nStdout: ")
        print(stdout)

        if "btn" in result and result["btn"] is not None:
            self.stdout.write(
                self.style.SUCCESS(
                    "The script has this call to action, " + result["btn"]["label"] + ": " + result["btn"]["url"]
                )
            )
