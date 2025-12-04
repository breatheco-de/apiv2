"""
Management command to audit email template usage across the codebase.

This command scans all Python files for send_email_message calls and validates them
against the notification registry to ensure consistency.
"""

import ast
import os
from pathlib import Path

from django.core.management.base import BaseCommand

from breathecode.notify.utils.email_manager import EmailManager


class EmailCallVisitor(ast.NodeVisitor):
    """AST visitor to find send_email_message calls."""

    def __init__(self):
        self.calls = []

    def visit_Call(self, node):
        """Visit function calls and extract send_email_message calls."""
        # Check if it's a call to send_email_message
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "send_email_message":
                self.calls.append(node)
        elif isinstance(node.func, ast.Name):
            if node.func.id == "send_email_message":
                self.calls.append(node)

        self.generic_visit(node)


class Command(BaseCommand):
    help = "Audit email template usage against the notification registry"

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Show all issues including warnings",
        )
        parser.add_argument(
            "--show-valid",
            action="store_true",
            help="Also show valid template usages",
        )
        parser.add_argument(
            "--path",
            type=str,
            default="breathecode",
            help="Path to scan (default: breathecode)",
        )

    def handle(self, *args, **options):
        strict = options["strict"]
        show_valid = options["show_valid"]
        scan_path = options["path"]

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("Email Template Usage Audit"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write("")

        # Get base path
        base_path = Path(os.getcwd()) / scan_path

        if not base_path.exists():
            self.stdout.write(self.style.ERROR(f"Path not found: {base_path}"))
            return

        # Scan all Python files
        python_files = list(base_path.rglob("*.py"))
        self.stdout.write(f"Scanning {len(python_files)} Python files in {scan_path}/\n")

        # Statistics
        total_calls = 0
        registered = 0
        unregistered = 0
        missing_vars = 0
        valid_calls = 0
        unknown_calls = 0

        issues = []

        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content, filename=str(py_file))
                visitor = EmailCallVisitor()
                visitor.visit(tree)

                for call in visitor.calls:
                    total_calls += 1
                    result = self._analyze_call(call, py_file)

                    if result:
                        if result["status"] == "unregistered":
                            unregistered += 1
                            issues.append(result)
                        elif result["status"] == "missing_vars":
                            missing_vars += 1
                            registered += 1
                            if strict:
                                issues.append(result)
                        elif result["status"] == "unknown":
                            unknown_calls += 1
                            registered += 1
                            if show_valid:
                                issues.append(result)
                        elif result["status"] == "valid":
                            valid_calls += 1
                            registered += 1
                            if show_valid:
                                issues.append(result)

            except SyntaxError:
                # Skip files with syntax errors
                pass
            except Exception as e:
                if strict:
                    self.stdout.write(self.style.WARNING(f"Error parsing {py_file}: {e}"))

        # Print results
        self._print_summary(total_calls, registered, unregistered, missing_vars, valid_calls, unknown_calls)
        self._print_issues(issues, strict, show_valid)

        # Print registry info
        self._print_registry_info()

    def _analyze_call(self, call, file_path):
        """Analyze a single send_email_message call."""
        # Extract template slug (first argument)
        if not call.args or len(call.args) == 0:
            return {
                "status": "error",
                "file": str(file_path),
                "line": call.lineno,
                "slug": "UNKNOWN",
                "message": "Cannot determine template slug",
            }

        # Try to extract template slug
        slug_arg = call.args[0]
        if isinstance(slug_arg, ast.Constant):
            slug = slug_arg.value
        elif isinstance(slug_arg, ast.Str):  # Python < 3.8
            slug = slug_arg.s
        else:
            return {
                "status": "dynamic",
                "file": str(file_path),
                "line": call.lineno,
                "slug": "DYNAMIC",
                "message": "Template slug is dynamically generated",
            }

        # Check if registered
        if not EmailManager.validate_notification(slug):
            return {
                "status": "unregistered",
                "file": str(file_path),
                "line": call.lineno,
                "slug": slug,
                "message": f"Template '{slug}' not found in registry",
            }

        # Try to extract data dict (third argument)
        data_vars = self._extract_data_dict(call)

        # Get registered variables
        notification = EmailManager.get_notification(slug)
        if not notification:
            return None

        registered_vars = {v["name"]: v for v in notification.get("variables", [])}
        required_vars = {name for name, v in registered_vars.items() if v.get("required", False)}

        # If data_vars is None, we can't determine what variables are passed
        # (it's a variable or complex expression), so mark as unknown
        if data_vars is None:
            return {
                "status": "unknown",
                "file": str(file_path),
                "line": call.lineno,
                "slug": slug,
                "message": f"Template '{slug}' - variables passed via variable (can't validate statically)",
            }

        # Normalize SUBJECT to subject (get_template_content does this automatically)
        # Lines 258-266 in breathecode/notify/actions.py:get_template_content()
        if "SUBJECT" in data_vars:
            data_vars.add("subject")

        # Check for missing required variables (only if we could extract them)
        missing = required_vars - data_vars
        extra = data_vars - set(registered_vars.keys())

        if missing or (extra and len(extra) > 3):  # Only flag if many extra vars
            return {
                "status": "missing_vars",
                "file": str(file_path),
                "line": call.lineno,
                "slug": slug,
                "missing": list(missing),
                "extra": list(extra) if len(extra) > 3 else [],
                "message": f"Variable mismatch in '{slug}'",
            }

        return {
            "status": "valid",
            "file": str(file_path),
            "line": call.lineno,
            "slug": slug,
            "message": f"Template '{slug}' is properly configured",
        }

    def _extract_data_dict(self, call):
        """
        Try to extract variable names from the data dict (3rd argument).
        
        Returns:
            set: Variable names if determinable from literal dict
            None: If data is passed via variable or complex expression (can't determine statically)
        """
        if len(call.args) < 3:
            return None

        data_arg = call.args[2]

        # Handle dict literal (inline dict)
        if isinstance(data_arg, ast.Dict):
            vars_found = set()
            for key in data_arg.keys:
                if isinstance(key, ast.Constant):
                    vars_found.add(key.value)
                elif isinstance(key, ast.Str):
                    vars_found.add(key.s)
            return vars_found

        # If it's a variable name or any other expression, we can't determine statically
        # This includes: variables, function calls, dict comprehensions, etc.
        return None

    def _print_summary(self, total, registered, unregistered, missing_vars, valid, unknown):
        """Print summary statistics."""
        self.stdout.write(self.style.SUCCESS("Summary:"))
        self.stdout.write(f"  Total send_email_message calls: {total}")
        self.stdout.write(f"  ✓ Registered templates: {registered}")
        self.stdout.write(f"    - Valid: {valid}")
        self.stdout.write(f"    - Unknown (vars via variable): {unknown}")
        self.stdout.write(f"    - With warnings: {missing_vars}")

        if unregistered > 0:
            self.stdout.write(self.style.ERROR(f"  ✗ Unregistered templates: {unregistered}"))
        else:
            self.stdout.write(f"  ✗ Unregistered templates: {unregistered}")

        self.stdout.write("")

    def _print_issues(self, issues, strict, show_valid):
        """Print detailed issues."""
        if not issues:
            self.stdout.write(self.style.SUCCESS("No issues found! 🎉"))
            return

        # Group by status
        unregistered = [i for i in issues if i["status"] == "unregistered"]
        missing_vars = [i for i in issues if i["status"] == "missing_vars"]
        unknown = [i for i in issues if i["status"] == "unknown"]
        valid = [i for i in issues if i["status"] == "valid"]

        # Print unregistered templates
        if unregistered:
            self.stdout.write(self.style.ERROR("\n❌ Unregistered Templates:"))
            self.stdout.write(self.style.ERROR("-" * 80))
            for issue in unregistered:
                rel_path = str(issue["file"]).replace(os.getcwd() + "/", "")
                self.stdout.write(f"\n  Template: {self.style.WARNING(issue['slug'])}")
                self.stdout.write(f"  Location: {rel_path}:{issue['line']}")
                self.stdout.write(f"  Issue: {issue['message']}")
                self.stdout.write(
                    f"  Fix: Create breathecode/notify/registry/{issue['slug']}.json"
                )

        # Print variable mismatches
        if missing_vars and strict:
            self.stdout.write(self.style.WARNING("\n⚠️  Variable Mismatches:"))
            self.stdout.write(self.style.WARNING("-" * 80))
            for issue in missing_vars:
                rel_path = str(issue["file"]).replace(os.getcwd() + "/", "")
                self.stdout.write(f"\n  Template: {issue['slug']}")
                self.stdout.write(f"  Location: {rel_path}:{issue['line']}")
                if issue.get("missing"):
                    self.stdout.write(f"  Missing required vars: {', '.join(issue['missing'])}")
                if issue.get("extra"):
                    self.stdout.write(f"  Extra undocumented vars: {', '.join(issue['extra'])}")

        # Print unknown calls (variables passed via variable)
        if unknown and show_valid:
            self.stdout.write(self.style.WARNING("\n❓ Unknown Variable Validation (data passed via variable):"))
            self.stdout.write(self.style.WARNING("-" * 80))
            for issue in unknown:
                rel_path = str(issue["file"]).replace(os.getcwd() + "/", "")
                self.stdout.write(f"  {issue['slug']} - {rel_path}:{issue['line']}")
                self.stdout.write(f"    Note: Variables are passed via variable/expression, can't validate statically")

        # Print valid calls
        if valid and show_valid:
            self.stdout.write(self.style.SUCCESS("\n✓ Valid Template Usages (inline dict):"))
            self.stdout.write(self.style.SUCCESS("-" * 80))
            for issue in valid:
                rel_path = str(issue["file"]).replace(os.getcwd() + "/", "")
                self.stdout.write(f"  {issue['slug']} - {rel_path}:{issue['line']}")

    def _print_registry_info(self):
        """Print information about the registry."""
        self.stdout.write("\n" + self.style.SUCCESS("Registry Information:"))
        self.stdout.write(self.style.SUCCESS("-" * 80))

        notifications = EmailManager.list_notifications()
        categories = EmailManager.get_categories()

        self.stdout.write(f"  Total registered notifications: {len(notifications)}")
        self.stdout.write(f"  Categories: {', '.join(categories)}")

        self.stdout.write("\n  Registered templates:")
        for notif in sorted(notifications, key=lambda x: x["slug"]):
            channels = ", ".join(notif.get("channels", {}).keys())
            self.stdout.write(f"    - {notif['slug']} ({notif['category']}) [{channels}]")

