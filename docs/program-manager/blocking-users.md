# Blocking Users

## Blocking Users from Mentorship Services

This document explains how program managers can block users from accessing mentorship services in different scenarios.

### Overview

The system allows blocking users from specific services based on different scopes. The blocking configuration uses service identifiers (like `"mentorship-service"`) to determine which service the blocks apply to. When a user is related to any of the blocking scopes for a service, they will be blocked from accessing that service.

The blocking scopes are:

1. Block from everywhere (platform-wide for the service)
2. Block from specific academy (when user is in that academy)
3. Block from specific cohort (when user is in that cohort)
4. Block from specific mentorship service (when user tries to access that specific service)

### Configuration

The blocking configuration is managed in the `breathecode/payments/flags.py` file through the `blocked_user_ids` dictionary.

#### Structure

```python
blocked_user_ids = {
    "mentorship-service": {  # Service identifier
        # Users blocked from this service across the entire platform
        "from_everywhere": [],
        # Users blocked from this service when in specific academies
        "from_academy": [],
        # Users blocked from this service when in specific cohorts
        "from_cohort": [],
        # Users blocked from specific instances of this service
        "from_mentorship_service": []
    }
}
```

### How to Block Users

#### 1. Block User Platform-wide

To block a user from accessing a specific service type across the entire platform:

1. Add the user's ID to the `from_everywhere` list under the appropriate service identifier:

```python
blocked_user_ids = {
    "mentorship-service": {  # Service to block
        "from_everywhere": [123],  # User ID will be blocked from all mentorship services
        ...
    }
}
```

#### 2. Block User from Service in Specific Academy

To block a user from accessing a service type when they are in a specific academy:

1. Add a tuple containing the user's ID and academy slug to the `from_academy` list:

```python
blocked_user_ids = {
    "mentorship-service": {  # Service to block
        "from_academy": [(123, "downtown-miami")],  # User 123 can't access mentorship services in downtown-miami academy
        ...
    }
}
```

#### 3. Block User from Service in Specific Cohort

To block a user from accessing a service type when they are in a specific cohort:

1. Add a tuple containing the user's ID and cohort slug to the `from_cohort` list:

```python
blocked_user_ids = {
    "mentorship-service": {  # Service to block
        "from_cohort": [(123, "4geeks-fs-1")],  # User 123 can't access mentorship services in 4geeks-fs-1 cohort
        ...
    }
}
```

#### 4. Block User from Specific Service Instance

To block a user from accessing a specific instance of a service:

1. Add a tuple containing the user's ID and service slug to the `from_mentorship_service` list:

```python
blocked_user_ids = {
    "mentorship-service": {  # Service type
        "from_mentorship_service": [(123, "geekpal-1-1")],  # User 123 can't access the geekpal-1-1 service specifically
        ...
    }
}
```

### Checking Block Status

Users can check their block status for different services by making a GET request to the `/v1/payments/me/service/blocked` endpoint. The response will indicate if they are blocked and from where:

```json
{
  "mentorship-service": {
    // Service identifier
    "from_everywhere": false, // Not blocked platform-wide
    "from_academy": ["academy-slug"], // Blocked in these academies
    "from_cohort": ["cohort-slug"], // Blocked in these cohorts
    "from_mentorship_service": ["service-slug"] // Blocked from these specific services
  }
}
```

### Important Notes

1. Blocking is enforced through the `payments.can_access` feature flag.
2. When a user is blocked, they will receive a 403 error with the message "You have been blocked from accessing this mentorship service".
3. Blocks are evaluated based on the user's relationships:
   - If they are in a blocked academy
   - If they are in a blocked cohort
   - If they try to access a specifically blocked service
   - If they are blocked platform-wide
4. Program managers should keep track of blocked users and review blocks periodically.
5. Changes to the blocking configuration require a deployment to take effect.

### Best Practices

1. Document the reason for blocking each user
2. Use the most specific blocking scope appropriate for the situation
3. Regularly review blocked users to ensure blocks are still necessary
4. Maintain a separate list of blocked users and reasons outside the code
5. Consider implementing a temporary blocking mechanism for short-term blocks
