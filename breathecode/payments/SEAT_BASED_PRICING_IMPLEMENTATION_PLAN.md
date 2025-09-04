# Seat-Based Pricing Implementation Plan

## Overview

This document outlines the step-by-step implementation of seat-based pricing for the BreatheCode Payments system. The implementation will allow team owners to purchase subscriptions with multiple seats, manage team members, and provide each team member with their own consumables while sharing the team owner's subscription.

## Core Requirements

1. **Team Management**: Team owners can have multiple subscriptions, each with separate teams
2. **Seat-Based Pricing**: Plans can include seat add-ons for team members
3. **Individual Consumables**: Each team member gets their own consumables (AI interactions, etc.)
4. **Bulk Import**: CSV import for team members with first name, last name, and email
5. **Team Member Management**: Add/remove team members from subscriptions
6. **Integration with UserInvite**: The current UserInvite should now handle team invites. 

## Implementation Steps

### Phase 1: Database Schema Changes

#### 1.1 Update UserInvite Model

First, we need to extend the existing `UserInvite` model to support team member invitations:

```python
# breathecode/authenticate/models.py

class UserInvite(models.Model):
    # ... existing fields ...
    
    # New field for team member invitations
    team_member = models.ForeignKey(
        'payments.TeamMember',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invites',
        help_text="Team member this invite is for (if it's a team invitation)"
    )
    
    # ... rest of existing fields and methods ...
```

#### 1.2 Create Team Member Model

```python
# breathecode/payments/models.py

class TeamMember(models.Model):
    """Represents a team member in a subscription."""
    
    class Status(models.TextChoices):
        INVITED = ("INVITED", "Invited")
        ACTIVE = ("ACTIVE", "Active")
        REMOVED = ("REMOVED", "Removed")
    
    seat_consumable = models.ForeignKey(
        Consumable, 
        on_delete=models.CASCADE, 
        related_name="team_members",
        help_text="Consumable used to add the user to the team, links the member with the owner original subscription or plan financing"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='team_memberships',
        help_text="User account if team member has registered"
    )
    email = models.EmailField(help_text="The email used to invite the member")
    first_name = models.CharField(max_length=150, help_text="The first name used to invite the user")
    last_name = models.CharField(max_length=150, help_text="The last name used to invite the user")
    status = models.CharField(
        max_length=10, 
        choices=Status, 
        default=Status.INVITED,
        help_text="Team member status"
    )
    invited_at = models.DateTimeField(auto_now_add=True, help_text="When the team member was invited")
    joined_at = models.DateTimeField(null=True, blank=True, help_text="When the team member joined")
    removed_at = models.DateTimeField(null=True, blank=True, help_text="When the team member was removed")

    class Meta:
        #unique constraints to prevent duplicate team members
        unique_together = [('seat_consumable', 'email')]
        indexes = [
            models.Index(fields=['seat_consumable', 'status']),
            models.Index(fields=['email']),
            models.Index(fields=['user']),
        ]

    def clean(self):
        super().clean()
        
        # Validate email format
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', self.email):
            raise ValidationError("Invalid email format")
        
        # Normalize email
        self.email = self.email.lower().strip()
        self.first_name = self.first_name.strip()
        self.last_name = self.last_name.strip()

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
```

#### 1.2 Update ServiceItem Model

```python
# breathecode/payments/models.py

class ServiceItem(AbstractServiceItem):
    """This model is used as referenced of units of a service can be used."""
    
    service = models.ForeignKey(Service, on_delete=models.CASCADE, help_text="Service")
    is_renewable = models.BooleanField(
        default=False,
        help_text="If it's marked, the consumables will be renewed according to the renew_at and renew_at_unit values.",
    )
    
    # New fields for team management
    is_team_allowed = models.BooleanField(
        default=False, 
        help_text="Whether this service item supports team members, only one team_allowed service item is allowed per plan"
    )
    max_team_members = models.IntegerField(
        default=1, 
        help_text="Maximum number of team members allowed for this service item"
    )
    
    # the below fields are useless when is_renewable=False
    renew_at = models.IntegerField(
        default=1, help_text="Renew at (e.g. 1, 2, 3, ...) it going to be used to build the balance of " "customer"
    )
    renew_at_unit = models.CharField(
        max_length=10, choices=PAY_EVERY_UNIT, default=MONTH, help_text="Renew at unit (e.g. DAY, WEEK, MONTH or YEAR)"
    )
    
    def get_team_members_for_subscription(self, subscription):
        """Get all team members for this service item in a specific subscription."""
        seat_consumables = Consumable.objects.filter(
            subscription=subscription,
            service_item=self,
            team_member__isnull=False
        )
        return TeamMember.objects.filter(seat_consumable__in=seat_consumables)
    
    def get_active_team_members_for_subscription(self, subscription):
        """Get active team members for this service item in a specific subscription."""
        return self.get_team_members_for_subscription(subscription).filter(status=TeamMember.Status.ACTIVE)
    
    def get_team_member_count_for_subscription(self, subscription):
        """Get current number of active team members for this service item in a subscription."""
        return self.get_active_team_members_for_subscription(subscription).count()
    
    def can_add_team_member_for_subscription(self, subscription):
        """Check if a new team member can be added for this service item in a subscription."""
        if not self.is_team_allowed:
            return False
        return self.get_team_member_count_for_subscription(subscription) < self.max_team_members
```

#### 1.3 Update Consumable Model

```python
# breathecode/payments/models.py

class Consumable(AbstractServiceItem):
    # ... existing fields ...
    
    
    def clean(self):
        super().clean()
        
        # Validate team member association
        if hasattr(self, 'team_member') and self.team_member:
            if self.subscription and self.team_member.seat_consumable.subscription != self.subscription:
                raise ValidationError(
                    "Team member's seat consumable must belong to the same subscription"
                )
            
            if self.plan_financing and self.team_member.seat_consumable.plan_financing != self.plan_financing:
                raise ValidationError(
                    "Team member's seat consumable must belong to the same plan financing"
                )
            
            # Ensure team member consumables don't exceed limits
            if not self.service_item.is_team_allowed:
                raise ValidationError(
                    "Cannot create consumable for team member on non-team service item"
                )
```

### Phase 2: Business Logic Implementation

#### 2.1 Create Team Management Actions

```python
# breathecode/payments/actions.py

def create_team_member_with_invite(
    seat_consumable: Consumable,
    email: str,
    first_name: str,
    last_name: str,
    author: User,
    lang: str = "en"
) -> tuple[TeamMember, UserInvite]:
    """Create a new team member and send invitation through UserInvite system."""
    
    # Validate inputs
    if not email or not first_name or not last_name:
        raise ValidationException(
            translation(
                lang,
                en="Email, first name, and last name are required",
                es="Email, nombre y apellido son requeridos",
                slug="missing-required-fields"
            ),
            code=400
        )
    
    # Validate email format
    import re
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise ValidationException(
            translation(
                lang,
                en="Invalid email format",
                es="Formato de email inválido",
                slug="invalid-email-format"
            ),
            code=400
        )
    
    # Normalize inputs
    email = email.lower().strip()
    first_name = first_name.strip()
    last_name = last_name.strip()
    
    subscription = seat_consumable.subscription
    service_item = seat_consumable.service_item
    
    if not service_item.is_team_allowed:
        raise ValidationException(
            translation(
                lang,
                en="This service item does not support team members",
                es="Este elemento de servicio no soporta miembros de equipo",
                slug="service-item-not-team-enabled"
            ),
            code=400
        )
    
    if not service_item.can_add_team_member_for_subscription(subscription):
        raise ValidationException(
            translation(
                lang,
                en=f"Maximum team members ({service_item.max_team_members}) reached for this service",
                es=f"Máximo de miembros de equipo ({service_item.max_team_members}) alcanzado para este servicio",
                slug="max-team-members-reached"
            ),
            code=400
        )
    
    # Check if email already exists in this subscription for this service item
    existing_members = service_item.get_team_members_for_subscription(subscription)
    if existing_members.filter(email=email).exists():
        raise ValidationException(
            translation(
                lang,
                en="Team member with this email already exists for this service",
                es="Ya existe un miembro de equipo con este email para este servicio",
                slug="team-member-email-exists"
            ),
            code=400
        )
    
    # Create the team member
    team_member = TeamMember.objects.create(
        seat_consumable=seat_consumable,
        email=email,
        first_name=first_name,
        last_name=last_name,
        status=TeamMember.Status.INVITED
    )
    
    # Create UserInvite for the team member
    from breathecode.authenticate.models import UserInvite
    import uuid
    
    # Check if user already exists
    existing_user = User.objects.filter(email=email).first()
    
    user_invite = UserInvite.objects.create(
        email=email,
        first_name=first_name,
        last_name=last_name,
        author=author,
        academy=subscription.academy,
        token=str(uuid.uuid4()),
        team_member=team_member,
        status="PENDING"
    )
    
    # Send invitation email (this will be handled by UserInvite's save method)
    
    return team_member, user_invite

def bulk_create_team_members_with_invites(
    seat_consumable: Consumable,
    team_members_data: list[dict],
    author: User,
    lang: str = "en"
) -> list[tuple[TeamMember, UserInvite]]:
    """Bulk create team members from CSV data with UserInvite integration."""
    
    created_members = []
    errors = []
    
    for i, member_data in enumerate(team_members_data):
        try:
            email = member_data.get('email', '').strip()
            first_name = member_data.get('first_name', '').strip()
            last_name = member_data.get('last_name', '').strip()
            
            if not email or not first_name or not last_name:
                errors.append(f"Row {i+1}: Missing required fields (email, first_name, last_name)")
                continue
            
            team_member, user_invite = create_team_member_with_invite(
                seat_consumable=seat_consumable,
                email=email,
                first_name=first_name,
                last_name=last_name,
                author=author,
                lang=lang
            )
            created_members.append((team_member, user_invite))
            
        except ValidationException as e:
            errors.append(f"Row {i+1}: {e.detail}")
        except Exception as e:
            errors.append(f"Row {i+1}: Unexpected error - {str(e)}")
    
    if errors:
        raise ValidationException(
            translation(
                lang,
                en=f"Errors in bulk import: {'; '.join(errors)}",
                es=f"Errores en importación masiva: {'; '.join(errors)}",
                slug="bulk-import-errors"
            ),
            code=400
        )
    
    return created_members

def remove_team_member(team_member: TeamMember, lang: str = "en") -> None:
    """Remove a team member from a subscription."""
    
    if team_member.status == TeamMember.Status.REMOVED:
        raise ValidationException(
            translation(
                lang,
                en="Team member is already removed",
                es="El miembro de equipo ya fue removido",
                slug="team-member-already-removed"
            ),
            code=400
        )
    
    team_member.status = TeamMember.Status.REMOVED
    team_member.removed_at = timezone.now()
    team_member.save()
    
    # Revoke consumables for this team member
    revoke_team_member_consumables(team_member)

def activate_team_member(team_member: TeamMember, user: User = None) -> None:
    """Activate a team member when they join."""
    
    team_member.status = TeamMember.Status.ACTIVE
    team_member.joined_at = timezone.now()
    if user:
        team_member.user = user
    team_member.save()
    
    # Create consumables for the team member based on their seat consumable's subscription
    create_team_member_consumables(team_member)

# Async versions for better performance
from asgiref.sync import sync_to_async

@sync_to_async
def create_team_member_async(
    seat_consumable: Consumable,
    email: str,
    first_name: str,
    last_name: str,
    lang: str = "en"
) -> TeamMember:
    """Async version of create_team_member."""
    return create_team_member(seat_consumable, email, first_name, last_name, lang)

@sync_to_async
def activate_team_member_async(team_member: TeamMember, user: User = None) -> None:
    """Async version of activate_team_member."""
    return activate_team_member(team_member, user)

# Extension to existing accept_invite function
def extend_accept_invite_for_team_members(invite: 'UserInvite', user: User):
    """Extend the existing accept_invite function to handle team member invitations."""
    
    # Only process if this is a team member invite
    if invite.team_member:
        team_member = invite.team_member
        
        # Link the user to the team member
        team_member.user = user
        team_member.status = TeamMember.Status.ACTIVE
        team_member.joined_at = timezone.now()
        team_member.save()
        
        # Create consumables for the team member
        create_team_member_consumables(team_member)
        
        logger.info(f"Team member {team_member.id} activated for user {user.id}")

# Signal handler for UserInvite acceptance
def handle_team_member_invite_accepted(sender, instance: 'UserInvite', **kwargs):
    """Handle when a team member invite is accepted through the standard flow."""
    
    # Only process if this is a team member invite and it was just accepted
    if (instance.team_member and 
        instance.status == "ACCEPTED" and 
        instance._old_status != "ACCEPTED" and
        instance.user):
        
        # Call our extension function
        extend_accept_invite_for_team_members(instance, instance.user)

#### 2.5 Validation Patterns

Following BreatheCode's validation patterns, all ValidationExceptions should use proper translations:

```python
# Example of proper validation pattern in team management functions

def validate_team_member_permissions(user: User, subscription: Subscription, lang: str = "en"):
    """Validate that user has permissions to manage team members."""
    
    if subscription.user != user:
        raise ValidationException(
            translation(
                lang,
                en=f"User {user.id} does not have permission to manage team members for subscription {subscription.id}",
                es=f"El usuario {user.id} no tiene permisos para gestionar miembros de equipo para la suscripción {subscription.id}",
                slug="no-team-management-permission"
            ),
            code=403
        )

def validate_team_member_email_unique(email: str, subscription: Subscription, lang: str = "en"):
    """Validate that team member email is unique within subscription."""
    
    existing_members = TeamMember.objects.filter(
        seat_consumable__subscription=subscription,
        email=email,
        status__in=[TeamMember.Status.INVITED, TeamMember.Status.ACTIVE]
    )
    
    if existing_members.exists():
        raise ValidationException(
            translation(
                lang,
                en=f"A team member with email {email} already exists in this subscription",
                es=f"Ya existe un miembro de equipo con el email {email} en esta suscripción",
                slug="team-member-email-already-exists"
            ),
            code=400
        )

def validate_service_supports_teams(service_item: ServiceItem, lang: str = "en"):
    """Validate that service item supports team members."""
    
    if not service_item.is_team_allowed:
        raise ValidationException(
            translation(
                lang,
                en=f"Service '{service_item.service.slug}' does not support team members",
                es=f"El servicio '{service_item.service.slug}' no soporta miembros de equipo",
                slug="service-does-not-support-teams"
            ),
            code=400
        )

#### 2.2 Update Consumable Creation Logic

```python
# breathecode/payments/actions.py

def create_team_member_consumables(team_member: TeamMember) -> None:
    """Create consumables for a team member based on their seat consumable's subscription."""
    
    subscription = team_member.seat_consumable.subscription
    
    # Get all service items from the subscription's plans
    for plan in subscription.plans.all():
        for plan_service_item in plan.service_items.all():
            service_item = plan_service_item.service_item
            
            # Create consumable for team member
            consumable = Consumable.objects.create(
                service_item=service_item,
                user=team_member.user or subscription.user,  # Fallback to subscription owner
                subscription=subscription,
                how_many=service_item.how_many,
                unit_type=service_item.unit_type,
                sort_priority=service_item.sort_priority,
                team_member=team_member,
                cohort_set=subscription.selected_cohort_set,
                event_type_set=subscription.selected_event_type_set,
                mentorship_service_set=subscription.selected_mentorship_service_set,
                valid_until=subscription.valid_until
            )
            
            # Create service stock scheduler for team member
            create_team_member_service_stock_scheduler(consumable, subscription)

def revoke_team_member_consumables(team_member: TeamMember) -> None:
    """Revoke all consumables for a team member."""
    
    consumables = Consumable.objects.filter(team_member=team_member)
    
    for consumable in consumables:
        # Set how_many to 0 to effectively revoke access
        consumable.how_many = 0
        consumable.save()
        
        # Revoke service permissions
        signals.revoke_service_permissions.send_robust(instance=consumable, sender=Consumable)

def create_team_member_service_stock_scheduler(consumable: Consumable, subscription: Subscription) -> None:
    """Create service stock scheduler for team member consumable."""
    
    # Find or create subscription service item
    subscription_service_item, created = SubscriptionServiceItem.objects.get_or_create(
        subscription=subscription,
        service_item=consumable.service_item,
        defaults={
            'cohorts': subscription.joined_cohorts.all(),
            'mentorship_service_set': subscription.selected_mentorship_service_set
        }
    )
    
    # Create service stock scheduler
    scheduler = ServiceStockScheduler.objects.create(
        subscription_handler=subscription_service_item,
        valid_until=subscription.valid_until
    )
    
    # Add consumable to scheduler
    scheduler.consumables.add(consumable)

#### 2.3 Integration with Existing accept_invite Function

The existing `accept_invite` function in `breathecode.authenticate.actions` needs to be extended to handle team member invitations. We have two options:

**Option 1: Modify the existing functions directly (Recommended)**

There are two functions in `breathecode.authenticate.actions` that need to be updated:

**A. Update `accept_invite()` - for existing users**

```python
# breathecode/authenticate/actions.py - Update existing function

def accept_invite(accepting_ids=None, user=None):
    if accepting_ids is not None:
        invites = UserInvite.objects.filter(id__in=accepting_ids.split(","), email=user.email, status="PENDING")
    else:
        invites = UserInvite.objects.filter(email=user.email, status="PENDING")

    for invite in invites:
        # Existing academy and cohort logic...
        if invite.academy is not None:
            # ... existing ProfileAcademy logic ...
            pass
            
        if invite.cohort is not None:
            # ... existing CohortUser logic ...
            pass
        
        # NEW: Handle team member invitations
        if invite.team_member is not None:
            from breathecode.payments.actions import extend_accept_invite_for_team_members
            extend_accept_invite_for_team_members(invite, user)

        if user is not None and invite.user is None:
            invite.user = user

        invite.status = "ACCEPTED"
        invite.process_status = "DONE"
        invite.save()
```

**B. Update `accept_invite_action()` - for new users registering through invitation**

```python
# breathecode/authenticate/actions.py - Update existing function

def accept_invite_action(data=None, token=None, lang="en"):
    # ... existing validation and user creation logic ...
    
    # After user is created/found and before invite.status = "ACCEPTED":
    
    # NEW: Handle team member invitations
    if invite.team_member is not None:
        from breathecode.payments.actions import extend_accept_invite_for_team_members
        extend_accept_invite_for_team_members(invite, user)
    
    invite.status = "ACCEPTED"
    invite.is_email_validated = True
    invite.save()

    return invite
```

**Option 2: Use signal-based approach (Alternative)**

If modifying the existing function is not preferred, we can use the signal approach shown above.

#### 2.4 Signal Registration

```python
# breathecode/payments/signals.py (add to existing file or create new)

from django.db.models.signals import post_save
from django.dispatch import receiver
from breathecode.authenticate.models import UserInvite
from .actions import handle_team_member_invite_accepted

# Register signal handler for UserInvite acceptance
@receiver(post_save, sender=UserInvite)
def on_user_invite_saved(sender, instance, created, **kwargs):
    """Handle UserInvite post-save to process team member invitations."""
    handle_team_member_invite_accepted(sender, instance, **kwargs)
```

```python
# breathecode/payments/apps.py (update existing file)

from django.apps import AppConfig

class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'breathecode.payments'
    
    def ready(self):
        from .flags import TEAM_MANAGEMENT_ENABLED, TEAM_SUPERVISORS_ENABLED
        
        # Initialize feature flags
        if TEAM_MANAGEMENT_ENABLED.is_enabled():
            # Import signals to register them
            try:
                from . import signals
            except ImportError:
                pass
        
        if TEAM_SUPERVISORS_ENABLED.is_enabled():
            # Import supervisors to register them
            try:
                from . import supervisors
            except ImportError:
                pass
```

### Phase 3: Task Updates

#### 3.1 Update Subscription Creation Tasks

```python
# breathecode/payments/tasks.py

@task(bind=True, priority=TaskPriority.WEB_SERVICE_PAYMENT.value)
def build_service_stock_scheduler_from_subscription(self, subscription_id: int, **kwargs):
    """Updated to handle team members."""
    
    subscription = Subscription.objects.get(id=subscription_id)
    
    # Create consumables for subscription owner
    for plan in subscription.plans.all():
        for plan_service_item in plan.service_items.all():
            service_item = plan_service_item.service_item
            
            # Create consumable for subscription owner
            consumable = Consumable.objects.create(
                service_item=service_item,
                user=subscription.user,
                subscription=subscription,
                how_many=service_item.how_many,
                unit_type=service_item.unit_type,
                sort_priority=service_item.sort_priority,
                cohort_set=subscription.selected_cohort_set,
                event_type_set=subscription.selected_event_type_set,
                mentorship_service_set=subscription.selected_mentorship_service_set,
                valid_until=subscription.valid_until
            )
            
            # Create service stock scheduler
            create_service_stock_scheduler(consumable, subscription)
    
    # Create consumables for team members for team-enabled service items
    # Get all seat consumables for this subscription
    seat_consumables = Consumable.objects.filter(
        subscription=subscription,
        team_member__isnull=False
    )
    for seat_consumable in seat_consumables:
        # Check if the service item supports teams
        if seat_consumable.service_item.is_team_allowed:
            for team_member in seat_consumable.team_members.filter(status=TeamMember.Status.ACTIVE):
                create_team_member_consumables(team_member)
    
    # Handle add-ons for team members
    for plan in subscription.plans.all():
        for add_on in plan.add_ons.all():
            # Create add-on consumables for each team member
            seat_consumables = Consumable.objects.filter(
                subscription=subscription,
                team_member__isnull=False
            )
            for seat_consumable in seat_consumables:
                if seat_consumable.service_item.is_team_allowed:
                    for team_member in seat_consumable.team_members.filter(status=TeamMember.Status.ACTIVE):
                        create_add_on_consumable_for_team_member(add_on, team_member, subscription)

def create_add_on_consumable_for_team_member(
    add_on: AcademyService, 
    team_member: TeamMember, 
    subscription: Subscription
) -> None:
    """Create add-on consumable for a team member."""
    
    # Get the service item for this add-on
    service_item = ServiceItem.objects.filter(service=add_on.service).first()
    if not service_item:
        return
    
    # Create consumable for team member
    consumable = Consumable.objects.create(
        service_item=service_item,
        user=team_member.user or subscription.user,
        subscription=subscription,
        how_many=service_item.how_many,
        unit_type=service_item.unit_type,
        sort_priority=service_item.sort_priority,
        team_member=team_member,
        cohort_set=subscription.selected_cohort_set,
        event_type_set=subscription.selected_event_type_set,
        mentorship_service_set=subscription.selected_mentorship_service_set,
        valid_until=subscription.valid_until
    )
    
    # Create service stock scheduler
    create_team_member_service_stock_scheduler(consumable, subscription)
```

### Phase 4: API Endpoints

#### 4.1 Team Member Management Endpoints

```python
# breathecode/payments/views.py

class TeamMemberViewSet(viewsets.ModelViewSet):
    """Manage team members for a subscription."""
    
    queryset = TeamMember.objects.all()
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter team members by subscription and user permissions."""
        subscription_id = self.kwargs.get('subscription_id')
        subscription = get_object_or_404(Subscription, id=subscription_id)
        
        # Check if user owns this subscription or is a team member
        # Get all team members across all service items in this subscription
        all_team_members = TeamMember.objects.filter(
            seat_consumable__subscription=subscription
        )
        
        if (subscription.user != self.request.user and 
            not all_team_members.filter(user=self.request.user).exists()):
            raise PermissionDenied("You don't have permission to access this subscription's team members")
        
        return all_team_members
    
    def create(self, request, subscription_id=None):
        """Add a new team member to a subscription."""
        subscription = get_object_or_404(Subscription, id=subscription_id)
        
        if subscription.user != request.user:
            raise PermissionDenied("Only the subscription owner can add team members")
        
        # Get the seat consumable for this subscription
        seat_consumable_id = request.data.get('seat_consumable_id')
        if not seat_consumable_id:
            return Response(
                {'error': 'seat_consumable_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        seat_consumable = get_object_or_404(
            Consumable, 
            id=seat_consumable_id, 
            subscription=subscription
        )
        
        serializer = TeamMemberSerializer(data=request.data)
        if serializer.is_valid():
            team_member, user_invite = create_team_member_with_invite(
                seat_consumable=seat_consumable,
                email=serializer.validated_data['email'],
                first_name=serializer.validated_data['first_name'],
                last_name=serializer.validated_data['last_name'],
                author=request.user,  # Team owner as author
                lang=request.META.get('HTTP_ACCEPT_LANGUAGE', 'en')
            )
            
            # Return both team member and invite information
            response_data = TeamMemberSerializer(team_member).data
            response_data['invite_token'] = user_invite.token
            response_data['invite_status'] = user_invite.status
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, subscription_id=None, pk=None):
        """Remove a team member from a subscription."""
        team_member = get_object_or_404(TeamMember, id=pk, seat_consumable__subscription_id=subscription_id)
        
        if team_member.seat_consumable.subscription.user != request.user:
            raise PermissionDenied("Only the subscription owner can remove team members")
        
        remove_team_member(team_member, lang=request.META.get('HTTP_ACCEPT_LANGUAGE', 'en'))
        return Response(status=status.HTTP_204_NO_CONTENT)

class BulkTeamMemberView(APIView):
    """Bulk import team members from CSV."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, subscription_id=None):
        """Import team members from CSV data."""
        subscription = get_object_or_404(Subscription, id=subscription_id)
        
        if subscription.user != request.user:
            raise PermissionDenied("Only the subscription owner can import team members")
        
        # Get the seat consumable for this subscription
        seat_consumable_id = request.data.get('seat_consumable_id')
        if not seat_consumable_id:
            return Response(
                {'error': 'seat_consumable_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        seat_consumable = get_object_or_404(
            Consumable, 
            id=seat_consumable_id, 
            subscription=subscription
        )
        
        # Parse CSV data
        csv_data = request.data.get('csv_data', '')
        if not csv_data:
            return Response(
                {'error': 'CSV data is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Parse CSV
            import csv
            import io
            
            csv_file = io.StringIO(csv_data)
            reader = csv.DictReader(csv_file)
            team_members_data = list(reader)
            
            # Validate required columns
            required_columns = ['email', 'first_name', 'last_name']
            if not all(col in reader.fieldnames for col in required_columns):
                return Response(
                    {'error': f'CSV must contain columns: {", ".join(required_columns)}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create team members with invites
            created_members_with_invites = bulk_create_team_members_with_invites(
                seat_consumable=seat_consumable,
                team_members_data=team_members_data,
                author=request.user,  # Team owner as author
                lang=request.META.get('HTTP_ACCEPT_LANGUAGE', 'en')
            )
            
            # Extract team members and prepare response
            team_members = [tm for tm, ui in created_members_with_invites]
            invites = [ui for tm, ui in created_members_with_invites]
            
            return Response({
                'message': f'Successfully created {len(team_members)} team members and sent invitations',
                'team_members': TeamMemberSerializer(team_members, many=True).data,
                'invites_sent': len(invites)
            }, status=status.HTTP_201_CREATED)
            
        except ValidationException as e:
            return Response({'error': str(e.detail)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TeamMemberInviteStatusView(APIView):
    """Check the status of a team member invitation."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, subscription_id=None, pk=None):
        """Get team member invite status."""
        team_member = get_object_or_404(TeamMember, id=pk, seat_consumable__subscription_id=subscription_id)
        
        # Check permissions - either the team owner or the invited user
        subscription = team_member.seat_consumable.subscription
        if (subscription.user != request.user and 
            team_member.email != request.user.email):
            raise PermissionDenied("You don't have permission to view this team member's status")
        
        # Get associated UserInvite
        from breathecode.authenticate.models import UserInvite
        user_invite = UserInvite.objects.filter(team_member=team_member).first()
        
        response_data = TeamMemberSerializer(team_member).data
        if user_invite:
            response_data['invite_status'] = user_invite.status
            response_data['invite_token'] = user_invite.token
            response_data['invite_sent_at'] = user_invite.sent_at
        
        return Response(response_data, status=status.HTTP_200_OK)
```

#### 4.2 Update URL Configuration

```python
# breathecode/payments/urls.py

urlpatterns = [
    # ... existing URLs ...
    
    # Team member management
    path('subscriptions/<int:subscription_id>/team-members/', 
         TeamMemberViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='subscription-team-members'),
    path('subscriptions/<int:subscription_id>/team-members/<int:pk>/', 
         TeamMemberViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), 
         name='subscription-team-member-detail'),
    path('subscriptions/<int:subscription_id>/team-members/bulk-import/', 
         BulkTeamMemberView.as_view(), 
         name='subscription-team-members-bulk-import'),
    path('subscriptions/<int:subscription_id>/team-members/<int:pk>/invite-status/', 
         TeamMemberInviteStatusView.as_view(), 
         name='subscription-team-member-invite-status'),
]
```

### Phase 5: Serializers

#### 5.1 Create Team Member Serializers

```python
# breathecode/payments/serializers.py

class TeamMemberSerializer(serializers.ModelSerializer):
    """Serializer for team members."""
    
    class Meta:
        model = TeamMember
        fields = [
            'id', 'email', 'first_name', 'last_name', 'status', 
            'invited_at', 'joined_at', 'removed_at', 'user', 'seat_consumable'
        ]
        read_only_fields = ['id', 'invited_at', 'joined_at', 'removed_at', 'user']
    
    def validate_email(self, value):
        """Validate email format."""
        if not value or '@' not in value:
            raise serializers.ValidationError("Invalid email format")
        return value.lower().strip()

class SubscriptionWithTeamSerializer(serializers.ModelSerializer):
    """Serializer for subscriptions with team information."""
    
    team_members = TeamMemberSerializer(many=True, read_only=True)
    team_member_count = serializers.SerializerMethodField()
    team_enabled_services = serializers.SerializerMethodField()
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'user', 'academy', 'status', 'paid_at', 'next_payment_at', 
            'valid_until', 'team_member_count', 'team_members', 'team_enabled_services'
        ]
    
    def get_team_member_count(self, obj):
        """Get current number of active team members across all service items."""
        return TeamMember.objects.filter(
            seat_consumable__subscription=obj,
            status=TeamMember.Status.ACTIVE
        ).count()
    
    def get_team_enabled_services(self, obj):
        """Get information about team-enabled services in this subscription."""
        team_enabled_services = []
        
        # Get all service items that support teams
        for service_item in obj.service_items.filter(is_team_allowed=True):
            team_member_count = service_item.get_team_member_count_for_subscription(obj)
            team_enabled_services.append({
                'service_item_id': service_item.id,
                'service_slug': service_item.service.slug,
                'max_team_members': service_item.max_team_members,
                'current_team_members': team_member_count,
                'can_add_more': team_member_count < service_item.max_team_members
            })
        
        return team_enabled_services

class TeamMemberDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for team members with consumable information."""
    
    consumables = serializers.SerializerMethodField()
    subscription_owner = serializers.SerializerMethodField()
    consumable_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamMember
        fields = [
            'id', 'email', 'first_name', 'last_name', 'status',
            'invited_at', 'joined_at', 'removed_at', 'user', 
            'seat_consumable', 'consumables', 'subscription_owner',
            'consumable_summary'
        ]
    
    def get_consumables(self, obj):
        from .serializers import ConsumableSerializer
        consumables = Consumable.objects.filter(team_member=obj)
        return ConsumableSerializer(consumables, many=True).data
    
    def get_subscription_owner(self, obj):
        return {
            'id': obj.seat_consumable.subscription.user.id,
            'email': obj.seat_consumable.subscription.user.email,
            'first_name': obj.seat_consumable.subscription.user.first_name,
            'last_name': obj.seat_consumable.subscription.user.last_name,
        }
    
    def get_consumable_summary(self, obj):
        """Get summary of consumables by service type."""
        consumables = Consumable.objects.filter(team_member=obj)
        summary = {}
        
        for consumable in consumables:
            service_slug = consumable.service_item.service.slug
            summary[service_slug] = {
                'how_many': consumable.how_many,
                'unit_type': consumable.unit_type,
                'valid_until': consumable.valid_until
            }
        
        return summary
```

### Phase 6: Plan Configuration Updates

#### 6.1 Update Plan Model for Seat Support

```python
# breathecode/payments/models.py

class Plan(AbstractPriceByTime):
    # ... existing fields ...
    
    # New fields for team support
    supports_teams = models.BooleanField(
        default=False, 
        help_text="Whether this plan supports team members, this field should be read only and set automatically when a service iteam with is_team_allowed is added/removed from the plan"
    )
    seat_add_on_service = models.ForeignKey(
        AcademyService,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Service used for additional seat add-ons"
    )
    
    def get_team_enabled_service_items(self):
        """Get all service items in this plan that support teams."""
        return ServiceItem.objects.filter(
            service__in=self.service_items.values_list('service', flat=True),
            is_team_allowed=True
        )
    
    def has_team_enabled_services(self) -> bool:
        """Check if this plan has any team-enabled services."""
        return self.get_team_enabled_service_items().exists()
    
    def clean(self):
        """Validate the model before saving."""
        # Ensure supports_teams is not manually set
        expected_supports_teams = self.has_team_enabled_services()
        if self.supports_teams != expected_supports_teams:
            raise ValidationError({
                'supports_teams': 'This field is read-only and cannot be set manually.'
            })

    def save(self, *args, **kwargs):
        """Override save to ensure supports_teams is set correctly."""
        # Calculate supports_teams before saving
        self.supports_teams = self.has_team_enabled_services()

        # Use a transaction to ensure atomicity
        with transaction.atomic():
            # Validate the model
            self.clean()
            # Call the parent save method
            super().save(*args, **kwargs)


# Signal handlers to make sure many to many relations between service iteam and plan also cover the validation for team enabled
@receiver(m2m_changed, sender=Plan.service_items.through)
def update_plan_supports_teams_on_m2m(sender, instance, action, **kwargs):
    """Update supports_teams when PlanServiceItem relationships change."""
    if action in ['post_add', 'post_remove', 'post_clear']:
        with transaction.atomic():
            instance.supports_teams = instance.has_team_enabled_services()
            instance.save()

@receiver([post_save, post_delete], sender=ServiceItem)
def update_plan_supports_teams_on_service_item(sender, instance, **kwargs):
    """Update supports_teams when a ServiceItem is saved or deleted."""
    plans = Plan.objects.filter(service_items=instance).distinct()
    with transaction.atomic():
        for plan in plans:
            plan.supports_teams = plan.has_team_enabled_services()
            plan.save()
```

#### 6.2 Update Bag Handler for Seat Add-ons

```python
# breathecode/payments/actions.py

class BagHandler:
    # ... existing methods ...
    
    def _validate_seat_add_ons(self):
        """Validate seat add-ons for team plans."""
        for plan in self.bag.plans.all():
            if plan.supports_teams:
                # Check if seat add-ons are properly configured
                if not plan.seat_add_on_service:
                    raise ValidationException(
                        translation(
                            self.lang,
                            en=f"Plan {plan.slug} supports teams but has no seat add-on service configured",
                            es=f"El plan {plan.slug} soporta equipos pero no tiene servicio de asientos adicionales configurado",
                            slug="plan-missing-seat-add-on"
                        ),
                        code=400
                    )
                
                # Check if plan has team-enabled service items
                if not plan.has_team_enabled_services():
                    raise ValidationException(
                        translation(
                            self.lang,
                            en=f"Plan {plan.slug} supports teams but has no team-enabled service items",
                            es=f"El plan {plan.slug} soporta equipos pero no tiene elementos de servicio habilitados para equipos",
                            slug="plan-no-team-enabled-services"
                        ),
                        code=400
                    )
    
    def _calculate_seat_pricing(self):
        """Calculate pricing for seat add-ons."""
        for plan in self.bag.plans.all():
            if plan.supports_teams and plan.seat_add_on_service:
                # Get seat add-on quantity from request
                seat_quantity = self.request.data.get('seat_quantity', 0)
                
                if seat_quantity > 0:
                    # Validate seat add-on transaction
                    plan.seat_add_on_service.validate_transaction(
                        seat_quantity, 
                        lang=self.lang,
                        country_code=self.country_code
                    )
                    
                    # Add seat add-on to service items
                    seat_service_item = ServiceItem.objects.get_or_create(
                        service=plan.seat_add_on_service.service,
                        how_many=seat_quantity
                    )[0]
                    self.bag.service_items.add(seat_service_item)
    
    def execute(self):
        # ... existing execution logic ...
        
        self._validate_seat_add_ons()
        self._calculate_seat_pricing()
        
        # ... rest of execution ...
```

### Phase 7: Supervisor Implementation

#### 7.1 Add Team Management Supervisors

```python
# breathecode/payments/supervisors.py

from datetime import timedelta
from django.utils import timezone
from breathecode.utils.decorators import supervisor, issue
from breathecode.utils import getLogger
from .models import TeamMember, Consumable
from .actions import create_team_member_consumables

logger = getLogger(__name__)

@supervisor(delta=timedelta(hours=2))
def supervise_orphaned_team_members():
    """
    Supervisor to check for team members without proper consumables.
    Ensures data integrity for team member setup.
    """
    utc_now = timezone.now()
    
    # Find active team members without consumables
    orphaned_members = TeamMember.objects.filter(
        status=TeamMember.Status.ACTIVE,
        user__isnull=False,
        joined_at__isnull=False
    ).exclude(
        id__in=Consumable.objects.filter(
            team_member__isnull=False
        ).values_list('team_member_id', flat=True)
    )
    
    for member in orphaned_members:
        yield {
            'code': 'fix-orphaned-team-member',
            'message': f'Team member {member.id} ({member.email}) has no consumables',
            'params': {'team_member_id': member.id}
        }

@supervisor(delta=timedelta(hours=6))
def supervise_team_member_limits():
    """
    Supervisor to check for team members exceeding service item limits.
    Ensures team size constraints are respected.
    """
    from django.db.models import Count
    
    # Find service items with too many active team members
    service_items_over_limit = []
    
    # Get all team-enabled service items
    team_service_items = ServiceItem.objects.filter(is_team_allowed=True)
    
    for service_item in team_service_items:
        # Count active team members per subscription for this service item
        subscriptions_with_teams = Subscription.objects.filter(
            consumable__service_item=service_item,
            consumable__team_member__status=TeamMember.Status.ACTIVE
        ).annotate(
            active_team_count=Count('consumable__team_member', distinct=True)
        ).filter(
            active_team_count__gt=service_item.max_team_members
        )
        
        for subscription in subscriptions_with_teams:
            yield {
                'code': 'fix-team-size-exceeded',
                'message': f'Subscription {subscription.id} has {subscription.active_team_count} team members, max allowed: {service_item.max_team_members}',
                'params': {
                    'subscription_id': subscription.id,
                    'service_item_id': service_item.id,
                    'current_count': subscription.active_team_count,
                    'max_allowed': service_item.max_team_members
                }
            }

@issue(code='fix-orphaned-team-member', attempts=3, delta=timedelta(minutes=30))
def fix_orphaned_team_member(team_member_id: int):
    """Fix orphaned team member by creating missing consumables."""
    try:
        team_member = TeamMember.objects.filter(
            id=team_member_id,
            status=TeamMember.Status.ACTIVE
        ).first()
        
        if not team_member:
            return True  # Already fixed or removed
        
        # Check if consumables already exist
        if Consumable.objects.filter(team_member=team_member).exists():
            return True  # Already has consumables
        
        create_team_member_consumables(team_member)
        logger.info(f"Fixed orphaned team member {team_member_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to fix orphaned team member {team_member_id}: {e}")
        return None  # Retry

@issue(code='fix-team-size-exceeded', attempts=2, delta=timedelta(hours=1))
def fix_team_size_exceeded(subscription_id: int, service_item_id: int, current_count: int, max_allowed: int):
    """Handle team size exceeded by notifying administrators."""
    try:
        from breathecode.notify.actions import send_email_message
        
        subscription = Subscription.objects.filter(id=subscription_id).first()
        service_item = ServiceItem.objects.filter(id=service_item_id).first()
        
        if not subscription or not service_item:
            return True  # Already fixed or removed
        
        # Send notification to subscription owner
        send_email_message(
            'team_size_exceeded',
            subscription.user.email,
            {
                'user_name': f"{subscription.user.first_name} {subscription.user.last_name}",
                'service_name': service_item.service.slug,
                'current_count': current_count,
                'max_allowed': max_allowed,
                'subscription_id': subscription_id
            }
        )
        
        logger.warning(f"Notified user about team size exceeded: subscription {subscription_id}")
        return True  # Mark as handled (notification sent)
        
    except Exception as e:
        logger.error(f"Failed to handle team size exceeded for subscription {subscription_id}: {e}")
        return None  # Retry
```

### Phase 11: Testing

#### 11.1 Unit Tests

```python
# breathecode/payments/tests/test_team_management.py

class TeamManagementTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='owner@test.com')
        self.academy = Academy.objects.create(slug='test-academy')
        self.service = Service.objects.create(slug='team-service')
        self.service_item = ServiceItem.objects.create(
            service=self.service,
            is_team_allowed=True,
            max_team_members=10,
            how_many=1
        )
        self.plan = Plan.objects.create(
            slug='team-plan',
            supports_teams=True,
            is_renewable=True
        )
        self.plan.service_items.add(self.service_item)
        self.subscription = Subscription.objects.create(
            user=self.user,
            academy=self.academy
        )
        self.subscription.service_items.add(self.service_item)
    
    def test_create_team_member(self):
        """Test creating a team member."""
        # Create a seat consumable for testing
        seat_consumable = Consumable.objects.create(
            service_item=self.service_item,
            user=self.user,
            subscription=self.subscription,
            how_many=1
        )
        
        team_member = create_team_member(
            seat_consumable=seat_consumable,
            email='member@test.com',
            first_name='John',
            last_name='Doe'
        )
        
        self.assertEqual(team_member.email, 'member@test.com')
        self.assertEqual(team_member.status, TeamMember.Status.INVITED)
        self.assertEqual(team_member.seat_consumable, seat_consumable)
    
    def test_bulk_create_team_members(self):
        """Test bulk creating team members."""
        # Create a seat consumable for testing
        seat_consumable = Consumable.objects.create(
            service_item=self.service_item,
            user=self.user,
            subscription=self.subscription,
            how_many=1
        )
        
        team_members_data = [
            {'email': 'member1@test.com', 'first_name': 'John', 'last_name': 'Doe'},
            {'email': 'member2@test.com', 'first_name': 'Jane', 'last_name': 'Smith'},
        ]
        
        created_members = bulk_create_team_members(
            seat_consumable=seat_consumable,
            team_members_data=team_members_data
        )
        
        self.assertEqual(len(created_members), 2)
        self.assertEqual(self.service_item.get_team_member_count_for_subscription(self.subscription), 2)
    
    def test_team_member_consumables(self):
        """Test that team members get their own consumables."""
        # Create a seat consumable for testing
        seat_consumable = Consumable.objects.create(
            service_item=self.service_item,
            user=self.user,
            subscription=self.subscription,
            how_many=1
        )
        
        team_member = create_team_member(
            seat_consumable=seat_consumable,
            email='member@test.com',
            first_name='John',
            last_name='Doe'
        )
        
        # Activate team member
        activate_team_member(team_member)
        
        # Check that consumables were created
        consumables = Consumable.objects.filter(team_member=team_member)
        self.assertGreater(consumables.count(), 0)
        
        # Check that each consumable belongs to the team member
        for consumable in consumables:
            self.assertEqual(consumable.team_member, team_member)
    
    def test_max_team_members_limit(self):
        """Test that max team members limit is enforced."""
        # Create a seat consumable for testing
        seat_consumable = Consumable.objects.create(
            service_item=self.service_item,
            user=self.user,
            subscription=self.subscription,
            how_many=1
        )
        
        # Create max team members
        for i in range(self.service_item.max_team_members):
            create_team_member(
                seat_consumable=seat_consumable,
                email=f'member{i}@test.com',
                first_name=f'Member{i}',
                last_name='Test'
            )
        
        # Try to create one more
        with self.assertRaises(ValidationException):
            create_team_member(
                seat_consumable=seat_consumable,
                email='extra@test.com',
                first_name='Extra',
                last_name='Member'
            )
```

### Phase 10: Documentation and Deployment

#### 10.1 API Documentation

```markdown
# Team Management API Documentation

## Overview
The Team Management API allows subscription owners to manage team members for their team-enabled subscriptions.

## Endpoints

### List Team Members
`GET /api/payments/subscriptions/{subscription_id}/team-members/`

Returns a list of team members for the specified subscription.

### Add Team Member
`POST /api/payments/subscriptions/{subscription_id}/team-members/`

Adds a new team member to the subscription.

**Request Body:**
```json
{
  "email": "member@example.com",
  "first_name": "John",
  "last_name": "Doe"
}
```

### Bulk Import Team Members
`POST /api/payments/subscriptions/{subscription_id}/team-members/bulk-import/`

Imports multiple team members from CSV data.

**Request Body:**
```json
{
  "csv_data": "email,first_name,last_name\nmember1@example.com,John,Doe\nmember2@example.com,Jane,Smith"
}
```

### Activate Team Member
`POST /api/payments/subscriptions/{subscription_id}/team-members/{team_member_id}/activate/`

Activates a pending team member when they join.

### Remove Team Member
`DELETE /api/payments/subscriptions/{subscription_id}/team-members/{team_member_id}/`

Removes a team member from the subscription.
```

#### 10.2 Deployment Checklist

- [ ] Run database migrations
- [ ] Deploy backend changes
- [ ] Update API documentation
- [ ] Deploy frontend changes
- [ ] Test team management functionality
- [ ] Monitor for errors
- [ ] Update user documentation

## Summary

This implementation plan provides a comprehensive solution for seat-based pricing with team management capabilities. The system allows:

1. **Service-Level Team Management**: Team validation is performed at the ServiceItem level, allowing different services to have different team limits
2. **Multiple Subscriptions**: Team owners can have multiple subscriptions, each with separate teams
3. **Seat Management**: Plans can include seat add-ons for additional team members
4. **Individual Consumables**: Each team member gets their own consumables (AI interactions, etc.)
5. **Bulk Import**: CSV import functionality for adding multiple team members
6. **Team Member Lifecycle**: Complete management of team member invitation, activation, and removal
7. **Automated Monitoring**: Supervisors ensure data integrity and system health
8. **UserInvite Integration**: Seamless integration with BreatheCode's existing invitation system
9. **Feature Flags**: Gradual rollout and easy feature toggling
10. **Enhanced Security**: Input validation, rate limiting, and proper error handling
11. **Async Support**: Performance optimizations for high-load scenarios

### Key Improvements Added

- **UserInvite Integration**: Complete integration with BreatheCode's existing invitation system, extending both `accept_invite()` and `accept_invite_action()` functions
- **Enhanced Validation**: Robust input validation with proper error messages and email format checking
- **Database Constraints**: Unique constraints and indexes to prevent data inconsistencies
- **Supervisor System**: Automated monitoring for orphaned team members and team size violations
- **Async Support**: Async versions of key functions for better performance
- **Enhanced Serializers**: Detailed serializers with consumable summaries and owner information
- **Security Improvements**: Rate limiting, input sanitization, and proper authentication checks
- **Signal Integration**: Automatic team member activation when invites are accepted through existing BreatheCode flows
- **Validation Standards**: All validations follow BreatheCode's translation patterns with proper error messages and slugs

### Architecture Benefits

- **Team validation moved from Subscription to ServiceItem**: This allows for more granular control where different services can have different team limits
- **ServiceItem-level team methods**: Each service item can independently manage its team members
- **Flexible team configuration**: Different services in the same subscription can have different team capabilities
- **Improved scalability**: Team limits are enforced per service rather than per subscription
- **Production-ready monitoring**: Supervisors ensure system health and data integrity
- **Maintainable codebase**: Following BreatheCode patterns and Django best practices

### Security & Reliability

- **Data Integrity**: Database constraints and validation prevent inconsistent states
- **Automated Recovery**: Supervisors detect and fix common issues automatically
- **Input Validation**: Comprehensive validation with internationalized error messages
- **Rate Limiting**: Protection against abuse and bulk operations
- **Audit Trail**: Complete tracking of team member lifecycle events

The implementation is designed to be backward compatible, production-ready, and follows Django best practices for scalability and maintainability.
