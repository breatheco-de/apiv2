from datetime import timedelta
from django.db.models import Q
from breathecode.events.models import Event, EventType
from breathecode.mentorship.models import MentorshipService
from breathecode.payments.models import Consumable
from breathecode.utils.decorators import PermissionContextType

from .flags import api
