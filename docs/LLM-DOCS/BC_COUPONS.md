Keep in mind that some coupons already come "auto-applied" in the bag, in the "coupons" json key, this auto aplied coupons will have to be shown in the coupon section as well.

## Applying a coupon

Before applying a coupon we need to make sure is valid, we call the following endpoint:

GET /v2/payments/coupon?coupons=<coupon_slug>&plan=<subscription_slug>

We get an answer with all the valid coupons, like this:

```json
[
    {
        "slug": "new-year-50",
        "discount_type": "PERCENT_OFF",
        "discount_value": 0.5,
        "referral_type": "NO_REFERRAL",
        "referral_value": 0.0,
        "auto": true,
        "offered_at": "2025-02-04T22:04:29Z",
        "expires_at": "2026-10-06T17:52:36Z"
    }
]
```

If the expected coupon slug is included in the array, the coupon is valid for this plan, otherwise the following error has to be shown:

`This coupon is invalid or doesn't work for the 4Geeks Plus Subscription plan. If you think this is an error, contact support@learnpack.co`

### Applying the valid coupon to the bag

If the coupon being applied is valid, we need to update the bag to make sure the coupon is applied:

PUT /v2/payments/bag/2414288/coupon?coupons=&plan=4geeks-plus-subscription

No request payload needed, the "coupons" querystring variable will determine the coupons applied to the plan, if empty, no extra coupons will be applied.
If the user applies a coupon we call the endpoint with querystring variable `coupons=<coupon_slug>` but if the coupon gets removed, we call the endpoint with `coupons=<empty>`

Here is the sample response payload after updating the bag to apply the 2 coupons `new-year-50,fakevalid`:

```json
{
    "id": 2414288,
    "service_items": [],
    "plans": [
        {
            "title": null,
            "slug": "4geeks-plus-subscription",
            "status": "ACTIVE",
            "time_of_life": 0,
            "time_of_life_unit": null,
            "trial_duration": 0,
            "trial_duration_unit": "MONTH",
            "service_items": [
                {
                    "unit_type": "UNIT",
                    "how_many": -1,
                    "sort_priority": 6,
                    "service": {
                        "id": 45,
                        "title": "Earn course certificates",
                        "slug": "course-certificates",
                        "icon_url": null,
                        "private": true,
                        "groups": [],
                        "type": "COHORT_SET",
                        "consumer": "NO_SET",
                        "session_duration": null
                    },
                    "is_team_allowed": false
                },
                {
                    "unit_type": "UNIT",
                    "how_many": -1,
                    "sort_priority": 1,
                    "service": {
                        "id": 106,
                        "title": "Generate Content with AI",
                        "slug": "ai-generation",
                        "icon_url": null,
                        "private": true,
                        "groups": [
                            {
                                "name": "Creator",
                                "permissions": [
                                    {
                                        "name": "Create packages in learnpack",
                                        "codename": "learnpack_create_package"
                                    }
                                ]
                            }
                        ],
                        "type": "VOID",
                        "consumer": "AI_INTERACTION",
                        "session_duration": null
                    },
                    "is_team_allowed": false
                },
                {
                    "unit_type": "UNIT",
                    "how_many": 5000,
                    "sort_priority": 2,
                    "service": {
                        "id": 93,
                        "title": "AI Chat",
                        "slug": "ai-conversation-message",
                        "icon_url": null,
                        "private": true,
                        "groups": [],
                        "type": "VOID",
                        "consumer": "AI_INTERACTION",
                        "session_duration": null
                    },
                    "is_team_allowed": false
                },
                {
                    "unit_type": "UNIT",
                    "how_many": 2,
                    "sort_priority": 3,
                    "service": {
                        "id": 52,
                        "title": "Mentorships from experts",
                        "slug": "mentorships-from-experts",
                        "icon_url": null,
                        "private": true,
                        "groups": [
                            {
                                "name": "Mentorships",
                                "permissions": [
                                    {
                                        "name": "Get my mentoring sessions",
                                        "codename": "get_my_mentoring_sessions"
                                    },
                                    {
                                        "name": "Join mentorship",
                                        "codename": "join_mentorship"
                                    }
                                ]
                            }
                        ],
                        "type": "MENTORSHIP_SERVICE_SET",
                        "consumer": "JOIN_MENTORSHIP",
                        "session_duration": null
                    },
                    "is_team_allowed": true
                },
                {
                    "unit_type": "UNIT",
                    "how_many": 3,
                    "sort_priority": 1,
                    "service": {
                        "id": 109,
                        "title": "Publish a LearnPack tutorial",
                        "slug": "learnpack-publish",
                        "icon_url": null,
                        "private": false,
                        "groups": [
                            {
                                "name": "Creator",
                                "permissions": [
                                    {
                                        "name": "Create packages in learnpack",
                                        "codename": "learnpack_create_package"
                                    }
                                ]
                            }
                        ],
                        "type": "VOID",
                        "consumer": "NO_SET",
                        "session_duration": null
                    },
                    "is_team_allowed": true
                },
                {
                    "unit_type": "UNIT",
                    "how_many": 5000,
                    "sort_priority": 1,
                    "service": {
                        "id": 48,
                        "title": "AI compilation",
                        "slug": "ai-compilation",
                        "icon_url": null,
                        "private": true,
                        "groups": [],
                        "type": "VOID",
                        "consumer": "AI_INTERACTION",
                        "session_duration": null
                    },
                    "is_team_allowed": true
                },
                {
                    "unit_type": "UNIT",
                    "how_many": -1,
                    "sort_priority": 1,
                    "service": {
                        "id": 111,
                        "title": "Access to all of our Courses",
                        "slug": "access-to-all-courses",
                        "icon_url": null,
                        "private": true,
                        "groups": [
                            {
                                "name": "Student",
                                "permissions": [
                                    {
                                        "name": "Get my containers",
                                        "codename": "get_containers"
                                    },
                                    {
                                        "name": "Get my certificate",
                                        "codename": "get_my_certificate"
                                    },
                                    {
                                        "name": "Get my mentoring sessions",
                                        "codename": "get_my_mentoring_sessions"
                                    },
                                    {
                                        "name": "Upload assignment telemetry",
                                        "codename": "upload_assignment_telemetry"
                                    }
                                ]
                            }
                        ],
                        "type": "COHORT_SET",
                        "consumer": "READ_LESSON",
                        "session_duration": null
                    },
                    "is_team_allowed": true
                }
            ],
            "financing_options": [],
            "has_available_cohorts": true
        }
    ],
    "coupons": [
        {
            "slug": "new-year-50",
            "discount_type": "PERCENT_OFF",
            "discount_value": 0.5,
            "referral_type": "NO_REFERRAL",
            "referral_value": 0.0,
            "auto": true,
            "offered_at": "2025-02-04T22:04:29Z",
            "expires_at": "2026-10-06T17:52:36Z"
        },
        {
            "slug": "FAKEVALID",
            "discount_type": "PERCENT_OFF",
            "discount_value": 0.1,
            "referral_type": "NO_REFERRAL",
            "referral_value": 0.0,
            "auto": false,
            "offered_at": "2025-10-11T17:09:40Z",
            "expires_at": null
        }
    ],
    "status": "CHECKING",
    "type": "PREVIEW",
    "is_recurrent": true,
    "was_delivered": false,
    "amount_per_month": 59.99,
    "amount_per_quarter": 0.0,
    "amount_per_half": 0.0,
    "amount_per_year": 479.99,
    "token": "945eea360b08fd2dc1ffd057a566f7db377de2de",
    "seat_service_item": null,
    "expires_at": "2025-10-11T17:42:38.339883Z"
}
```