#!/usr/bin/env python
"""
Checks if there are assets with errors to be fixed
"""
from breathecode.utils import ScriptNotification
from breathecode.registry.models import AssetErrorLog
from breathecode.utils.datetime_integer import from_now

errors = AssetErrorLog.objects.filter(status="ERROR")

total_errors = errors.count()
if total_errors == 0:
    print("No asset errors found")

else:
    content = ""
    for e in errors:
        content += f"- {e.slug} with path {str(e.path)} since {from_now(e.created_at)} ago \n"

    raise ScriptNotification(
        f"There are {str(total_errors)} erros on the asset log: \n\n" f"{content}",
        status="CRITICAL",
        title=f"There are {str(total_errors)} erros on the asset log:",
        slug="asset-errors",
    )
