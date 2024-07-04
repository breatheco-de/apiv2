from typing import TypedDict
from django.core.management.base import BaseCommand
from ...models import Capability, Role

CAPABILITIES = [
    {"slug": "read_my_academy", "description": "Read your academy information"},
    {
        "slug": "crud_my_academy",
        "description": "Read, or update your academy information (very high level, almost the academy admin)",
    },
    {
        "slug": "crud_member",
        "description": "Create, update or delete academy members (very high level, almost the academy admin)",
    },
    {"slug": "read_member", "description": "Read academy staff member information"},
    {"slug": "crud_student", "description": "Create, update or delete students"},
    {"slug": "read_student", "description": "Read student information"},
    {"slug": "read_invite", "description": "Read invites from users"},
    {"slug": "crud_invite", "description": "Create, update or delete invites from users"},
    {"slug": "invite_resend", "description": "Resent invites for user academies"},
    {"slug": "read_assignment", "description": "Read assignment information"},
    {
        "slug": "read_assignment_sensitive_details",
        "description": 'The mentor in residence is allowed to see aditional info about the task, like the "delivery url"',
    },
    {"slug": "read_shortlink", "description": "Access the list of marketing shortlinks"},
    {"slug": "crud_shortlink", "description": "Create, update and delete marketing short links"},
    {"slug": "crud_assignment", "description": "Update assignments"},
    {
        "slug": "task_delivery_details",
        "description": "Get delivery URL for a task, that url can be sent to students for delivery",
    },
    {"slug": "read_certificate", "description": "List and read all academy certificates"},
    {"slug": "crud_certificate", "description": "Create, update or delete student certificates"},
    {"slug": "read_layout", "description": "Read layouts to generate new certificates"},
    {"slug": "read_syllabus", "description": "List and read syllabus information"},
    {"slug": "crud_syllabus", "description": "Create, update or delete syllabus versions"},
    {"slug": "read_organization", "description": "Read academy organization details"},
    {"slug": "crud_organization", "description": "Update, create or delete academy organization details"},
    {"slug": "read_event", "description": "List and retrieve event information"},
    {"slug": "crud_event", "description": "Create, update or delete event information"},
    {"slug": "read_event_type", "description": "List and retrieve event type information"},
    {"slug": "crud_event_type", "description": "Create, update or delete event type information"},
    {"slug": "read_all_cohort", "description": "List all the cohorts or single cohort information"},
    {"slug": "read_single_cohort", "description": "single cohort information related to a user"},
    {"slug": "crud_cohort", "description": "Create, update or delete cohort info"},
    {"slug": "read_eventcheckin", "description": "List and read all the event_checkins"},
    {"slug": "read_survey", "description": "List all the nps answers"},
    {"slug": "crud_survey", "description": "Create, update or delete surveys"},
    {"slug": "read_nps_answers", "description": "List all the nps answers"},
    {"slug": "read_lead", "description": "List all the leads"},
    {"slug": "read_won_lead", "description": "List all the won leads"},
    {"slug": "crud_lead", "description": "Create, update or delete academy leads"},
    {"slug": "read_review", "description": "Read review for a particular academy"},
    {"slug": "crud_review", "description": "Create, update or delete academy reviews"},
    {"slug": "read_media", "description": "List all the medias"},
    {"slug": "crud_media", "description": "Create, update or delete academy medias"},
    {"slug": "read_media_resolution", "description": "List all the medias resolutions"},
    {"slug": "crud_media_resolution", "description": "Create, update or delete academy media resolutions"},
    {"slug": "read_cohort_activity", "description": "Read low level activity in a cohort (attendancy, etc.)"},
    {"slug": "generate_academy_token", "description": "Create a new token only to be used by the academy"},
    {"slug": "get_academy_token", "description": "Read the academy token"},
    {"slug": "send_reset_password", "description": "Generate a temporal token and resend forgot password link"},
    {"slug": "read_activity", "description": "List all the user activities"},
    {"slug": "crud_activity", "description": "Create, update or delete a user activities"},
    {"slug": "read_assignment", "description": "List all the assignments"},
    {"slug": "crud_assignment", "description": "Create, update or delete a assignment"},
    {
        "slug": "classroom_activity",
        "description": "To report student activities during the classroom or cohorts (Specially meant for teachers)",
    },
    {"slug": "academy_reporting", "description": "Get detailed reports about the academy activity"},
    {
        "slug": "generate_temporal_token",
        "description": "Generate a temporal token to reset github credential or forgot password",
    },
    {"slug": "read_mentorship_service", "description": "Get all mentorship services from one academy"},
    {
        "slug": "crud_mentorship_service",
        "description": "Create, delete or update all mentorship services from one academy",
    },
    {"slug": "read_mentorship_agent", "description": "Get all mentorship agents from one academy"},
    {"slug": "read_mentorship_mentor", "description": "Get all mentorship mentors from one academy"},
    {
        "slug": "crud_mentorship_mentor",
        "description": "Create, delete or update all mentorship mentors from one academy",
    },
    {"slug": "read_mentorship_session", "description": "Get all session from one academy"},
    {"slug": "crud_mentorship_session", "description": "Create, delete or update all session from one academy"},
    {"slug": "crud_freelancer_bill", "description": "Create, delete or update all freelancer bills from one academy"},
    {"slug": "read_freelancer_bill", "description": "Read all all freelancer bills from one academy"},
    {"slug": "crud_mentorship_bill", "description": "Create, delete or update all mentroship bills from one academy"},
    {"slug": "read_mentorship_bill", "description": "Read all mentroship bills from one academy"},
    {"slug": "read_asset", "description": "Read all academy registry assets"},
    {"slug": "crud_asset", "description": "Update, create and delete registry assets"},
    {"slug": "read_content_variables", "description": "Read all academy content variables used in the asset markdowns"},
    {
        "slug": "crud_content_variables",
        "description": "Update, create and delete content variables used in the asset markdowns",
    },
    {"slug": "read_tag", "description": "Read marketing tags and their details"},
    {"slug": "crud_tag", "description": "Update, create and delete a marketing tag and its details"},
    {"slug": "get_gitpod_user", "description": "List gitpod user the academy is consuming"},
    {"slug": "update_gitpod_user", "description": "Update gitpod user expiration based on available information"},
    {"slug": "get_github_user", "description": "List github user the academy is consuming"},
    {"slug": "update_github_user", "description": "Update github user expiration based on available information"},
    {
        "slug": "sync_organization_users",
        "description": "Calls for the github API and brings all org users, then tries to synch them",
    },
    {"slug": "read_technology", "description": "Read asset technologies"},
    {"slug": "crud_technology", "description": "Update, create and delete asset technologies"},
    {"slug": "read_keyword", "description": "Read SEO keywords"},
    {"slug": "crud_keyword", "description": "Update, create and delete SEO keywords"},
    {"slug": "read_keywordcluster", "description": "Update, create and delete asset technologies"},
    {"slug": "crud_keywordcluster", "description": "Update, create and delete asset technologies"},
    {
        "slug": "read_cohort_log",
        "description": "Read the cohort logo that contains attendance and other info logged each day",
    },
    {
        "slug": "crud_cohort_log",
        "description": "Update and delete things like the cohort attendance, teacher comments, etc",
    },
    {"slug": "read_category", "description": "Read categories from the content registry"},
    {"slug": "crud_category", "description": "Update and delete categories from the content registry"},
    {"slug": "read_project_invoice", "description": "Read the financial status of a project and invoices"},
    {"slug": "crud_project_invoice", "description": "Create, Update and delete project invoices"},
    {"slug": "read_freelance_projects", "description": "Read project details without financials"},
    {"slug": "read_lead_gen_app", "description": "Read lead generation apps"},
    {"slug": "chatbot_message", "description": "Speak with a chatbot"},
    {"slug": "start_or_end_class", "description": "start or end a class"},
    {
        "slug": "get_academy_auth_settings",
        "description": "Settings related to authentication, for example the github auth integration",
    },
    {
        "slug": "crud_academy_auth_settings",
        "description": "Settings related to authentication, for example the github auth integration",
    },
    {"slug": "start_or_end_event", "description": "Start or end event"},
    {"slug": "read_provisioning_bill", "description": "Read provisioning activities and bills"},
    {"slug": "crud_provisioning_activity", "description": "Create, update or delete provisioning activities"},
    {"slug": "read_service", "description": "Read service details"},
    {"slug": "read_academyservice", "description": "Read Academy Service details"},
    {"slug": "crud_academyservice", "description": "Crud Academy Service details"},
    {
        "slug": "crud_provisioning_bill",
        "description": "Crud Provisioning Bills",
    },
    {"slug": "read_calendly_organization", "description": "Access info about the calendly integration"},
    {"slug": "create_calendly_organization", "description": "Add a new calendly integration"},
    {"slug": "reset_calendly_organization", "description": "Reset the calendly token"},
    {"slug": "delete_calendly_organization", "description": "Delete calendly integration"},
    {"slug": "crud_assessment", "description": "Manage student quizzes and assessments"},
    {"slug": "read_user_assessment", "description": "Read user assessment submissions"},
]

ROLES = [
    {
        "slug": "admin",
        "name": "Admin",
        "caps": [c["slug"] for c in CAPABILITIES],
    },
    {
        "slug": "academy_token",
        "name": "Academy Token",
        "caps": [
            "read_member",
            "read_syllabus",
            "read_student",
            "read_all_cohort",
            "read_media",
            "read_my_academy",
            "read_invite",
            "read_lead",
            "crud_lead",
            "crud_tag",
            "read_tag",
            "read_technology",
            "read_review",
            "read_shortlink",
            "read_nps_answers",
            "read_won_lead",
            "read_asset",
            "read_category",
            "read_cohort_log",
            "read_lead_gen_app",
            "read_mentorship_service",
            "read_mentorship_mentor",
            "read_freelancer_bill",
            "read_keywordcluster",
            "crud_academyservice",
            "crud_event",
            "crud_mentorship_session",
            "read_calendly_organization",
        ],
    },
    {
        "slug": "basic",
        "name": "Basic (Base)",
        "caps": [
            "read_media",
            "read_my_academy",
            "read_invite",
            "crud_activity",
            "read_tag",
            "academy_reporting",
            "read_activity",
            "read_technology",
            "read_academyservice",
        ],
    },
    {
        "slug": "read_only",
        "name": "Read Only (Base)",
        "caps": [
            "read_academyservice",
            "read_member",
            "read_syllabus",
            "read_student",
            "read_all_cohort",
            "read_media",
            "read_my_academy",
            "read_invite",
            "read_survey",
            "read_tag",
            "read_layout",
            "read_event",
            "read_event_type",
            "read_certificate",
            "read_won_lead",
            "read_eventcheckin",
            "read_review",
            "read_activity",
            "read_shortlink",
            "read_mentorship_service",
            "read_mentorship_mentor",
            "read_lead_gen_app",
            "read_technology",
            "read_service",
        ],
    },
    {
        "slug": "staff",
        "name": "Staff (Base)",
        "caps": [
            "chatbot_message",
            "read_member",
            "read_syllabus",
            "read_student",
            "read_all_cohort",
            "read_media",
            "read_my_academy",
            "read_invite",
            "get_academy_token",
            "crud_activity",
            "read_survey",
            "read_tag",
            "read_layout",
            "read_event",
            "read_event_type",
            "read_certificate",
            "academy_reporting",
            "crud_media",
            "read_won_lead",
            "read_eventcheckin",
            "read_review",
            "read_activity",
            "read_shortlink",
            "read_mentorship_service",
            "read_mentorship_mentor",
            "read_lead_gen_app",
            "read_technology",
            "read_service",
        ],
    },
    {
        "slug": "student",
        "name": "Student",
        "caps": [
            "crud_assignment",
            "chatbot_message",
            "read_syllabus",
            "read_assignment",
            "read_single_cohort",
            "read_my_academy",
            "read_all_cohort",
            "crud_activity",
            "read_mentorship_service",
            "read_mentorship_mentor",
            "read_cohort_log",
            "read_service",
            "read_academyservice",
        ],
    },
]


def extend(roles, slugs):
    caps_groups = [item["caps"] for item in roles if item["slug"] in slugs]
    inhered_caps = []
    for roles in caps_groups:
        inhered_caps = inhered_caps + roles
    return list(dict.fromkeys(inhered_caps))


def remove_duplicates(slugs):
    return list(dict.fromkeys(slugs))


# this function is used to can mock the list of capabilities
def get_capabilities():
    # prevent edit the constant
    return CAPABILITIES.copy()


# this function is used to can mock the list of roles
def get_roles():
    # prevent edit the constant
    return ROLES.copy()


class RoleType(TypedDict):
    slug: str
    name: str
    caps: list[str]


# this function is used to can mock the list of roles
def extend_roles(roles: list[RoleType]) -> None:
    """
    These are additional roles that extend from the base roles above,
    you can extend from more than one role but also add additional capabilities at the end.
    """

    roles.append(
        {
            "slug": "content_writer",
            "name": "Content Writer",
            "caps": extend(roles, ["basic"])
            + [
                "read_keywordcluster",
                "read_member",
                "read_media",
                "read_keyword",
                "read_my_academy",
                "read_asset",
                "crud_asset",
                "read_category",
                "crud_category",
                "read_content_variables",
                "crud_content_variables",
                "crud_assessment",
            ],
        }
    )

    roles.append(
        {
            "slug": "assistant",
            "name": "Teacher Assistant",
            "caps": extend(roles, ["staff"])
            + [
                "read_assignment",
                "crud_assignment",
                "read_cohort_activity",
                "read_nps_answers",
                "classroom_activity",
                "read_event",
                "read_event_type",
                "task_delivery_details",
                "crud_cohort",
                "read_cohort_log",
                "crud_cohort_log",
                "start_or_end_class",
                "start_or_end_event",
                "read_user_assessment",
            ],
        }
    )
    roles.append(
        {
            "slug": "career_support",
            "name": "Career Support Specialist",
            "caps": extend(roles, ["staff"])
            + [
                "read_certificate",
                "crud_certificate",
                "crud_shortlink",
                "read_mentorship_mentor",
                "crud_mentorship_mentor",
                "read_mentorship_service",
                "crud_mentorship_service",
                "read_mentorship_session",
                "crud_mentorship_session",
                "read_assignment",
                "crud_assignment",
                "crud_mentorship_bill",
                "read_mentorship_bill",
                "classroom_activity",
                "read_asset",
                "task_delivery_details",
            ],
        }
    )
    roles.append(
        {
            "slug": "career_support_head",
            "name": "Career Support Head",
            "caps": extend(roles, ["career_support", "content_writer"]) + ["crud_syllabus"],
        }
    )
    roles.append(
        {
            "slug": "admissions_developer",
            "name": "Admissions Developer",
            "caps": extend(roles, ["staff"])
            + [
                "crud_lead",
                "crud_student",
                "crud_cohort",
                "read_all_cohort",
                "read_lead",
                "read_activity",
                "invite_resend",
            ],
        }
    )
    roles.append(
        {
            "slug": "syllabus_coordinator",
            "name": "Syllabus Coordinator",
            "caps": extend(roles, ["staff", "content_writer"])
            + ["crud_syllabus", "crud_media", "crud_technology", "read_freelancer_bill", "crud_freelancer_bill"],
        }
    )
    roles.append(
        {
            "slug": "culture_and_recruitment",
            "name": "Culture and Recruitment",
            "caps": extend(roles, ["staff"]) + ["crud_member", "crud_media"],
        }
    )
    roles.append(
        {
            "slug": "graphic_designer",
            "name": "Graphic Designer",
            "caps": extend(roles, ["staff"])
            + ["read_event", "read_event_type", "crud_media", "read_asset", "read_media"],
        }
    )
    roles.append(
        {
            "slug": "community_manager",
            "name": "Manage Syllabus, Exercises and all academy content",
            "caps": extend(roles, ["staff", "graphic_designer"])
            + [
                "crud_lead",
                "crud_event",
                "crud_event_type",
                "read_eventcheckin",
                "read_nps_answers",
                "read_lead",
                "read_all_cohort",
                "crud_asset",
                "read_keywordcluster",
                "read_keyword",
            ],
        }
    )
    roles.append(
        {
            "slug": "growth_manager",
            "name": "Growth Manager",
            "caps": extend(roles, ["staff", "community_manager"])
            + [
                "crud_media",
                "read_activity",
                "read_lead",
                "read_user_assessment",
                "read_won_lead",
                "crud_review",
                "crud_shortlink",
                "crud_tag",
                "crud_keyword",
                "crud_keywordcluster",
                "crud_asset",
                "read_category",
            ],
        }
    )
    roles.append(
        {
            "slug": "accountant",
            "name": "Accountant",
            "caps": extend(roles, ["staff"])
            + [
                "read_freelancer_bill",
                "crud_freelancer_bill",
                "crud_mentorship_bill",
                "read_mentorship_bill",
                "read_project_invoice",
                "crud_project_invoice",
                "get_github_user",
                "read_provisioning_bill",
                "crud_provisioning_bill",
            ],
        }
    )
    roles.append(
        {
            "slug": "homework_reviewer",
            "name": "Homework Reviewer",
            "caps": extend(roles, ["assistant"]) + ["crud_student"],
        }
    )
    roles.append({"slug": "teacher", "name": "Teacher", "caps": extend(roles, ["assistant"]) + ["crud_cohort"]})
    roles.append(
        {
            "slug": "academy_coordinator",
            "name": "Mentor in residence",
            "caps": extend(roles, ["teacher"])
            + [
                "crud_syllabus",
                "crud_cohort",
                "crud_student",
                "crud_survey",
                "read_won_lead",
                "crud_member",
                "send_reset_password",
                "generate_temporal_token",
                "crud_certificate",
                "crud_review",
                "read_assignment_sensitive_details",
                "crud_shortlink",
                "invite_resend",
                "crud_invite",
                "crud_mentorship_mentor",
                "read_mentorship_mentor",
                "read_mentorship_service",
                "crud_mentorship_service",
                "read_mentorship_session",
                "crud_mentorship_session",
                "crud_mentorship_bill",
                "read_mentorship_bill",
                "crud_freelancer_bill",
                "get_gitpod_user",
                "update_gitpod_user",
                "get_github_user",
                "update_github_user",
                "read_project_invoice",
                "read_freelance_projects",
                "sync_organization_users",
                "read_provisioning_bill",
                "read_calendly_organization",
                "reset_calendly_organization",
                "create_calendly_organization",
                "delete_calendly_organization",
            ],
        }
    )
    roles.append(
        {
            "slug": "country_manager",
            "name": "Country Manager",
            "caps": extend(
                roles,
                [
                    "academy_coordinator",
                    "student",
                    "career_support",
                    "growth_manager",
                    "admissions_developer",
                    "syllabus_coordinator",
                    "accountant",
                ],
            )
            + [
                "crud_my_academy",
                "crud_organization",
                "generate_academy_token",
                "send_reset_password",
                "generate_temporal_token",
                "read_organization",
                "crud_provisioning_bill",
            ],
        }
    )


class Command(BaseCommand):
    help = "Create default system capabilities"

    def handle(self, *args, **options):

        # Here is a list of all the current capabilities in the system
        caps = get_capabilities()

        for c in caps:
            _cap = Capability.objects.filter(slug=c["slug"]).first()
            if _cap is None:
                _cap = Capability(**c)
                _cap.save()
            else:
                _cap.description = c["description"]
                _cap.save()

        # These are the MAIN roles, they cannot be deleted by anyone at the academy.
        roles = get_roles()

        # These are additional roles that extend from the base roles above,
        # you can exend from more than one role but also add additional capabilitis at the end
        extend_roles(roles)

        for r in roles:
            _r = Role.objects.filter(slug=r["slug"]).first()
            if _r is None:
                _r = Role(slug=r["slug"], name=r["name"])
                _r.save()

            _r.capabilities.clear()
            r["caps"] = remove_duplicates(r["caps"])
            for c in r["caps"]:
                _r.capabilities.add(c)
