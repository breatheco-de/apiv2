import json
from ..decorator import action
from breathecode.monitoring.models import Endpoint
class Monitoring:

    def __init__(self, context):
        self.context = context

    # disable endpoint testing until specific time
    @action(only='staff')
    def snooze_test_endpoint(self, **kwargs):

        selected_date = kwargs['actions'][0]['selected_date']
        endpoint_id = kwargs['state']['endpoint_id']
        print(endpoint_id)
        e = Endpoint.objects.get(id=endpoint_id)
        e.paused_until = selected_date
        e.save()

        return {
            "text": "✅ The endpoint test has been snoozed until "+selected_date,
            "response_type": "ephemeral"
        }

def render_snooze_text_endpoint(endpoints):
    
    snooze_dates = []
    for e in endpoints:
        snooze_dates.append({
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"*App:* {e.application.title} \n *URL:* {e.url} \n *Status:* {e.status} \n *Details:* {e.status_text}",
			},
			"accessory": {
				"type": "datepicker",
				"placeholder": {
					"type": "plain_text",
					"text": "Select a date to snooze",
					"emoji": True
				},
				"action_id": json.dumps({ "class": "monitoring", "method": "snooze_test_endpoint", "endpoint_id": e.id })
			}
		})

    return 	[
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🛑 Endpoint monitor error!",
                "emoji": True
            }
        }
    ] + snooze_dates