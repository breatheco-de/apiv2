This si how the payment goes

## 1) First we create a bag by calling checking:

PUT /v2/payments/checking

```json
{"type":"PREVIEW","plans":["4geeks-plus-subscription"],"country_code":"US","service_items":[]}
```
Successfull response payload:

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
    "token": "409a031c3ff6e2f55394722d4c05db63bd336df4",
    "seat_service_item": null,
    "expires_at": "2025-10-11T17:42:38.186215Z"
}
```

You will get all the service items that are included in the plan, this services are ideal to explain to the user which features are included in he plan.
If the "coupons" key on the response payload has a none-empty array, it meanse this plan has coupons that need to be "auto aplied"
If the coupon is applied, we need to show the real price crossed over and the new price with the discount applied.

## 2) Then the user needs to fill the card and press the button to pay:

We call the first endpoint first to save the card on the payment platform (stripe)

POST /v2/payments/card
Request Payload: 
```json
{"card_number":"4242424242424242","exp_month":"10","exp_year":"26","cvc":"435","academy":47}
```

Response payload like this:
Status: 200
```json
{
    "status": "ok",
    "details": {
        "4Geeks.com": {
            "card_last4": "4242",
            "card_brand": "Visa",
            "card_exp_month": 10,
            "card_exp_year": 2026
        }
    }
}
```

## 3) After the card was saved, we call the "pay" endpoint to charge the user:

Then you call the pay method like this: 
POST /v2/payments/pay
```json
{"country_code":"US","type":"PREVIEW","token":"cc70fb0c3bff8f0967205b0b46acc8610a74a3c7","chosen_period":"YEAR","coupons":[{"slug":"new-year-50","discount_type":"PERCENT_OFF","discount_value":0.5,"referral_type":"NO_REFERRAL","referral_value":0,"auto":true,"offered_at":"2025-02-04T22:04:29Z","expires_at":"2026-10-06T17:52:36Z"}],"add_ons":[],"conversion_info":{"user_agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36","landing_url":"/","conversion_url":"/","internal_cta_placement":"navbar-get-started"}}
```

Successfull Response payload:
Status: 200
```json
{
    "amount": 239.995,
    "currency": {
        "code": "USD",
        "name": "US Dollar"
    },
    "paid_at": "2025-10-11T16:35:12.904426Z",
    "status": "FULFILLED",
    "user": {
        "first_name": "Ramon",
        "last_name": "Peralta",
        "email": "aalejo+ramon@gmail.com"
    },
    "id": 7018,
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
        }
    ]
}
```

If the payment failed we get the following payload:
status: 4xx
Failed Response payload:
```json
{
    "detail": "Card declined",
    "status_code": 402,
    "silent": true,
    "silent_code": "card-error"
}
```