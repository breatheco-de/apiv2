"""
Management command to test validate_email_local with multiple emails

Usage examples:
    # Validate single email
    python manage.py test_validate_email_local test@gmail.com

    # Validate multiple emails
    python manage.py test_validate_email_local test@gmail.com user@yahoo.com admin@company.com

    # Validate emails from a file
    python manage.py test_validate_email_local --file emails.txt

    # Use the example file (default if no arguments)
    python manage.py test_validate_email_local --file example_emails.txt

    # Use Spanish error messages
    python manage.py test_validate_email_local --file emails.txt --lang es

    # Output in JSON format
    python manage.py test_validate_email_local --file emails.txt --json
"""
import json
import os
from django.core.management.base import BaseCommand, CommandError
from capyc.rest_framework.exceptions import ValidationException

from breathecode.marketing.actions import validate_email_local


class Command(BaseCommand):
    help = "Test validate_email_local action with one or multiple emails"

    def add_arguments(self, parser):
        parser.add_argument(
            "emails",
            nargs="*",
            type=str,
            help="Email addresses to validate (space-separated)",
        )
        parser.add_argument(
            "--file",
            type=str,
            help="Path to a text file containing email addresses (one per line). "
            "If 'example_emails.txt' is used, it will look in the same directory as this command.",
        )
        parser.add_argument(
            "--lang",
            type=str,
            default="en",
            help="Language for error messages (default: en)",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output results in JSON format",
        )

    def _get_example_file_path(self):
        """Get the path to example_emails.txt in the same directory as this command"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, "example_emails.txt")

    def _read_emails_from_file(self, file_path):
        """Read emails from a file, one per line"""
        try:
            # If the file is 'example_emails.txt' and doesn't exist, try in the command directory
            if file_path == "example_emails.txt" and not os.path.exists(file_path):
                file_path = self._get_example_file_path()

            with open(file_path, "r", encoding="utf-8") as f:
                emails = []
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        emails.append(line)
                return emails
        except FileNotFoundError:
            raise CommandError(f'File "{file_path}" not found.')
        except Exception as e:
            raise CommandError(f'Error reading file "{file_path}": {e}')

    def handle(self, *args, **options):
        emails = []
        lang = options["lang"]
        output_json = options["json"]

        # Get emails from command line arguments
        if options["emails"]:
            emails.extend(options["emails"])

        # Get emails from file
        if options["file"]:
            file_emails = self._read_emails_from_file(options["file"])
            emails.extend(file_emails)
            self.stdout.write(
                self.style.SUCCESS(f"Loaded {len(file_emails)} emails from {options['file']}")
            )

        # If no emails provided and no file specified, try to use example_emails.txt
        if not emails:
            example_file = self._get_example_file_path()
            if os.path.exists(example_file):
                self.stdout.write(
                    self.style.WARNING(
                        f"No emails provided. Using example file: {example_file}"
                    )
                )
                emails = self._read_emails_from_file(example_file)
            else:
                raise CommandError(
                    "No emails provided. Use --help for usage information.\n"
                    "Examples:\n"
                    "  python manage.py test_validate_email_local test@gmail.com\n"
                    "  python manage.py test_validate_email_local --file emails.txt"
                )

        results = []
        valid_count = 0
        invalid_count = 0
        total_emails = len(emails)

        for idx, email in enumerate(emails, 1):
            if not output_json:
                self.stdout.write(f"Validando {idx}/{total_emails}: {email}...", ending="\r")
                self.stdout.flush()
            
            try:
                result = validate_email_local(email, lang)
                results.append(
                    {
                        "email": email,
                        "status": "valid",
                        "result": result,
                    }
                )
                valid_count += 1

                if not output_json:
                    # Limpiar la línea de progreso
                    self.stdout.write(" " * 80 + "\r", ending="")
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ {email} - VALID")
                    )
                    self.stdout.write(
                        f"  Format: {result['format_valid']}, "
                        f"MX: {result['mx_found']}, "
                        f"MX Records: {len(result.get('mx_records', []))}, "
                        f"SPF: {'Yes' if result.get('spf') else 'No'}, "
                        f"DMARC: {'Yes' if result.get('dmarc') else 'No'}, "
                        f"Free: {result['free']}, "
                        f"Role: {result['role']}, "
                        f"Disposable: {result['disposable']}, "
                        f"Score: {result['score']:.2f}"
                    )

            except ValidationException as e:
                results.append(
                    {
                        "email": email,
                        "status": "invalid",
                        "error": {
                            "slug": e.slug,
                            "message": str(e),
                        },
                    }
                )
                invalid_count += 1

                if not output_json:
                    # Limpiar la línea de progreso
                    self.stdout.write(" " * 80 + "\r", ending="")
                    self.stdout.write(self.style.ERROR(f"✗ {email} - INVALID"))
                    self.stdout.write(f"  Error: {e.slug} - {str(e)}")

            except Exception as e:
                results.append(
                    {
                        "email": email,
                        "status": "error",
                        "error": {
                            "type": type(e).__name__,
                            "message": str(e),
                        },
                    }
                )
                invalid_count += 1

                if not output_json:
                    # Limpiar la línea de progreso
                    self.stdout.write(" " * 80 + "\r", ending="")
                    self.stdout.write(self.style.ERROR(f"✗ {email} - ERROR"))
                    self.stdout.write(f"  Error: {type(e).__name__} - {str(e)}")

        # Summary
        if output_json:
            output = {
                "summary": {
                    "total": len(emails),
                    "valid": valid_count,
                    "invalid": invalid_count,
                },
                "results": results,
            }
            self.stdout.write(json.dumps(output, indent=2))
        else:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(
                self.style.SUCCESS(
                    f"Summary: {valid_count} valid, {invalid_count} invalid out of {len(emails)} total"
                )
            )
            self.stdout.write(self.style.SUCCESS("=" * 60))

