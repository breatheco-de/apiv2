#!/usr/bin/env python
"""
Alert when there are Tags without tag_type
"""

# flake8: noqa: F821

from breathecode.marketing.models import Tag
from breathecode.utils import ScriptNotification

tags = Tag.objects.all()
pending_tags = tags.filter(tag_type__isnull=True, ac_academy__academy__id=academy.id)
total_pending_tags = pending_tags.count()
if total_pending_tags > 0:
    raise ScriptNotification(
        f"""There are {str(total_pending_tags)} that need to be reviewd and the type must be applied, this is important to make the most out of the tag functionality, for example:
    - Tags with type=DISCOVERY are used for events attendies, downloadables and bottom of the funnel.
    - Tags with type=EVENT are usually only event slug\'s, when you create a new event the slug becomes a tag prepended with the word "event-"
    - Tags with type=SOFT or STRONG are top of the funnel, contacts with this type are added to the CRM and close the the sale.
    - Tags with type=OTHER are not involved in the marketing process, probably used internaly for other things.
    - The tag functionality keeps being developed and there may be other cases not specified in this email.
""",
        status="CRITICAL",
        title=f"There are {str(total_pending_tags)} tags without type in {academy.name}",
        slug="academy-has-tags-without-type",
    )

print(f"No tags without a type from {str(tags.count())} records")
