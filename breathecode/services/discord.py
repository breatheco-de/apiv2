import logging
import os

import aiohttp
import requests
from capyc.rest_framework.exceptions import ValidationException

from breathecode.authenticate.models import AcademyAuthSettings

logger = logging.getLogger(__name__)


class Discord:
    def __init__(self, academy_id=None):
        self.academy_id = academy_id
        self.bot_token = self._get_bot_token()

    def _get_bot_token(self):
        if self.academy_id:
            try:
                settings = AcademyAuthSettings.objects.filter(academy__id=self.academy_id).first()
                if settings and settings.discord_settings:
                    token = settings.discord_settings.get("discord_bot_token")
                    if token:
                        return token
            except Exception as e:
                logger.error(f"Error obtainging token from AcademyAuthSettings: {e}")

        # Fallback a variable de entorno
        token = os.getenv("DISCORD_BOT_TOKEN", "")
        if not token:
            logger.warning("DISCORD_BOT_TOKEN not configured")
        return token

    def join_user_to_guild(self, access_token: str, guild_id: int, discord_user_id: int):
        join_result = self._join_guild(access_token, guild_id, discord_user_id)

        if join_result.status_code == 201:

            return join_result

        elif join_result.status_code == 204:
            logger.debug("User already in the Discord server")
            return join_result
        else:
            return join_result

    def _join_guild(self, access_token, guild_id, discord_user_id):
        """Une usuario al servidor de Discord"""
        url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{discord_user_id}"

        headers = {"Authorization": f"Bot {self.bot_token}", "Content-Type": "application/json"}

        payload = {"access_token": access_token}

        try:
            response = requests.put(url, headers=headers, json=payload)

            if response.status_code == 201:
                logger.info(f"User {discord_user_id} successfully joined guild {guild_id}")
                return response
            else:
                error_msg = f"Discord API error {response.status_code}"
                error_data = response.json()
                error_msg += f': {error_data.get("message", "Unknown error")}'

                logger.error(error_msg)
                return response

        except Exception as e:
            logger.error(f"Error joining user {discord_user_id} to guild {guild_id}, {e}")
            return response

    def assign_role_to_user(self, guild_id: int, discord_user_id: int, role_id: int):
        headers = {"Authorization": f"Bot {self.bot_token}"}
        url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{discord_user_id}/roles/{role_id}"
        try:
            response = requests.put(url, headers=headers)
            if response.status_code == 204:
                logger.info(f"Role {role_id} assigned to user {discord_user_id} in guild {guild_id}")
                return response.status_code
            else:
                error_msg = f"Error assigning role {response}"
                logger.error(error_msg)
                return response.status_code

        except requests.exceptions.RequestException as e:
            logger.error(f"Error assigning role to user {discord_user_id}: {str(e)}")
            return False

    def remove_role_to_user(self, guild_id: int, discord_user_id: int, role_id: int):
        headers = {"Authorization": f"Bot {self.bot_token}"}
        url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{discord_user_id}/roles/{role_id}"
        try:
            response = requests.delete(url, headers=headers)
            if response.status_code == 204:
                logger.info(f"Role {role_id} removed from user {discord_user_id} in guild {guild_id}")
                return response.status_code
            else:
                return response.status_code

        except requests.exceptions.RequestException as e:
            logger.error(f"Error assigning role to user {discord_user_id}: {str(e)}")
            return False

    async def send_dm_to_user(self, discord_user_id: int, message: str):
        headers = {"Authorization": f"Bot {self.bot_token}", "Content-Type": "application/json"}
        try:
            async with aiohttp.ClientSession() as session:
                """Create a DM channel"""
                url_dm_channel = "https://discord.com/api/v10/users/@me/channels"
                payload_dm_channel = {"recipient_id": discord_user_id}

                async with session.post(url_dm_channel, json=payload_dm_channel, headers=headers) as dm_response:
                    if dm_response.status != 200:
                        return dm_response.status

                    data = await dm_response.json()
                    dm_channel_id = data["id"]
                    url_send_message = f"https://discord.com/api/v10/channels/{dm_channel_id}/messages"
                    payload_message = {"content": message}

                    if not dm_channel_id:
                        logger.error("No DM channel ID received from Discord")
                    async with session.post(url_send_message, headers=headers, json=payload_message) as response_msg:
                        if response_msg.status == 200:
                            logger.info(f"DM sent succesfully to user {discord_user_id}")
                            return response_msg.status
                        elif response_msg.status == 404:
                            error_msg = "DM channel not found"
                            logger.error(f"Not found error: {error_msg}")
                            return response_msg.status
        except Exception as e:
            logger.error(f"Error sending DM: {str(e)}")
            raise ValidationException(str(e))

    def get_member_in_server(self, discord_user_id: int, guild_id: int):
        headers = {"Authorization": f"Bot {self.bot_token}"}
        url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{discord_user_id}"
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response
            elif response.status_code == 404:
                logger.info(f"User {discord_user_id} is not in guild {guild_id}")
                return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Error obtaining user {discord_user_id}: {str(e)}")
            return False
