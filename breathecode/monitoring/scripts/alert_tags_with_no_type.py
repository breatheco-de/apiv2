#!/usr/bin/env python
"""
Alert when there are Tags without tag_type
"""
from breathecode.marketing.models import Tag
from breathecode.utils import ScriptNotification

tags = Tag.objects.all()
pending_tags = tags.filter(tag_type__isnull=True, ac_academy__academy__id=academy.id)

if len(pending_tags) > 0:
    raise ScriptNotification(
        f"""There are {str(pending_tags)} that need to be reviewd and type applied, this is important to make the most out of the tag functionality, for example:
    - Tags with type=DISCOVERY are used for events and downloadables, the tags are applied to attendies.
    - Tags with type=EVENT are usually only event slug\'s, when you create a new event the slug becomes a tag prepended with the word "event-"
    - Tags with type=SOFT or STRONG are used to add contacts to active campaign automations.
    - The tag functionality keeps being developed and there may be other cases not specified in this email.
""",
        status='CRITICAL',
        title=f'There are {str(pending_tags)} tags without type',
        slug='academy-has-tags-without-type')

print(f'No tags without a type from {str(tags.count())} records')
