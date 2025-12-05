"""
Webhook Events Metadata Configuration

This module contains the single source of truth for all webhook events in the BreatheCode API.
Most fields are auto-derived from the 'action' string for minimal configuration.

Required Fields:
  - action: Format "app.Model.signal_name" (e.g., "assignments.Task.assignment_created")
  - description: Human-readable description of when this webhook fires

Optional Fields (all auto-derived unless explicitly overridden):
  - model: Auto-derived as "app.Model" from action
  - app: Auto-derived as "app" from action (first part)
  - label: Auto-derived by de-slugifying third part (e.g., "assignment_created" → "Assignment Created")
  - signal: Auto-derived as "breathecode.app.signals.signal_name"
  - sender: Auto-derived as "breathecode.app.models.Model"
  - event_action: Auto-derived from action (third part, e.g., "signal_name")
  - serializer: Optional serializer import path for custom payload
  - auto_register: Set to False to prevent auto-registration (for manual receivers)

Minimal Example:
  "assignment.assignment_created": {
      "action": "assignments.Task.assignment_created",
      "description": "Triggered when a new assignment is created",
      # Everything else is auto-derived! Only 2 required fields.
  }

Auto-Derivation:
  From action "app.Model.signal_name", the system derives:
  - model → "app.Model"
  - app → "app"
  - label → "Signal Name" (de-slugified signal_name)
  - signal → "breathecode.app.signals.signal_name"
  - sender → "breathecode.app.models.Model"
  - event_action → "signal_name"
  - HOOK_EVENTS → Generated automatically (imported in settings.py)

Label Override Example:
  "cohort_user.edu_status_updated": {
      "action": "admissions.CohortUser.edu_status_updated",
      "description": "...",
      "label": "Student Status Updated",  # Override auto-derived "Edu Status Updated"
  }
"""

HOOK_EVENTS_METADATA = {
    # Student & Cohort Management (app & model auto-derived from action)
    "profile_academy.added": {
        "action": "authenticate.ProfileAcademy.created+",
        "label"
        "description": "Triggered when students or staff members are added to an academy",
        # All metadata auto-derived from action!
    },
    "profile_academy.changed": {
        "action": "authenticate.ProfileAcademy.updated+",
        "label": "Profile of user is updated in academy",
        "description": "Triggered when an academy member's profile is updated",
        # All metadata auto-derived from action!
    },
    "cohort_user.added": {
        "action": "admissions.CohortUser.created+",
        "label": "User is added to a cohort",  
        "description": "Its triggered when students or staff members are added to a cohort",
        # All metadata auto-derived from action!
    },
    "cohort_user.changed": {
        "action": "admissions.CohortUser.updated+",
        "label": "User-Cohort Record Updated",  
        "description": "Triggered when a cohort user record is updated",
        # All metadata auto-derived from action!
    },
    "cohort_user.edu_status_updated": {
        "action": "admissions.CohortUser.edu_status_updated",
        "description": "Triggered when a student's educational status changes (ACTIVE, GRADUATED, DROPPED, etc.)",
        "label": "Student Status Updated",  # Override auto-derived "Edu Status Updated"
        # Signal name doesn't match action - must be explicit
        "signal": "breathecode.admissions.signals.student_edu_status_updated",
        "serializer": "breathecode.admissions.serializers.CohortUserHookSerializer",
        # Manual receiver: has custom academy logic (cohort.academy instead of instance.academy)
        "auto_register": False,
    },
    "cohort.cohort_stage_updated": {
        "action": "admissions.Cohort.cohort_stage_updated",
        "description": "Triggered when a cohort's stage changes (INACTIVE, PREWORK, STARTED, FINAL_PROJECT, ENDED)",
        "serializer": "breathecode.admissions.serializers.CohortHookSerializer",
    },
    "user_invite.invite_status_updated": {
        "action": "authenticate.UserInvite.invite_status_updated",
        "description": "Triggered when an invitation status changes (accepted, rejected, etc.)",
        # All metadata auto-derived! Minimal 2-field configuration.
    },
    # Assignments & Learning (app auto-derived from action)
    "assignment.assignment_created": {
        "action": "assignments.Task.assignment_created",
        "description": "Triggered when a new assignment is created for a student",
        # app, signal, sender, event_action all auto-derived from action
        "serializer": "breathecode.assignments.serializers.TaskHookSerializer",
    },
    "assignment.assignment_status_updated": {
        "action": "assignments.Task.assignment_status_updated",
        "description": "Triggered when an assignment's task status changes (PENDING to DONE)",
        # app, signal, sender, event_action all auto-derived from action
        "serializer": "breathecode.assignments.serializers.TaskHookSerializer",
    },
    "assignment.assignment_revision_status_updated": {
        "action": "assignments.Task.assignment_revision_status_updated",
        "description": "Triggered when an assignment's revision status changes (PENDING, APPROVED, REJECTED)",
        # app auto-derived: "assignments"
        # Signal name doesn't match action - must be explicit
        "signal": "breathecode.assignments.signals.revision_status_updated",
        "serializer": "breathecode.assignments.serializers.TaskHookSerializer",
    },
    "asset.asset_status_updated": {
        "action": "registry.Asset.asset_status_updated",
        "description": "Triggered when a learning asset's status is updated",
        # app, signal, sender, event_action all auto-derived from action
        "serializer": "breathecode.registry.serializers.AssetHookSerializer",
    },
    # Assessments (app auto-derived from action)
    "UserAssessment.userassessment_status_updated": {
        "action": "assessment.UserAssessment.userassessment_status_updated",
        "description": "Triggered when a user assessment status is updated",
        # app, signal, sender, event_action all auto-derived from action
        "serializer": "breathecode.assessment.serializers.HookUserAssessmentSerializer",
    },
    # Events & Attendance (app auto-derived from action)
    "event.event_status_updated": {
        "action": "events.Event.event_status_updated",
        "description": "Triggered when an event's status changes",
        # app, signal, sender, event_action all auto-derived from action
        "serializer": "breathecode.events.serializers.EventJoinSmallSerializer",
    },
    "event.event_rescheduled": {
        "action": "events.Event.event_rescheduled",
        "description": "Triggered when an event's date or time is changed",
        # app, signal, sender, event_action all auto-derived from action
        "serializer": "breathecode.events.serializers.EventJoinSmallSerializer",
        # Manual receiver: has custom logic (builds bulk email payload with attendee list)
        "auto_register": False,
    },
    "event.new_event_order": {
        "action": "events.EventCheckin.new_event_order",
        "description": "Triggered when a new event registration/order is created",
        # app, signal, sender, event_action all auto-derived from action
        "serializer": "breathecode.events.serializers.EventHookCheckinSerializer",
    },
    "event.new_event_attendee": {
        "action": "events.EventCheckin.new_event_attendee",
        "description": "Triggered when a new attendee is added to an event",
        # app, signal, sender, event_action all auto-derived from action
        "serializer": "breathecode.events.serializers.EventHookCheckinSerializer",
    },
    # Marketing & Leads (app auto-derived from action)
    "form_entry.added": {
        "action": "marketing.FormEntry.created+",
        "description": "Triggered when a new lead/form submission is created",
        # app auto-derived: "marketing"
        # Auto-triggered by post_save signal
    },
    "form_entry.changed": {
        "action": "marketing.FormEntry.updated+",
        "description": "Triggered when a form entry is updated",
        # app auto-derived: "marketing"
        # Auto-triggered by post_save signal
    },
    "form_entry.won_or_lost": {
        "action": "marketing.FormEntry.won_or_lost",
        "description": "Triggered when a lead is marked as won or lost",
        # app auto-derived: "marketing"
        # Signal name doesn't match action - must be explicit
        "signal": "breathecode.marketing.signals.form_entry_won_or_lost",
        "serializer": "breathecode.marketing.serializers.FormEntryHookSerializer",
    },
    "form_entry.new_deal": {
        "action": "marketing.FormEntry.new_deal",
        "description": "Triggered when a new deal is created in the CRM",
        # app auto-derived: "marketing"
        # Signal name doesn't match action - must be explicit
        "signal": "breathecode.marketing.signals.new_form_entry_deal",
        "serializer": "breathecode.marketing.serializers.FormEntryHookSerializer",
    },
    # Payments & Subscriptions (app auto-derived from action)
    "planfinancing.planfinancing_created": {
        "action": "payments.PlanFinancing.planfinancing_created",
        "description": "Triggered when a new financing plan is created",
        # app, signal, sender, event_action all auto-derived from action
        "serializer": "breathecode.payments.serializers.GetPlanFinancingSerializer",
    },
    "subscription.subscription_created": {
        "action": "payments.Subscription.subscription_created",
        "description": "Triggered when a new subscription is created",
        # app, signal, sender, event_action all auto-derived from action
        "serializer": "breathecode.payments.serializers.GetSubscriptionHookSerializer",
    },
    # Mentorship (app auto-derived from action)
    "session.mentorship_session_status": {
        "action": "mentorship.MentorshipSession.mentorship_session_status",
        "description": "Triggered when a mentorship session status changes (PENDING, STARTED, COMPLETED, FAILED)",
        # app, signal, sender, event_action all auto-derived from action
        "serializer": "breathecode.mentorship.serializers.SessionHookSerializer",
        # Note: This receiver has custom logic, so it needs manual handling
        "auto_register": False,
    },
}

