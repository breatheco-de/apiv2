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

        for study_id in study_configs_map:
            def get_module_for_sorting(config_study_pair):
                config = config_study_pair[0]
                module = (config.syllabus or {}).get("module")
                if module is None:
                    return 0
                return module
            
            study_configs_map[study_id].sort(key=get_module_for_sorting)

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

            context_module = self.context.get("module") if isinstance(self.context, dict) else None
            
            def get_module(config_study_pair):
                config = config_study_pair[0]
                module = (config.syllabus or {}).get("module")
                return module if module is not None else 0
            
            if self.trigger_type == SurveyConfiguration.TriggerType.MODULE_COMPLETION:
                all_study_configs = sorted(config_study_pairs, key=get_module)
            else:
                all_study_configs = config_study_pairs
            
            eligible_configs = []
            for config, study in all_study_configs:
                if not self._apply_filters(config, study):
                    continue
                
                config_module = get_module((config, study))
                
                if self.trigger_type == SurveyConfiguration.TriggerType.MODULE_COMPLETION:
                    if context_module is not None:
                        if config_module > context_module:
                            continue
                    elif config_module is not None:
                        continue
                
                eligible_configs.append((config, study))
            
            if not eligible_configs:
                logger.info(
                    "[survey-trigger] skip: no eligible configs for context | user_id=%s trigger_type=%s study_id=%s module=%s",
                    self.user.id,
                    self.trigger_type,
                    active_study.id,
                    context_module,
                )
                continue
            
            # Conditional Hazard-Based Sampling ONLY for MODULE_COMPLETION
            # For other triggers, each configuration is independent
            if self.trigger_type == SurveyConfiguration.TriggerType.MODULE_COMPLETION:
                # Use conditional hazard-based sampling with cumulative priorities
                previous_priority = 0.0
                
                for config, study in eligible_configs:
                    config_module = get_module((config, study))
                    
                    current_priority = config.priority if config.priority is not None else 100.0
                    
                    if previous_priority >= 100.0:
                        conditional_probability = 0.0
                    elif previous_priority >= current_priority:
                        conditional_probability = 0.0
                    else:
                        conditional_probability = (current_priority - previous_priority) / (100.0 - previous_priority)
                    
                    hash_input = f"{self.user.id}_{active_study.id}_{config_module}"
                    hash_value = hash(hash_input)
                    random_value = abs(hash_value) % 100
                    
                    conditional_probability_percent = conditional_probability * 100.0
                    
                    if random_value >= conditional_probability_percent:
                        logger.info(
                            "[survey-trigger] skip: conditional probability | user_id=%s survey_config_id=%s module=%s current_priority=%s prev_priority=%s conditional_prob=%s random_value=%s",
                            self.user.id,
                            config.id,
                            config_module,
                            current_priority,
                            previous_priority,
                            conditional_probability_percent,
                            random_value,
                        )
                        previous_priority = current_priority
                        continue
                    
                    if self._check_deduplication(config, active_study):
                        logger.info(
                            "[survey-trigger] skip: deduplication check failed | user_id=%s survey_config_id=%s survey_study_id=%s",
                            self.user.id,
                            config.id,
                            active_study.id,
                        )
                        previous_priority = current_priority
                        continue
                    
                    survey_response = self._create_response(config, active_study)
                    if survey_response:
                        logger.info(
                            "[survey-trigger] created | user_id=%s survey_config_id=%s survey_study_id=%s survey_response_id=%s module=%s current_priority=%s prev_priority=%s conditional_prob=%s",
                            self.user.id,
                            config.id,
                            active_study.id,
                            survey_response.id,
                            config_module,
                            current_priority,
                            previous_priority,
                            conditional_probability_percent,
                        )
                        return survey_response
                    
                    previous_priority = current_priority
            else:
                # For non-module triggers: use first eligible config (each config is independent)
                # Priority field is ignored for non-module triggers
                for config, study in eligible_configs:
                    if self._check_deduplication(config, active_study):
                        logger.info(
                            "[survey-trigger] skip: deduplication check failed | user_id=%s survey_config_id=%s survey_study_id=%s",
                            self.user.id,
                            config.id,
                            active_study.id,
                        )
                        continue
                    
                    survey_response = self._create_response(config, active_study)
                    if survey_response:
                        logger.info(
                            "[survey-trigger] created | user_id=%s survey_config_id=%s survey_study_id=%s survey_response_id=%s trigger_type=%s",
                            self.user.id,
                            config.id,
                            active_study.id,
                            survey_response.id,
                            self.trigger_type,
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
        from breathecode.feedback.actions import create_survey_response

        return create_survey_response(survey_config, self.user, self.context, survey_study=active_study)

