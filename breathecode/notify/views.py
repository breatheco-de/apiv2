import logging
import os

from capyc.rest_framework.exceptions import ValidationException
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.admissions.models import Academy
from breathecode.utils import APIViewExtensions, GenerateLookupsMixin
from breathecode.utils.decorators import capable_of

from .actions import get_template_content
from .models import AcademyNotifySettings, Hook, Notification, SlackTeam
from .serializers import AcademyNotifySettingsSerializer, HookSerializer, NotificationSerializer, SlackTeamSerializer
from .tasks import async_slack_action, async_slack_command
from .utils.email_manager import EmailManager

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def preview_template(request, slug):
    template = get_template_content(slug, request.GET, formats=["html"])
    return HttpResponse(template["html"])


@api_view(["GET"])
@permission_classes([AllowAny])
def preview_slack_template(request, slug):
    template = get_template_content(slug, request.GET, ["slack"])
    return HttpResponse(template["slack"])


@api_view(["GET"])
@permission_classes([AllowAny])
def test_email(request, email):
    # tags = sync_user_issues()
    # return Response(tags, status=status.HTTP_200_OK)
    pass


@api_view(["POST"])
@permission_classes([AllowAny])
def process_interaction(request):
    try:
        async_slack_action.delay(request.POST)
        logger.debug("Slack action enqueued")
        return Response("Processing...", status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("Error processing slack action")
        return Response(str(e), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def slack_command(request):

    try:
        async_slack_command.delay(request.data)
        logger.debug("Slack command enqueued")
        return Response("Processing...", status=status.HTTP_200_OK)
    except Exception as e:
        logger.exception("Error processing slack command")
        return Response(str(e), status=status.HTTP_200_OK)


@api_view(["GET"])
def get_sample_data(request, hook_id=None):

    if hook_id is not None:
        hook = Hook.objects.filter(user__id=request.user.id, id=hook_id).first()
        if hook is None:
            return Response(
                {"details": "No hook found with this filters for sample data"}, status=status.HTTP_400_BAD_REQUEST
            )

        if hook.sample_data is None:
            return Response([])

        return Response(hook.sample_data)

    items = Hook.objects.filter(user__id=request.user.id)
    filtered = False
    event = request.GET.get("event", None)
    if event is not None:
        filtered = True
        items = items.filter(event__in=event.split(","))

    service_id = request.GET.get("service_id", None)
    if service_id is not None:
        filtered = True
        items = items.filter(service_id__in=service_id.split(","))

    like = request.GET.get("like", None)

    if like is not None:
        items = items.filter(Q(event__icontains=like) | Q(target__icontains=like))

    if not filtered:
        return Response(
            {"details": "Please specify hook id or filters get have an idea on what sample data you want"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    single = items.first()
    if single is None:
        return Response(
            {"details": "No hook found with this filters for sample data"}, status=status.HTTP_400_BAD_REQUEST
        )

    return Response(single.sample_data)


@api_view(["GET"])
def get_hook_events(request):
    """
    Get all available webhook events with descriptions and metadata.
    
    Returns a list of all available webhook events that can be subscribed to,
    including their descriptions, apps, labels, and associated models.
    
    Query Parameters:
        app (optional): Filter events by app name (admissions, assignments, marketing, etc.)
        like (optional): Search in event name or description
    
    Example Response:
        [
            {
                "event": "assignment.assignment_created",
                "label": "Assignment Created",
                "description": "Triggered when a new assignment is created for a student",
                "app": "assignments",
                "model": "assignments.Task"
            },
            ...
        ]
    """
    from django.conf import settings
    from breathecode.notify.utils.auto_register_hooks import (
        derive_app_from_action,
        derive_label_from_action,
        derive_model_from_action,
    )

    # Get metadata from settings, fallback to empty dict if not defined
    metadata = getattr(settings, "HOOK_EVENTS_METADATA", {})
    
    # Build response with all available events
    events = []
    for event_name, event_config in metadata.items():
        action = event_config.get("action")
        
        # Get or derive app name
        app_name = event_config.get("app")
        if not app_name and action:
            app_name = derive_app_from_action(action)
        
        # Get or derive model
        model = event_config.get("model")
        if not model and action:
            model = derive_model_from_action(action)
        
        # Get or derive label
        label = event_config.get("label")
        if not label and action:
            label = derive_label_from_action(action)
        
        event_data = {
            "event": event_name,
            "label": label or "Unknown",
            "description": event_config.get("description", "No description available"),
            "app": app_name or "unknown",
            "model": model or "Unknown",
        }
        events.append(event_data)
    
    # Filter by app if provided
    app = request.GET.get("app", None)
    if app:
        events = [e for e in events if e["app"].lower() == app.lower()]
    
    # Filter by search term if provided
    like = request.GET.get("like", None)
    if like:
        like_lower = like.lower()
        events = [
            e
            for e in events
            if like_lower in e["event"].lower()
            or like_lower in e["description"].lower()
            or like_lower in e["app"].lower()
            or like_lower in e["label"].lower()
        ]
    
    # Sort by app, then by event name
    events.sort(key=lambda x: (x["app"], x["event"]))
    
    return Response(events)


class HooksView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    def get(self, request):
        handler = self.extensions(request)

        items = Hook.objects.filter(user__id=request.user.id)

        event = request.GET.get("event", None)
        if event is not None:
            items = items.filter(event__in=event.split(","))

        service_id = request.GET.get("service_id", None)
        if service_id is not None:
            items = items.filter(service_id__in=service_id.split(","))

        like = request.GET.get("like", None)
        if like is not None:
            items = items.filter(Q(event__icontains=like) | Q(target__icontains=like))

        items = handler.queryset(items)
        serializer = HookSerializer(items, many=True)

        return handler.response(serializer.data)

    def post(self, request):

        serializer = HookSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, hook_id):

        hook = Hook.objects.filter(id=hook_id, user__id=request.user.id).first()
        if hook is None:
            raise ValidationException(f"Hook {hook_id} not found for this user", slug="hook-not-found")

        serializer = HookSerializer(
            instance=hook,
            data=request.data,
            context={
                "request": request,
            },
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, hook_id=None):

        filtered = False
        items = Hook.objects.filter(user__id=request.user.id)
        if hook_id is not None:
            items = items.filter(id=hook_id)
            filtered = True
        else:
            event = request.GET.get("event", None)
            if event is not None:
                filtered = True
                items = items.filter(event__in=event.split(","))

            service_id = request.GET.get("service_id", None)
            if service_id is not None:
                filtered = True
                items = items.filter(service_id__in=service_id.split(","))

        if not filtered:
            raise ValidationException("Please include some filter in the URL")

        total = items.count()
        for item in items:
            item.delete()

        return Response({"details": f"Unsubscribed from {total} hooks"}, status=status.HTTP_200_OK)


class SlackTeamsView(APIView, GenerateLookupsMixin):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    def get(self, request):
        handler = self.extensions(request)

        items = SlackTeam.objects.all()
        academy = request.GET.get("academy", None)
        if academy is not None:
            academy = academy.split(",")
            items = items.filter(academy__slug__in=academy)

        items = handler.queryset(items)
        serializer = SlackTeamSerializer(items, many=True)

        return handler.response(serializer.data)


class NotificationsView(APIView, GenerateLookupsMixin):
    extensions = APIViewExtensions(sort="-id", paginate=True)

    def get(self, request):
        handler = self.extensions(request)
        items = Notification.objects.filter(user__id=request.user.id)

        if (academies := request.GET.get("academy")) is not None:
            academies = academies.split(",")
            items = items.filter(academy__slug__in=academies)

        if (done_at := request.GET.get("done_at")) is not None:
            items = items.filter(done_at__gte=done_at)

        if request.GET.get("seen") == "true":
            items = items.filter(seen_at__isnull=False)

        items = handler.queryset(items)

        ids = [x.id for x in items if x.seen_at is None]
        if ids:
            Notification.objects.filter(id__in=ids).update(seen_at=timezone.now())

        serializer = NotificationSerializer(items, many=True)
        return handler.response(serializer.data)


class NotificationTemplatesView(APIView):
    """
    List all notification templates from the registry.
    """

    @capable_of("read_notification")
    def get(self, request, academy_id=None):
        """
        GET /v1/notify/academy/template
        List all registered notifications with optional filters.

        Query params:
        - category: filter by category
        - search: search in name/description
        - channel: filter by channel availability
        """
        category = request.GET.get("category")
        search = request.GET.get("search", "").lower()
        channel = request.GET.get("channel")

        # Get notifications from EmailManager
        notifications = EmailManager.list_notifications(category=category, channel=channel)

        # Apply search filter
        if search:
            notifications = [
                n
                for n in notifications
                if search in n.get("name", "").lower() or search in n.get("description", "").lower()
            ]

        # Get categories for metadata
        categories = EmailManager.get_categories()

        return Response({"templates": notifications, "categories": categories, "total": len(notifications)})


class NotificationTemplateView(APIView):
    """
    Get metadata for a specific notification template.
    """

    @capable_of("read_notification")
    def get(self, request, slug, academy_id=None):
        """
        GET /v1/notify/academy/template/<slug>
        Get notification configuration for a specific slug.
        """
        notification = EmailManager.get_notification(slug)

        if not notification:
            raise ValidationException(f"Notification template '{slug}' not found", slug="notification-not-found")

        return Response(notification)


class NotificationTemplatePreviewView(APIView):
    """
    Preview a notification template with raw template source.
    """

    @capable_of("read_notification")
    def get(self, request, slug, academy_id=None):
        """
        GET /v1/notify/academy/template/<slug>/preview
        Preview notification template across all or specific channels.

        The academy_id is provided by the capable_of decorator from the request headers.
        User can only preview templates for their own academy.

        Query params:
        - channels: comma-separated list of channels (email,slack,sms)
        """
        # Get academy from academy_id provided by capable_of decorator
        academy = None
        if academy_id:
            academy = Academy.objects.filter(id=academy_id).first()

        # Parse channels filter
        channels = None
        if request.GET.get("channels"):
            channels = [ch.strip() for ch in request.GET.get("channels").split(",")]

        # Get preview from EmailManager
        try:
            preview_data = EmailManager.get_template_preview(slug, academy=academy, channels=channels)
            return Response(preview_data)
        except ValidationException:
            raise
        except Exception as e:
            logger.exception(f"Error generating preview for {slug}")
            raise ValidationException(f"Error generating preview: {str(e)}", slug="preview-error")


class AcademyNotifySettingsView(APIView):
    """Manage notification settings for an academy."""

    @capable_of("read_notification")
    def get(self, request, academy_id=None):
        """Get notification settings for academy."""
        settings = AcademyNotifySettings.objects.filter(academy_id=academy_id).first()
        if not settings:
            return Response({"template_variables": {}, "academy": academy_id})

        serializer = AcademyNotifySettingsSerializer(settings)
        return Response(serializer.data)

    @capable_of("crud_notification")
    def put(self, request, academy_id=None):
        """Update notification settings for academy."""
        settings, created = AcademyNotifySettings.objects.get_or_create(academy_id=academy_id)

        serializer = AcademyNotifySettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademyNotifyVariablesView(APIView):
    """Show available notification variables for an academy."""

    @capable_of("read_notification")
    def get(self, request, academy_id=None):
        """
        Get all available variables for notification templates.
        
        Query params:
        - template: Optional template slug to show final merged values for that template
        """
        academy = Academy.objects.filter(id=academy_id).first()
        if not academy:
            raise ValidationException("Academy not found", slug="academy-not-found")

        # System defaults from environment
        system_defaults = {
            "API_URL": os.environ.get("API_URL", ""),
            "COMPANY_NAME": os.environ.get("COMPANY_NAME", ""),
            "COMPANY_CONTACT_URL": os.environ.get("COMPANY_CONTACT_URL", ""),
            "COMPANY_LEGAL_NAME": os.environ.get("COMPANY_LEGAL_NAME", ""),
            "COMPANY_ADDRESS": os.environ.get("COMPANY_ADDRESS", ""),
            "COMPANY_INFO_EMAIL": os.environ.get("COMPANY_INFO_EMAIL", ""),
            "DOMAIN_NAME": os.environ.get("DOMAIN_NAME", ""),
            "style__success": "#99ccff",
            "style__danger": "#ffcccc",
            "style__secondary": "#ededed",
        }

        # Academy model values
        academy_values = {
            "COMPANY_NAME": academy.name,
            "COMPANY_LOGO": academy.logo_url,
            "COMPANY_INFO_EMAIL": academy.feedback_email,
            "COMPANY_LEGAL_NAME": academy.legal_name or academy.name,
            "PLATFORM_DESCRIPTION": academy.platform_description,
            "DOMAIN_NAME": academy.website_url,
        }

        # Academy template_variables overrides
        global_overrides = {}
        template_specific_overrides = {}
        
        if hasattr(academy, 'notify_settings') and academy.notify_settings:
            settings = academy.notify_settings
            
            for key, value in settings.template_variables.items():
                if key.startswith("global."):
                    var_name = key.replace("global.", "")
                    global_overrides[var_name] = value
                elif key.startswith("template."):
                    # Parse template.SLUG.VARIABLE format
                    parts = key.split(".", 2)  # Split into max 3 parts
                    if len(parts) == 3:
                        template_slug = parts[1]
                        var_name = parts[2]
                        if template_slug not in template_specific_overrides:
                            template_specific_overrides[template_slug] = {}
                        template_specific_overrides[template_slug][var_name] = value

        response_data = {
            "system_defaults": system_defaults,
            "academy_values": academy_values,
            "global_overrides": global_overrides,
            "template_specific_overrides": template_specific_overrides,
        }

        # If template specified, show final merged values for that template
        template_slug = request.GET.get("template")
        if template_slug:
            if hasattr(academy, 'notify_settings') and academy.notify_settings:
                settings = academy.notify_settings
                
                # Check if template is disabled
                if not settings.is_template_enabled(template_slug):
                    response_data["template_disabled"] = True
                    response_data["final_values"] = {}
                else:
                    # Get all overrides for this template (includes interpolation)
                    overrides = settings.get_all_overrides_for_template(template_slug)
                    response_data["resolved_for_template"] = overrides
                    response_data["template_disabled"] = False
                    
                    # Build final values (simulating what send_email_message would use)
                    final = {}
                    final.update(system_defaults)
                    final.update({k: v for k, v in academy_values.items() if v is not None})
                    final.update(overrides)
                    
                    response_data["final_values"] = final
            else:
                # No settings, just show academy model values over system defaults
                final = {}
                final.update(system_defaults)
                final.update({k: v for k, v in academy_values.items() if v is not None})
                response_data["final_values"] = final
                response_data["template_disabled"] = False

        return Response(response_data)
