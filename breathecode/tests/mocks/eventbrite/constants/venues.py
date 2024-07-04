# https://www.eventbrite.com.mx/platform/api#/reference/event/retrieve-an-event?console=1
EVENTBRITE_VENUES_URL = "https://www.eventbriteapi.com/v3/organizations/:id/venues/"
EVENTBRITE_VENUES = {
    "pagination": {"object_count": 1, "page_number": 1, "page_size": 50, "page_count": 1, "has_more_items": False},
    "venues": [
        {
            "address": {
                "address_1": "11200 Southwest 8th Street",
                "address_2": "",
                "city": "Miami",
                "region": "FL",
                "postal_code": "33174",
                "country": "US",
                "latitude": "25.7580596",
                "longitude": "-80.37702200000001",
                "localized_address_display": "11200 Southwest 8th Street, Miami, FL 33174",
                "localized_area_display": "Miami, FL",
                "localized_multi_line_address_display": ["11200 Southwest 8th Street", "Miami, FL 33174"],
            },
            "resource_uri": "https://www.eventbriteapi.com/v3/venues/1/",
            "id": "1",
            "age_restriction": None,
            "capacity": None,
            "name": "Florida International University College of Business",
            "latitude": "25.7580596",
            "longitude": "-80.37702200000001",
        }
    ],
}


def get_eventbrite_venues_url(id: str):
    return EVENTBRITE_VENUES_URL.replace(":id", id)
