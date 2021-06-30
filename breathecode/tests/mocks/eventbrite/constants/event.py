# https://www.eventbrite.com.mx/platform/api#/reference/event/retrieve-an-event?console=1
EVENTBRITE_EVENT_URL = 'https://www.eventbriteapi.com/v3/events/1/'
EVENTBRITE_EVENT = {
    "id": "1",
    "name": {
        "text": "Some text",
        "html": "<p>Some text</p>"
    },
    "description": {
        "text": "Some text",
        "html": "<p>Some text</p>"
    },
    "start": {
        "timezone": "America/Los_Angeles",
        "utc": "2018-05-12T02:00:00Z",
        "local": "2018-05-11T19:00:00"
    },
    "end": {
        "timezone": "America/Los_Angeles",
        "utc": "2018-05-12T02:00:00Z",
        "local": "2018-05-11T19:00:00"
    },
    "url": "https://www.eventbrite.com/e/45263283700",
    "vanity_url": "https://testevent.eventbrite.com",
    "created": "2017-02-19T20:28:14Z",
    "changed": "2017-02-19T20:28:14Z",
    "published": "2017-02-19T20:28:14Z",
    "status": "live",
    "currency": "USD",
    "online_event": False,
    "organization_id": "1",
    "organizer_id": "1",
    "organizer": {
        "name": "",
        "description": {
            "text": "Some text",
            "html": "<p>Some text</p>"
        },
        "long_description": {
            "text": "Some text",
            "html": "<p>Some text</p>"
        },
        "logo_id": {},
        "logo": {
            "id": "12345",
            "url": "https://image.com",
            "crop_mask": {
                "top_left": {
                    "id": "1",
                    "name": {
                        "text": "Some text",
                        "html": "<p>Some text</p>"
                    },
                    "description": {
                        "text": "Some text",
                        "html": "<p>Some text</p>"
                    },
                    "start": {
                        "timezone": "America/Los_Angeles",
                        "utc": "2018-05-12T02:00:00Z",
                        "local": "2018-05-11T19:00:00"
                    },
                    "end": {
                        "timezone": "America/Los_Angeles",
                        "utc": "2018-05-12T02:00:00Z",
                        "local": "2018-05-11T19:00:00"
                    },
                    "url": "https://www.eventbrite.com/e/45263283700",
                    "vanity_url": "https://testevent.eventbrite.com",
                    "created": "2017-02-19T20:28:14Z",
                    "changed": "2017-02-19T20:28:14Z",
                    "published": "2017-02-19T20:28:14Z",
                    "status": "live",
                    "currency": "USD",
                    "online_event": False,
                    "organization_id": "",
                    "organizer_id": "",
                    "organizer": {
                        "name": "",
                        "description": {
                            "text": "Some text",
                            "html": "<p>Some text</p>"
                        },
                        "long_description": {
                            "text": "Some text",
                            "html": "<p>Some text</p>"
                        },
                        "logo_id": {},
                        "logo": {
                            "id": "1",
                            "url": "https://image.com",
                            "crop_mask": {
                                "top_left": {
                                    "y": 15,
                                    "x": 15
                                },
                                "width": 15,
                                "height": 15
                            },
                            "original": {
                                "url": "https://image.com",
                                "width": 800,
                                "height": 400
                            },
                            "aspect_ratio": "2",
                            "edge_color": "#6a7c8b",
                            "edge_color_set": True
                        },
                        "resource_uri":
                        "https://www.eventbriteapi.com/v3/organizers/1/",
                        "id": "1",
                        "url": "https://www.eventbrite.com/o/1/",
                        "num_past_events": 5,
                        "num_future_events": 1,
                        "twitter": "@abc",
                        "facebook": "abc"
                    },
                    "logo_id": {},
                    "logo": {
                        "id": "1",
                        "url": "https://image.com",
                        "crop_mask": {
                            "top_left": {
                                "y": 15,
                                "x": 15
                            },
                            "width": 15,
                            "height": 15
                        },
                        "original": {
                            "url": "https://image.com",
                            "width": 800,
                            "height": 400
                        },
                        "aspect_ratio": "2",
                        "edge_color": "#6a7c8b",
                        "edge_color_set": True
                    },
                    "venue": {
                        "name": "Great Venue",
                        "age_restriction": {},
                        "capacity": 100,
                        "address": {
                            "address_1": {},
                            "address_2": {},
                            "city": {},
                            "region": {},
                            "postal_code": {},
                            "country": {},
                            "latitude": {},
                            "longitude": {}
                        },
                        "resource_uri":
                        "https://www.eventbriteapi.com/v3/venues/3003/",
                        "id": "3003",
                        "latitude": "49.28497549999999",
                        "longitude": "123.11082529999999"
                    },
                    "format_id": {},
                    "format": {
                        "id":
                        "1",
                        "name":
                        "Seminar or Talk",
                        "name_localized":
                        "Seminar or Talk",
                        "short_name":
                        "Seminar",
                        "short_name_localized":
                        "Seminar",
                        "resource_uri":
                        "https://www.eventbriteapi.com/v3/formats/2/"
                    },
                    "category": {
                        "id":
                        "1",
                        "resource_uri":
                        "https://www.eventbriteapi.com/v3/categories/103/",
                        "name":
                        "Music",
                        "name_localized":
                        "Music",
                        "short_name":
                        "Music",
                        "short_name_localized":
                        "Music",
                        "subcategories": [{
                            "id": "3003",
                            "resource_uri":
                            "https://www.eventbriteapi.com/v3/subcategories/3003/",
                            "name": "Classical",
                            "parent_category": {}
                        }]
                    },
                    "subcategory": {
                        "id": "1",
                        "resource_uri":
                        "https://www.eventbriteapi.com/v3/subcategories/3003/",
                        "name": "Classical",
                        "parent_category": {
                            "id": "1",
                            "resource_uri":
                            "https://www.eventbriteapi.com/v3/categories/103/",
                            "name": "Music",
                            "name_localized": "Music",
                            "short_name": "Music",
                            "short_name_localized": "Music",
                            "subcategories": [{}]
                        }
                    },
                    "music_properties": {
                        "age_restriction": {},
                        "presented_by": {},
                        "door_time": "2019-05-12T-19:00:00Z"
                    },
                    "bookmark_info": {
                        "bookmarked": False
                    },
                    "ticket_availhttps://www.eventbrite.com.mx/platform/api#/reference/event/retrieve-an-event?console=1ability":
                    {
                        "has_available_tickets": False,
                        "minimum_ticket_price": {
                            "currency": "USD",
                            "value": 432,
                            "major_value": "4.32",
                            "display": "4.32 USD"
                        },
                        "maximum_ticket_price": {
                            "currency": "USD",
                            "value": 432,
                            "major_value": "4.32",
                            "display": "4.32 USD"
                        },
                        "is_sold_out": True,
                        "start_sales_date": {
                            "timezone": "America/Los_Angeles",
                            "utc": "2018-05-12T02:00:00Z",
                            "local": "2018-05-11T19:00:00"
                        },
                        "waitlist_available": False
                    },
                    "listed": False,
                    "shareable": False,
                    "invite_only": False,
                    "show_remaining": True,
                    "password": "12345",
                    "capacity": 100,
                    "capacity_is_custom": True,
                    "tx_time_limit": "12345",
                    "hide_start_date": True,
                    "hide_end_date": True,
                    "locale": "en_US",
                    "is_locked": True,
                    "privacy_setting": "unlocked",
                    "is_externally_ticketed": False,
                    "external_ticketing": {
                        "external_url": "",
                        "ticketing_provider_name": "",
                        "is_free": False,
                        "minimum_ticket_price": {
                            "currency": "USD",
                            "value": 432,
                            "major_value": "4.32",
                            "display": "4.32 USD"
                        },
                        "maximum_ticket_price": {
                            "currency": "USD",
                            "value": 432,
                            "major_value": "4.32",
                            "display": "4.32 USD"
                        },
                        "sales_start": "",
                        "sales_end": ""
                    },
                    "is_series": True,
                    "is_series_parent": True,
                    "series_id": "1",
                    "is_reserved_seating": True,
                    "show_pick_a_seat": True,
                    "show_seatmap_thumbnail": True,
                    "show_colors_in_seatmap_thumbnail": True,
                    "is_free": True,
                    "source": "api",
                    "version": "null",
                    "resource_uri":
                    "https://www.eventbriteapi.com/v3/events/1234/",
                    "event_sales_status": {
                        "sales_status": "text",
                        "start_sales_date": {
                            "timezone": "America/Los_Angeles",
                            "utc": "2018-05-12T02:00:00Z",
                            "local": "2018-05-11T19:00:00"
                        }
                    },
                    "checkout_settings": {
                        "created":
                        "2018-01-31T13:00:00Z",
                        "changed":
                        "2018-01-31T13:00:00Z",
                        "country_code":
                        "",
                        "currency_code":
                        "",
                        "checkout_method":
                        "paypal",
                        "offline_settings": [{
                            "payment_method": "CASH",
                            "instructions": ""
                        }],
                        "user_instrument_vault_id":
                        "",
                    },
                    "y": 15,
                    "x": 15,
                },
                "width": 15,
                "height": 15
            },
            "original": {
                "url": "https://image.com",
                "width": 800,
                "height": 400
            },
            "aspect_ratio": "2",
            "edge_color": "#6a7c8b",
            "edge_color_set": True
        },
        "resource_uri": "https://www.eventbriteapi.com/v3/organizers/12345/",
        "id": "1",
        "url": "https://www.eventbrite.com/o/12345/",
        "num_past_events": 5,
        "num_future_events": 1,
        "twitter": "@abc",
        "facebook": "abc"
    },
    "logo_id": {},
    "logo": {
        "id": "1",
        "url": "https://image.com",
        "crop_mask": {
            "top_left": {
                "y": 15,
                "x": 15
            },
            "width": 15,
            "height": 15
        },
        "original": {
            "url": "https://image.com",
            "width": 800,
            "height": 400
        },
        "aspect_ratio": "2",
        "edge_color": "#6a7c8b",
        "edge_color_set": True
    },
    "venue": {
        "name": "Great Venue",
        "age_restriction": {},
        "capacity": 100,
        "address": {
            "address_1": {},
            "address_2": {},
            "city": {},
            "region": {},
            "postal_code": {},
            "country": {},
            "latitude": {},
            "longitude": {}
        },
        "resource_uri": "https://www.eventbriteapi.com/v3/venues/3003/",
        "id": "1",
        "latitude": "49.28497549999999",
        "longitude": "123.11082529999999"
    },
    "format_id": {},
    "format": {
        "id": "1",
        "name": "Seminar or Talk",
        "name_localized": "Seminar or Talk",
        "short_name": "Seminar",
        "short_name_localized": "Seminar",
        "resource_uri": "https://www.eventbriteapi.com/v3/formats/2/"
    },
    "category": {
        "id":
        "1",
        "resource_uri":
        "https://www.eventbriteapi.com/v3/categories/103/",
        "name":
        "Music",
        "name_localized":
        "Music",
        "short_name":
        "Music",
        "short_name_localized":
        "Music",
        "subcategories": [{
            "id": "1",
            "resource_uri":
            "https://www.eventbriteapi.com/v3/subcategories/3003/",
            "name": "Classical",
            "parent_category": {}
        }]
    },
    "subcategory": {
        "id": "1",
        "resource_uri": "https://www.eventbriteapi.com/v3/subcategories/3003/",
        "name": "Classical",
        "parent_category": {
            "id": "1",
            "resource_uri": "https://www.eventbriteapi.com/v3/categories/103/",
            "name": "Music",
            "name_localized": "Music",
            "short_name": "Music",
            "short_name_localized": "Music",
            "subcategories": [{}]
        }
    },
    "music_properties": {
        "age_restriction": {},
        "presented_by": {},
        "door_time": "2019-05-12T-19:00:00Z"
    },
    "bookmark_info": {
        "bookmarked": False
    },
    "ticket_availability": {
        "has_available_tickets": False,
        "minimum_ticket_price": {
            "currency": "USD",
            "value": 432,
            "major_value": "4.32",
            "display": "4.32 USD"
        },
        "maximum_ticket_price": {
            "currency": "USD",
            "value": 432,
            "major_value": "4.32",
            "display": "4.32 USD"
        },
        "is_sold_out": True,
        "start_sales_date": {
            "timezone": "America/Los_Angeles",
            "utc": "2018-05-12T02:00:00Z",
            "local": "2018-05-11T19:00:00"
        },
        "waitlist_available": False
    },
    "listed": False,
    "shareable": False,
    "invite_only": False,
    "show_remaining": True,
    "password": "12345",
    "capacity": 100,
    "capacity_is_custom": True,
    "tx_time_limit": "12345",
    "hide_start_date": True,
    "hide_end_date": True,
    "locale": "en_US",
    "is_locked": True,
    "privacy_setting": "unlocked",
    "is_externally_ticketed": False,
    "external_ticketing": {
        "external_url": "",
        "ticketing_provider_name": "",
        "is_free": False,
        "minimum_ticket_price": {
            "currency": "USD",
            "value": 432,
            "major_value": "4.32",
            "display": "4.32 USD"
        },
        "maximum_ticket_price": {
            "currency": "USD",
            "value": 432,
            "major_value": "4.32",
            "display": "4.32 USD"
        },
        "sales_start": "",
        "sales_end": ""
    },
    "is_series": True,
    "is_series_parent": True,
    "series_id": "1",
    "is_reserved_seating": True,
    "show_pick_a_seat": True,
    "show_seatmap_thumbnail": True,
    "show_colors_in_seatmap_thumbnail": True,
    "is_free": True,
    "source": "api",
    "version": "null",
    "resource_uri": "https://www.eventbriteapi.com/v3/events/1234/",
    "event_sales_status": {
        "sales_status": "text",
        "start_sales_date": {
            "timezone": "America/Los_Angeles",
            "utc": "2018-05-12T02:00:00Z",
            "local": "2018-05-11T19:00:00"
        }
    },
    "checkout_settings": {
        "created": "2018-01-31T13:00:00Z",
        "changed": "2018-01-31T13:00:00Z",
        "country_code": "",
        "currency_code": "",
        "checkout_method": "paypal",
        "offline_settings": [{
            "payment_method": "CASH",
            "instructions": ""
        }],
        "user_instrument_vault_id": ""
    }
}
