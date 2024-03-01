import asyncio
from typing import TypedDict

from django.contrib.auth.models import User, UserManager
from django.core.management.base import BaseCommand
from django.db.models import Q
from linked_services.django.service import Service

from breathecode.authenticate.actions import aget_app

from ...models import App, FirstPartyCredentials


class ExternalIds(TypedDict):
    user: User
    rigobot_id: int


class Command(BaseCommand):
    help = 'Get first-party IDs for specified apps'

    def add_arguments(self, parser) -> None:
        parser.add_argument('app_names', nargs='+', type=str, help='List of app names for which to get first-party IDs')

    def handle(self, *args, **options) -> None:
        self.app_names = options['app_names']
        self.apps: list[App] = []
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.async_handle(*args, **options))

    async def async_handle(self, *args, **options) -> None:
        try:
            await self.set_apps()

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error while getting apps: {e}'))
            return

        users = await self.get_users()

        page_side = 200
        start = 0
        end = page_side

        users[start:end]
        while batch := users[start:end]:
            self.stdout(self.style.SUCCESS(f'Processing {start} to {end}'))
            not_found = []

            async for user in batch:
                if not user.credentials:
                    not_found.append(user)

            credentials = await self.get_external_ids(batch)

            to_create = []
            to_update = []

            for x in credentials:
                if x['user'] in not_found:
                    to_create.append(x)

                else:
                    to_update.append(x)

            await self.create_credentials(to_create)
            await self.update_credentials(to_update)

            start += page_side
            end += page_side
            users[start:end]

    async def set_apps(self) -> None:
        for app_name in self.app_names:

            app = await aget_app(app_name)
            self.apps.append(app)

        if not self.apps:
            raise Exception('No services provided')

    async def get_users(self) -> UserManager[User]:
        query = Q(credentials__isnull=True)
        fields = ['id', 'email']

        for app_name in self.app_names:
            query = query | Q(**{f'credentials__{app_name}__isnull': True})
            fields.append(f'credentials__{app_name}_id')

        return User.objects.filter(query).only(**fields)

    async def get_external_ids(self, users: list[User]) -> list[ExternalIds]:
        external_ids = {}

        cache = {}
        map = dict([(user.email, user) async for user in users])
        keys = list(map.keys())

        # fetch
        for app in self.apps:
            async with Service(app) as s:
                res = await s.get(params={'email': ','.join(keys)})
                cache[app.slug] = await res.json()

        # fill
        for app in self.apps:
            res = cache[app.slug]
            for x in res:
                default = {'user': map[x['email']]}
                current = external_ids.get(x['email'], default)
                current[app.slug + '_id'] = x['id']
                external_ids[x['email']] = current

        return list(external_ids.values())

    async def create_credentials(self, external_ids: list[ExternalIds]):
        if not external_ids:
            return

        await FirstPartyCredentials.objects.abulk_create([x for x in external_ids])

    async def update_credentials(self, external_ids: list[ExternalIds]):
        if not external_ids:
            return

        promises = []
        for ids in external_ids:
            u = ids.pop('user')
            promise = FirstPartyCredentials.objects.filter(user=u).aupdate(**ids)
            promises.append(promise)

        await asyncio.gather(*promises)
