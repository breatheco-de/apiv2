import logging

from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from breathecode.feedback.models import SurveyConfiguration, SurveyStudy, SurveyResponse

logger = logging.getLogger(__name__)


class SurveyManager:
    """
    Manager class for handling survey triggers and filtering logic.
    
    This class centralizes all survey triggering logic, making it easier to maintain
    and extend with new trigger types and filtering rules.
    """

    def __init__(self, user: User, trigger_type: str, context: dict):
        self.user = user
        self.trigger_type = trigger_type
        self.context = context or {}
        self.academy = None
        self.academy_source = None
        self.filtered_out = 0

    def trigger_survey_for_user(self) -> SurveyResponse | None:
        """
        Main method to trigger a survey for a user when a specific action is completed.

        Returns:
            SurveyResponse instance if created, None otherwise
        """
        if not self._validate_user():
            return None

        if not self._validate_trigger_type():
            return None

        logger.info(
            "[survey-trigger] start | user_id=%s trigger_type=%s context_keys=%s",
            self.user.id,
            self.trigger_type,
            sorted(list(self.context.keys())),
        )

        if not self._resolve_academy():
            return None

        survey_configs = SurveyConfiguration.objects.filter(
            trigger_type=self.trigger_type, is_active=True, academy=self.academy
        ).prefetch_related("cohorts", "survey_studies")

        if not survey_configs.exists():
            logger.info(
                "[survey-trigger] no active configs | user_id=%s trigger_type=%s academy_id=%s",
                self.user.id,
                self.trigger_type,
                self.academy.id,
            )
            return None

        study_configs_map = {}

        for survey_config in survey_configs:
            active_study = self._get_active_study(survey_config)
            if not active_study:
                continue

            if not self._apply_filters(survey_config, active_study):
                continue

            # Group by study
            if active_study.id not in study_configs_map:
                study_configs_map[active_study.id] = []
            study_configs_map[active_study.id].append((survey_config, active_study))

        # Sort configs within each study by config ID for consistent round-robin
        for study_id in study_configs_map:
            study_configs_map[study_id].sort(key=lambda x: x[0].id)

        if not study_configs_map:
            logger.info(
                "[survey-trigger] no active studies | user_id=%s trigger_type=%s academy_id=%s",
                self.user.id,
                self.trigger_type,
                self.academy.id,
            )
            return None

        for study_id, config_study_pairs in study_configs_map.items():
            active_study = config_study_pairs[0][1]

            existing_study_response = SurveyResponse.objects.filter(
                survey_study=active_study,
                user=self.user,
            ).exclude(status=SurveyResponse.Status.EXPIRED).first()

            if existing_study_response:
                logger.info(
                    "[survey-trigger] skip: user already has response for study | user_id=%s survey_study_id=%s survey_response_id=%s",
                    self.user.id,
                    active_study.id,
                    existing_study_response.id,
                )
                continue

            configs_for_study = [pair[0] for pair in config_study_pairs]
            
            # Round-robin based on last N responses (where N = number of configs)
            # This ensures true rotation: A → B → C → A → B → C...
            # Get the last N responses for this study to see which configs were used
            num_configs = len(configs_for_study)
            last_responses = list(
                SurveyResponse.objects.filter(
                    survey_study=active_study,
                )
                .exclude(status=SurveyResponse.Status.EXPIRED)
                .order_by("-created_at")
                .values_list("survey_config_id", flat=True)[:num_configs]
            )
            
            # Get config IDs in order (sorted for consistency)
            config_ids_ordered = sorted([config.id for config, _ in config_study_pairs])
            
            # Create a mapping of config_id to (config, study) for easy lookup
            config_map = {config.id: (config, study) for config, study in config_study_pairs}
            
            # Find which configs were used in the last N responses
            used_config_ids = set(last_responses)
            
            # Find the first config (in order) that wasn't used in the last N responses
            selected_config = None
            selected_study = None
            
            for config_id in config_ids_ordered:
                if config_id not in used_config_ids:
                    # This config wasn't used in the last N responses
                    selected_config, selected_study = config_map[config_id]
                    break
            
            # If all configs were used (we have exactly N responses), continue rotation
            # by selecting the next config after the most recent one
            if selected_config is None:
                # All configs were used, get the most recent response (first in last_responses)
                most_recent_config_id = last_responses[0] if last_responses else None
                
                if most_recent_config_id:
                    # Find the index of the most recent config in the ordered list
                    try:
                        current_index = config_ids_ordered.index(most_recent_config_id)
                        # Get the next config in rotation (wrap around if needed)
                        next_index = (current_index + 1) % len(config_ids_ordered)
                        next_config_id = config_ids_ordered[next_index]
                        selected_config, selected_study = config_map[next_config_id]
                    except ValueError:
                        # Config ID not found (shouldn't happen, but safety check)
                        first_config_id = config_ids_ordered[0]
                        selected_config, selected_study = config_map[first_config_id]
                else:
                    # No responses yet, start with first config
                    first_config_id = config_ids_ordered[0]
                    selected_config, selected_study = config_map[first_config_id]

            if self._check_deduplication(selected_config, selected_study):
                logger.info(
                    "[survey-trigger] skip: deduplication check failed | user_id=%s survey_config_id=%s survey_study_id=%s",
                    self.user.id,
                    selected_config.id,
                    selected_study.id,
                )
                continue

            survey_response = self._create_response(selected_config, selected_study)
            if survey_response:
                logger.info(
                    "[survey-trigger] created | user_id=%s survey_config_id=%s survey_study_id=%s survey_response_id=%s last_responses=%s total_configs=%s",
                    self.user.id,
                    selected_config.id,
                    selected_study.id,
                    survey_response.id,
                    list(last_responses),
                    len(configs_for_study),
                )
                return survey_response

        logger.info(
            "[survey-trigger] no response created | user_id=%s trigger_type=%s academy_id=%s studies_checked=%s filtered_out=%s",
            self.user.id,
            self.trigger_type,
            self.academy.id,
            len(study_configs_map),
            self.filtered_out,
        )
        return None

    def _validate_user(self) -> bool:
        """Validate that user is not None."""
        if not self.user:
            logger.warning("[survey-trigger] abort: user is None | trigger_type=%s", self.trigger_type)
            return False
        return True

    def _validate_trigger_type(self) -> bool:
        """Validate that trigger_type is valid."""
        valid_triggers = [choice[0] for choice in SurveyConfiguration.TriggerType.choices]
        if self.trigger_type not in valid_triggers:
            logger.warning(
                "[survey-trigger] abort: invalid trigger_type=%s valid_triggers=%s user_id=%s",
                self.trigger_type,
                valid_triggers,
                self.user.id,
            )
            return False
        return True

    def _resolve_academy(self) -> bool:
        """
        Resolve academy from context or user's profileacademy_set.
        
        Returns:
            True if academy was found, False otherwise
        """
        if "academy" in self.context and self.context["academy"] is not None:
            self.academy = self.context["academy"]
            self.academy_source = "context"
        elif hasattr(self.user, "profileacademy_set") and self.user.profileacademy_set.exists():
            self.academy = self.user.profileacademy_set.first().academy
            self.academy_source = "profileacademy_set.first"

        if not self.academy:
            logger.warning(
                "[survey-trigger] abort: no academy found | user_id=%s trigger_type=%s has_profileacademy=%s context_has_academy=%s",
                self.user.id,
                self.trigger_type,
                bool(getattr(self.user, "profileacademy_set", None) and self.user.profileacademy_set.exists()),
                "academy" in self.context,
            )
            return False

        logger.info(
            "[survey-trigger] academy resolved | user_id=%s academy_id=%s source=%s",
            self.user.id,
            self.academy.id,
            self.academy_source,
        )
        return True

    def _get_active_study(self, survey_config: SurveyConfiguration) -> SurveyStudy | None:
        """Get active SurveyStudy for the given survey_config."""
        utc_now = timezone.now()
        active_study = (
            SurveyStudy.objects.filter(
                academy=self.academy,
                survey_configurations=survey_config,
            )
            .filter(Q(starts_at__lte=utc_now) | Q(starts_at__isnull=True))
            .filter(Q(ends_at__gte=utc_now) | Q(ends_at__isnull=True))
            .order_by("-starts_at", "-id")
            .first()
        )

        if not active_study:
            logger.info(
                "[survey-trigger] skip: no active study | user_id=%s survey_config_id=%s trigger_type=%s academy_id=%s",
                self.user.id,
                survey_config.id,
                self.trigger_type,
                self.academy.id,
            )

        return active_study

    def _apply_filters(self, survey_config: SurveyConfiguration, active_study: SurveyStudy) -> bool:
        """
        Apply all filters for the survey configuration.
        
        Returns:
            True if survey_config passes all filters, False otherwise
        """
        # Filter by syllabus/module for module and syllabus completion
        if self.trigger_type in (
            SurveyConfiguration.TriggerType.MODULE_COMPLETION,
            SurveyConfiguration.TriggerType.SYLLABUS_COMPLETION,
        ):
            if not self._filter_by_syllabus_module(survey_config):
                return False

        # Filter by cohort for course completion
        if self.trigger_type == SurveyConfiguration.TriggerType.COURSE_COMPLETION:
            if not self._filter_by_cohort(survey_config):
                return False

        # Filter by cohort for module and syllabus completion
        elif self.trigger_type in (
            SurveyConfiguration.TriggerType.MODULE_COMPLETION,
            SurveyConfiguration.TriggerType.SYLLABUS_COMPLETION,
        ):
            if not self._filter_by_cohort(survey_config):
                return False

        # Filter by asset_slug for learnpack completion
        elif self.trigger_type == SurveyConfiguration.TriggerType.LEARNPACK_COMPLETION:
            if not self._filter_by_asset_slug(survey_config):
                return False

        return True

    def _filter_by_syllabus_module(self, survey_config: SurveyConfiguration) -> bool:
        """Filter by syllabus slug, version, and module."""
        syllabus_filter = survey_config.syllabus or {}
        if not syllabus_filter:
            return True

        # Filter by syllabus slug
        config_syllabus_slug = syllabus_filter.get("syllabus")
        context_syllabus_slug = self.context.get("syllabus_slug")
        if config_syllabus_slug and context_syllabus_slug:
            if config_syllabus_slug != context_syllabus_slug:
                self.filtered_out += 1
                logger.info(
                    "[survey-trigger] filtered by syllabus_slug | user_id=%s survey_config_id=%s config_syllabus=%s context_syllabus=%s academy_id=%s",
                    self.user.id,
                    survey_config.id,
                    config_syllabus_slug,
                    context_syllabus_slug,
                    self.academy.id,
                )
                return False

        # Filter by syllabus version
        config_version = syllabus_filter.get("version")
        context_version = self.context.get("syllabus_version")
        if config_version is not None and context_version is not None:
            if config_version != context_version:
                self.filtered_out += 1
                logger.info(
                    "[survey-trigger] filtered by syllabus_version | user_id=%s survey_config_id=%s config_version=%s context_version=%s academy_id=%s",
                    self.user.id,
                    survey_config.id,
                    config_version,
                    context_version,
                    self.academy.id,
                )
                return False

        # Filter by module (only for module_completion)
        if self.trigger_type == SurveyConfiguration.TriggerType.MODULE_COMPLETION:
            config_module = syllabus_filter.get("module")
            context_module = self.context.get("module")
            if config_module is not None and context_module is not None:
                if config_module != context_module:
                    self.filtered_out += 1
                    logger.info(
                        "[survey-trigger] filtered by module | user_id=%s survey_config_id=%s config_module=%s context_module=%s academy_id=%s",
                        self.user.id,
                        survey_config.id,
                        config_module,
                        context_module,
                        self.academy.id,
                    )
                    return False

        return True

    def _filter_by_cohort(self, survey_config: SurveyConfiguration) -> bool:
        """Filter by cohort."""
        cohort = self.context.get("cohort")
        if not cohort:
            return True

        # If cohorts filter is set, check if this cohort is in the list
        if survey_config.cohorts.exists():
            if cohort not in survey_config.cohorts.all():
                self.filtered_out += 1
                logger.info(
                    "[survey-trigger] filtered by cohort (%s) | user_id=%s survey_config_id=%s cohort_id=%s academy_id=%s",
                    self.trigger_type,
                    self.user.id,
                    survey_config.id,
                    getattr(cohort, "id", None),
                    self.academy.id,
                )
                return False

        # If cohorts filter is empty, apply to all cohorts
        return True

    def _filter_by_asset_slug(self, survey_config: SurveyConfiguration) -> bool:
        """Filter by asset_slug for learnpack completion."""
        asset_slug = self.context.get("asset_slug")
        if not asset_slug:
            return True

        if survey_config.asset_slugs:
            if asset_slug not in survey_config.asset_slugs:
                self.filtered_out += 1
                logger.info(
                    "[survey-trigger] filtered by asset_slug | user_id=%s survey_config_id=%s asset_slug=%s academy_id=%s",
                    self.user.id,
                    survey_config.id,
                    asset_slug,
                    self.academy.id,
                )
                return False

        return True

    def _check_deduplication(self, survey_config: SurveyConfiguration, active_study: SurveyStudy) -> bool:
        """
        Check if user already has a response for this config+trigger.
        
        Returns:
            True if duplicate exists (should skip), False otherwise
        """
        dedupe_query = SurveyResponse.objects.filter(
            survey_config=survey_config,
            user=self.user,
            survey_study=active_study,
            trigger_context__trigger_type=self.trigger_type,
        ).exclude(status=SurveyResponse.Status.EXPIRED)

        # Add trigger-specific deduplication filters
        if self.trigger_type == SurveyConfiguration.TriggerType.COURSE_COMPLETION:
            cohort_id = self.context.get("cohort_id")
            cohort = self.context.get("cohort")
            if cohort_id is None and cohort is not None:
                cohort_id = getattr(cohort, "id", None)

            if cohort_id is not None:
                dedupe_query = dedupe_query.filter(trigger_context__cohort_id=cohort_id)

        elif self.trigger_type == SurveyConfiguration.TriggerType.SYLLABUS_COMPLETION:
            syllabus_slug = self.context.get("syllabus_slug")
            version = self.context.get("syllabus_version")
            cohort_id = self.context.get("cohort_id") or getattr(self.context.get("cohort"), "id", None)
            if syllabus_slug is not None:
                dedupe_query = dedupe_query.filter(trigger_context__syllabus_slug=syllabus_slug)
            if version is not None:
                dedupe_query = dedupe_query.filter(trigger_context__syllabus_version=version)
            if cohort_id is not None:
                dedupe_query = dedupe_query.filter(trigger_context__cohort_id=cohort_id)

        elif self.trigger_type == SurveyConfiguration.TriggerType.MODULE_COMPLETION:
            syllabus_slug = self.context.get("syllabus_slug")
            version = self.context.get("syllabus_version")
            module = self.context.get("module")
            cohort_id = self.context.get("cohort_id") or getattr(self.context.get("cohort"), "id", None)
            if syllabus_slug is not None:
                dedupe_query = dedupe_query.filter(trigger_context__syllabus_slug=syllabus_slug)
            if version is not None:
                dedupe_query = dedupe_query.filter(trigger_context__syllabus_version=version)
            if module is not None:
                dedupe_query = dedupe_query.filter(trigger_context__module=module)
            if cohort_id is not None:
                dedupe_query = dedupe_query.filter(trigger_context__cohort_id=cohort_id)

        existing_response = dedupe_query.first()

        if existing_response:
            logger.info(
                "[survey-trigger] skip: existing response | user_id=%s survey_config_id=%s survey_response_id=%s status=%s",
                self.user.id,
                survey_config.id,
                existing_response.id,
                existing_response.status,
            )
            return True

        return False

    def _create_response(self, survey_config: SurveyConfiguration, active_study: SurveyStudy) -> SurveyResponse | None:
        """Create survey response for the user."""
        # Import here to avoid circular import
        from breathecode.feedback.actions import create_survey_response

        return create_survey_response(survey_config, self.user, self.context, survey_study=active_study)

