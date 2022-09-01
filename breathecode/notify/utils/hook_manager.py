import logging
from django.conf import settings
from ..tasks import async_deliver_hook
from django.apps import apps as django_apps
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class HookManagerClass(object):
    _HOOK_EVENT_ACTIONS_CONFIG = None
    HOOK_EVENTS = {}

    def __init__(self):
        self.HOOK_EVENTS = getattr(settings, 'HOOK_EVENTS', None)
        if self.HOOK_EVENTS is None:
            raise Exception('You need to define settings.HOOK_EVENTS!')

    def get_event_actions_config(self):
        if self._HOOK_EVENT_ACTIONS_CONFIG is None:
            self._HOOK_EVENT_ACTIONS_CONFIG = {}
            for event_name, auto in self.HOOK_EVENTS.items():
                if not auto:
                    continue
                model_label, action = auto.rsplit('.', 1)
                action_parts = action.rsplit('+', 1)
                action = action_parts[0]
                ignore_user_override = False
                if len(action_parts) == 2:
                    ignore_user_override = True

                model_config = self._HOOK_EVENT_ACTIONS_CONFIG.setdefault(model_label, {})
                if action in model_config:
                    raise ImproperlyConfigured('settings.HOOK_EVENTS have a dublicate {action} for model '
                                               '{model_label}'.format(action=action, model_label=model_label))
                model_config[action] = (
                    event_name,
                    ignore_user_override,
                )
        return self._HOOK_EVENT_ACTIONS_CONFIG

    def get_module(self, path):
        """
        A modified duplicate from Django's built in backend
        retriever.
            slugify = get_module('django.template.defaultfilters.slugify')
        """
        try:
            from importlib import import_module
        except ImportError as e:
            from django.utils.importlib import import_module

        try:
            mod_name, func_name = path.rsplit('.', 1)
            mod = import_module(mod_name)
        except ImportError as e:
            raise ImportError('Error importing alert function {0}: "{1}"'.format(mod_name, e))

        try:
            func = getattr(mod, func_name)
        except AttributeError:
            raise ImportError(('Module "{0}" does not define a "{1}" function').format(mod_name, func_name))

        return func

    def get_hook_model(self):
        """
        Returns the Custom Hook model if defined in settings,
        otherwise the default Hook model.
        """
        model_label = getattr(settings, 'HOOK_CUSTOM_MODEL', None)
        if django_apps:
            model_label = (model_label or 'notify.Hook').replace('.models.', '.')
            try:
                return django_apps.get_model(model_label, require_ready=False)
            except ValueError:
                raise ImproperlyConfigured(
                    f"Invalid model {model_label}, HOOK_CUSTOM_MODEL must be of the form 'app_label.model_name'"
                )
            except LookupError:
                raise ImproperlyConfigured(
                    "HOOK_CUSTOM_MODEL refers to model '%s' that has not been installed" % model_label)
        else:
            if model_label in (None, 'notify.Hook'):
                from rest_hooks.models import Hook
                HookModel = Hook
            else:
                try:
                    HookModel = self.get_module(settings.HOOK_CUSTOM_MODEL)
                except ImportError:
                    raise ImproperlyConfigured(
                        "HOOK_CUSTOM_MODEL refers to model '%s' that cannot be imported" % model_label)
            return

    def find_and_fire_hook(self, event_name, instance, user_override=None, payload_override=None):
        """
        Look up Hooks that apply
        """
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
        except ImportError:
            from django.contrib.auth.models import User

        if event_name not in self.HOOK_EVENTS.keys():
            raise Exception('"{}" does not exist in `settings.HOOK_EVENTS`.'.format(event_name))

        filters = {'event': event_name}

        # only process hooks from instances from the same academy
        if hasattr(instance, 'academy') and instance.academy is not None:
            superadmins = User.objects.filter(is_superuser=True).values_list('username', flat=True)
            filters['user__username__in'] = [instance.academy.slug] + list(superadmins)
        else:
            logger.debug(
                f'Only admin will receive hook notification for {event_name} because entity has not academy property'
            )
            # Only the admin can retrieve events from objects that don't belong to any academy
            filters['user__is_superuser'] = True

        # Ignore the user if the user_override is False
        if user_override is not False:
            if user_override:
                filters['user'] = user_override
            elif hasattr(instance, 'user'):
                filters['user'] = instance.user
            elif isinstance(instance, User):
                filters['user'] = instance
            else:
                raise Exception('{} has no `user` property. REST Hooks needs this.'.format(repr(instance)))

        HookModel = self.get_hook_model()
        hooks = HookModel.objects.filter(**filters)
        print('filters', filters)
        for hook in hooks:
            self.deliver_hook(hook, instance, payload_override=payload_override)

    def process_model_event(
        self,
        instance,
        model=False,
        action=False,
        user_override=None,
        event_name=False,
        trust_event_name=False,
        payload_override=None,
    ):
        """
        Take `event_name` or determine it using action and model
        from settings.HOOK_EVENTS, and let hooks fly.
        if `event_name` is passed together with `model` or `action`, then
        they should be the same as in settings or `trust_event_name` should be
        `True`
        If event_name is not found or is invalidated, then just quit silently.
        If payload_override is passed, then it will be passed into HookModel.deliver_hook
        """

        if event_name is False and (model is False or action is False):
            raise TypeError('process_model_event() requires either `event_name` argument or '
                            'both `model` and `action` arguments.')
        if event_name:
            if trust_event_name:
                pass
            elif event_name in self.HOOK_EVENTS:
                auto = self.HOOK_EVENTS[event_name]
                if auto:
                    allowed_model, allowed_action = auto.rsplit('.', 1)

                    allowed_action_parts = allowed_action.rsplit('+', 1)
                    allowed_action = allowed_action_parts[0]

                    model = model or allowed_model
                    action = action or allowed_action

                    if not (model == allowed_model and action == allowed_action):
                        event_name = None

                    if len(allowed_action_parts) == 2:
                        user_override = False
        else:
            event_actions_config = self.get_event_actions_config()
            event_name, ignore_user_override = event_actions_config.get(model, {}).get(action, (None, False))
            if ignore_user_override:
                user_override = False

        if event_name:
            logger.debug(f'process_model_event for event_name={event_name}')
            self.find_and_fire_hook(event_name,
                                    instance,
                                    user_override=user_override,
                                    payload_override=payload_override)

    def deliver_hook(self, hook, instance, payload_override=None):
        """
        Deliver the payload to the target URL.
        By default it serializes to JSON and POSTs.
        Args:
            instance: instance that triggered event.
            payload_override: JSON-serializable object or callable that will
                return such object. If callable is used it should accept 2
                arguments: `hook` and `instance`.
        """
        if payload_override is None:
            payload = hook.serialize_hook(instance)
        else:
            payload = payload_override

        if callable(payload):
            payload = payload(hook, instance)

        logger.debug(f'Calling delayed task deliver_hook for hook {hook.id}')
        async_deliver_hook.delay(hook.target, payload, hook_id=hook.id)

        return None


HookManager = HookManagerClass()
