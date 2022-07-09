import logging
from django.dispatch import receiver
from .models import Asset, AssetAlias
from .signals import asset_slug_modified

logger = logging.getLogger(__name__)


@receiver(asset_slug_modified, sender=Asset)
def post_asset_slug_modified(sender, instance: Asset, **kwargs):
    logger.debug('Procesing asset slug creation')
    if instance.lang == 'en':
        instance.lang = 'us'

    # create a new slug alias but keep the old one for redirection purposes
    alias = AssetAlias.objects.create(slug=instance.slug, asset=instance)

    # add the asset as the first translation
    a = Asset.objects.get(id=instance.id)
    a.all_translations.add(instance)
    instance.save()
