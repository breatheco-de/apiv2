import hashlib
import logging
import os
import time
from typing import Optional
from celery import shared_task, Task
from breathecode.services.seo import SEOAnalyzer

from breathecode.media.models import Media, MediaResolution
from breathecode.media.views import media_gallery_bucket
from breathecode.services.google_cloud import FunctionV1
from breathecode.services.google_cloud.storage import Storage
from .models import Asset
from .actions import pull_from_github, screenshots_bucket, test_asset, clean_asset_readme

logger = logging.getLogger(__name__)


def google_project_id():
    return os.getenv('GOOGLE_PROJECT_ID', '')


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 2, 'countdown': 60 * 10}
    retry_backoff = True


@shared_task
def async_pull_from_github(asset_slug, user_id=None):
    logger.debug(f'Synching asset {asset_slug} with data found on github')
    asset = pull_from_github(asset_slug)
    return asset != 'ERROR'


@shared_task
def async_test_asset(asset_slug):
    a = Asset.objects.filter(slug=asset_slug).first()
    if a is None:
        logger.debug(f'Error: Error testing asset with slug {asset_slug}, does not exist.')

    try:
        if test_asset(a):
            return True
    except Exception as e:
        logger.exception(f'Error testing asset {a.slug}')

    return False


@shared_task
def async_clean_asset_readme(asset_slug):
    a = Asset.objects.filter(slug=asset_slug).first()
    if a is None:
        logger.debug(f'Error: Error running SEO report for asset with slug {asset_slug}, does not exist.')

    clean_asset_readme(a)
    return a.cleaning_status == 'OK'


@shared_task
def async_execute_seo_report(asset_slug):
    a = Asset.objects.filter(slug=asset_slug).first()
    if a is None:
        logger.debug(f'Error: Error running SEO report for asset with slug {asset_slug}, does not exist.')

    try:
        report = SEOAnalyzer(a)
        report.start()
    except Exception as e:
        logger.exception(f'Error running SEO report asset {a.slug}')

    return False


@shared_task
def async_create_asset_thumbnail(asset_slug: str):
    asset = Asset.objects.filter(slug=asset_slug).first()
    if asset is None:
        logger.error(f'Asset with slug {asset_slug} not found')
        return

    slug1 = 'learn-to-code'
    slug2 = asset_slug
    url = f'https://4geeksacademy.com/us/{slug1}/{slug2}/preview'
    func = FunctionV1(region='us-central1', project_id=google_project_id(), name='screenshots', method='GET')

    name = f'{slug1}-{slug2}.png'
    response = func.call(
        params={
            'url': url,
            'name': name,
            'dimension': '1200x630',
            # this should be fixed if the screenshots is taken without load the content properly
            'delay': 1000,
        },
        timeout=5)

    if response.status_code >= 400:
        logger.error('Unhandled error with async_create_asset_thumbnail, the cloud function `screenshots` '
                     f'returns status code {response.status_code}')
        return

    json = response.json()
    json = json[0]

    url = json['url']
    filename = json['filename']

    storage = Storage()
    cloud_file = storage.file(screenshots_bucket(), filename)

    # reattempt 60 times
    for _ in range(0, 60):
        content_file = cloud_file.download()
        if not content_file:
            time.sleep(1)
            cloud_file = storage.file(screenshots_bucket(), filename)
            continue

        hash = hashlib.sha256(content_file).hexdigest()
        break

    # file already exists for this academy
    if Media.objects.filter(hash=hash, academy=asset.academy).exists():
        # this prevent a screenshots duplicated
        cloud_file.delete()
        logger.warn(f'Media with hash {hash} already exists, skipping')
        return

    # file already exists for another academy
    media = Media.objects.filter(hash=hash).first()
    if media:
        # this prevent a screenshots duplicated
        cloud_file.delete()
        media = Media(slug=f'asset-{asset_slug}',
                      name=media.name,
                      url=media.url,
                      thumbnail=media.thumbnail,
                      academy=asset.academy,
                      mime=media.mime,
                      hash=media.hash)
        media.save()

        logger.warn(f'Media was save with {hash} for academy {asset.academy}')
        return

    # if media does not exist too, keep the screenshots with other name
    cloud_file.rename(hash)
    url = f'https://storage.googleapis.com/{screenshots_bucket()}/{hash}'

    media = Media(
        slug=f'asset-{asset_slug}',
        name=name,
        url=url,
        thumbnail=f'{url}-thumbnail',
        academy=asset.academy,
        mime='image/png',  # this should change in a future, check the cloud function
        hash=hash)
    media.save()

    logger.warn(f'Media was save with {hash} for academy {asset.academy}')


@shared_task
def async_resize_asset_thumbnail(media_id: int, width: Optional[int] = 0, height: Optional[int] = 0):
    media = Media.objects.filter(id=media_id).first()
    if media is None:
        logger.error(f'Media with id {media_id} not found')
        return

    if not width and not height:
        logger.error('async_resize_asset_thumbnail needs the width or height parameter')
        return

    if width and height:
        logger.error("async_resize_asset_thumbnail can't be used with width and height together")
        return

    kwargs = {'width': width} if width else {'height': height}

    func = FunctionV1(region='us-central1', project_id=google_project_id(), name='resize-image')

    response = func.call({
        **kwargs,
        'filename': media.hash,
        'bucket': media_gallery_bucket(),
    })

    res = response.json()

    if not res['status_code'] == 200 or not res['message'] == 'Ok':
        logger.error(f'Unhandled error with `resize-image` cloud function, response {res}')
        return

    resolution = MediaResolution(width=res['width'], height=res['height'], hash=media.hash)
    resolution.save()
