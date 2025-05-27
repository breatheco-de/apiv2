from django.core.management.base import BaseCommand
from breathecode.registry.models import Asset

class Command(BaseCommand):
    help = 'Set all asset.feature values to False one by one'

    def handle(self, *args, **options):
        assets = Asset.objects.filter(feature=True, category__isnull=False)
total_count = assets.count()

if total_count == 0:
    print('No assets found with feature set to True.')
    return

print(f'Found {total_count} assets with feature=True. Updating one by one...')

updated_count = 0
for asset in assets:
    asset.feature = False
    asset.save()
    updated_count += 1
    print(f'Processed {updated_count}/{total_count} assets...')

print(f'Successfully processed {total_count} assets. Updated {updated_count} assets to set feature to False.')