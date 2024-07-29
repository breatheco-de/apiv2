"""
Possible parameters for this command:
- bot_slug: Name of the bot to chat with

"""

import openai

from breathecode.mentorship.models import ChatBot
from ..decorator import command
from ..exceptions import SlackException


@command(capable_of="chatbot_message")
def execute(bot_name=None, academies=None, **context):

    if academies is None:
        academies = []

    query = ChatBot.objects.filter(academy__id__in=[academies])

    if bot_name is not None:
        query = query.filter(slug=bot_name)

    bot = query.first()
    if bot is None:
        raise SlackException("No chatbot was found to respond this message.", slug="chatbot-not-found")

    text = context["text"]

    openai.organization = bot.api_organization
    openai.api_key = bot.api_key
    result = openai.Completion.create(model="text-davinci-003", prompt=text, max_tokens=2000, temperature=0)

    response = {"blocks": []}
    response["blocks"].append(render_message(result))

    return response


def render_message(result):

    message = result["choices"].pop()

    return {"type": "section", "text": {"type": "mrkdwn", "text": f"""{message["text"]}"""}}
