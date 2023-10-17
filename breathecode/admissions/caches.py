from breathecode.utils import Cache
from .models import Cohort, CohortUser, SyllabusVersion
from breathecode.authenticate.models import ProfileAcademy
from django.contrib.auth.models import User

MODULE = 'admissions'


class CohortCache(Cache):
    model = Cohort
    depends = ['Academy', 'SyllabusVersion', 'SyllabusSchedule']
    parents = [
        'CohortUser', 'Task', 'UserInvite', 'UserSpecialty', 'Survey', 'SlackChannel', 'CohortTimeSlot',
        'FinalProject', 'GitpodUser', 'Answer', 'Review', 'EventTypeVisibilitySetting', 'Course', 'CohortSet',
        'CohortSetCohort', 'PlanFinancing', 'Subscription', 'SubscriptionServiceItem'
    ]


class TeacherCache(Cache):
    model = ProfileAcademy
    depends = ['Academy', 'User', 'Role']
    parents = []


class CohortUserCache(Cache):
    model = CohortUser
    depends = ['User', 'Cohort']
    parents = []


class UserCache(Cache):
    model = User
    depends = []
    parents = [
        'CohortUser',
        'Assessment',
        'Question',
        'UserAssessment',
        'UserAttachment',
        'Task',
        'FinalProject',
        'Profile',
        'UserSetting',
        'AppUserAgreement',
        'UserInvite',
        'ProfileAcademy',
        'CredentialsGithub',
        'AcademyAuthSettings',
        'GithubAcademyUser',
        'CredentialsSlack',
        'CredentialsFacebook',
        'CredentialsQuickBooks',
        'CredentialsGoogle',
        'GitpodUser',
        'UserSpecialty',
        'TaskWatcher',
        'Event',
        'EventCheckin',
        'EventbriteWebhook',
        'Answer',
        'Review',
        'Freelancer',
        'ProjectInvoice',
        'Bill',
        'Issue',
        'FormEntry',
        'ShortLink',
        'Downloadable',
        'UTMField',
        'SupportAgent',
        'MentorProfile',
        'MentorshipBill',
        'MentorshipSession',
        'Device',
        'SlackTeam',
        'SlackUser',
        'Bag',
        'Invoice',
        'PlanFinancing',
        'Subscription',
        'Consumable',
        'PaymentContact',
        'FinancialReputation',
        'ProvisioningContainer',
        'Asset',
        'AssetComment',
        'AssetErrorLog',
    ]


class SyllabusVersionCache(Cache):
    model = SyllabusVersion
    depends = ['Syllabus']
    parents = ['Cohort']
