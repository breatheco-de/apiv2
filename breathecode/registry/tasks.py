import hashlib
import logging
import os
import time
import re
import pathlib
from typing import Optional
from celery import shared_task, Task
from breathecode.services.seo import SEOAnalyzer
from django.utils import timezone
from bs4 import BeautifulSoup
from breathecode.media.models import Media, MediaResolution
from breathecode.media.views import media_gallery_bucket
from breathecode.services.google_cloud import FunctionV1
from breathecode.services.google_cloud.storage import Storage
from .models import Asset, AssetImage
from .actions import (pull_from_github, screenshots_bucket, test_asset, clean_asset_readme,
                      upload_image_to_bucket, asset_images_bucket)

logger = logging.getLogger(__name__)


def google_project_id():
    return os.getenv('GOOGLE_PROJECT_ID', '')


img_regex = r'https?:(?:[/|.|\w|\s|-])*\.(?:jpg|gif|png|svg|jpeg)'


def is_remote_image(_str):
    if _str is None or _str == '' or asset_images_bucket() in _str:
        return False

    match = re.search(img_regex, _str)
    if match is None:
        return False

    return True


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 2, 'countdown': 60 * 10}
    retry_backoff = True


@shared_task
def async_pull_from_github(asset_slug, user_id=None):
    logger.debug(f'Synching asset {asset_slug} with data found on github')
    asset = pull_from_github(asset_slug)
    return asset.sync_status != 'ERROR'


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
def async_regenerate_asset_readme(asset_slug):
    a = Asset.objects.filter(slug=asset_slug).first()
    if a is None:
        logger.debug(f'Error: Error running SEO report for asset with slug {asset_slug}, does not exist.')

    a.readme = a.readme_raw
    a.save()
    clean_asset_readme(a)

    async_download_readme_images.delay(a.slug)

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

    func = FunctionV1(region='us-central1', project_id=google_project_id(), name='screenshots', method='GET')

    name = f'{slug1}-{slug2}.png'
    response = func.call(
        params={
            'url': asset.get_preview_generation_url(),
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
def async_download_readme_images(asset_slug):
    logger.debug(f'Downloading images for asset {asset_slug}')

    from ..services.google_cloud import Storage

    asset = Asset.get_by_slug(asset_slug)
    if asset is None:
        raise Exception(f'Asset with slug {asset_slug} not found')

    readme = asset.get_readme(parse=True)
    if 'html' not in readme:
        logger.error(f'Asset with {asset_slug} readme cannot be parse into an HTML')
        return False

    images = BeautifulSoup(readme['html'], features='html.parser').find_all('img', attrs={'srcset': True})

    # check if old images are stil in the new markdown file
    old_images = asset.images.all()
    no_longer_used = {}
    for img in old_images:
        # we will assume they are not by default
        no_longer_used[img.original_url] = img

    image_links = []
    for image in images:
        image_links.append(image['src'])

        srcset = image.attrs.get('srcset')
        if srcset and srcset != '':
            srcsets = [src.strip().split(' ')[0] for src in srcset.split(',')]
            image_links += srcsets

    additional_img_urls = list(re.finditer(img_regex, readme['html']))
    while len(additional_img_urls) > 0:
        match = additional_img_urls.pop(0)
        if match is not None:
            img_url = match.group()
            image_links.append(img_url)

    image_links = list(dict.fromkeys(filter(lambda x: is_remote_image(x), image_links)))
    logger.debug(f'Found {len(image_links)} images on asset {asset_slug}')

    # create subfolder with the page name
    if len(image_links) == 0:
        print('No images found')
        return False

    for link in image_links:
        if link in no_longer_used:
            del no_longer_used[link]
        async_download_single_readme_image.delay(asset_slug, link)

    # delete asset from this image
    logger.debug(f'Found {len(no_longer_used)} images no longer used on asset {asset_slug}')
    for old_img in no_longer_used:
        no_longer_used[old_img].assets.remove(asset)

        # if its not being sed on any other asset, we delete it from cloud
        if no_longer_used[old_img].assets.count() == 0:
            async_remove_img_from_cloud(no_longer_used[old_img].id)

    return True


@shared_task
def async_delete_asset_images(asset_slug):

    asset = Asset.get_by_slug(asset_slug)
    if asset is None:
        raise Exception(f'Asset with slug {asset_slug} not found')

    storage = Storage()
    for img in asset.images.all():
        if img.assets.count() == 1 and img.asset.filter(slug=asset_slug).exists():
            extension = pathlib.Path(img.name).suffix
            cloud_file = storage.file(asset_images_bucket(), img.hash + extension)
            cloud_file.delete()
            img.delete()
        else:
            img.assets.remove(asset)

        logger.info(f'Image {img.name} was deleted')

    return True


@shared_task
def async_remove_img_from_cloud(id):

    logger.info(f'async_remove_img_from_cloud')

    img = AssetImage.objects.filter(id=id).first()
    if img is None:
        raise Exception(f'Image with id {id} not found')

    img_name = img.name

    storage = Storage()
    extension = pathlib.Path(img.name).suffix
    cloud_file = storage.file(asset_images_bucket(), img.hash + extension)
    cloud_file.delete()
    img.delete()

    logger.info(f'Image id ({img_name}) was deleted from the cloud')
    return True


@shared_task
def async_upload_image_to_bucket(id):

    img = AssetImage.objects.filter(id=id).first()
    if img is None:
        raise Exception(f'Image with id {id} not found')

    img.download_status = 'PENDING'
    img.download_details = f'Downloading {link}'
    img.save()

    try:
        img = upload_image_to_bucket(img, asset)
    except Exception as e:
        img.download_details = str(e)
        img.download_status = 'ERROR'
        logger.error(str(e))
        return False

    img.save()
    return img.download_status


@shared_task
def async_download_single_readme_image(asset_slug, link):

    asset = Asset.get_by_slug(asset_slug)
    if asset is None:
        raise Exception(f'Asset with slug {asset_slug} not found')

    img = AssetImage.objects.filter(original_url=link).first()
    if img is None:
        temp_filename = link.split('/')[-1].split('?')[0]
        img = AssetImage(name=temp_filename, original_url=link, last_download_at=timezone.now())

    if img.download_status != 'OK':

        img.download_status = 'PENDING'
        img.download_details = f'Downloading {link}'
        img.save()

        try:
            img = upload_image_to_bucket(img, asset)
        except Exception as e:
            img.download_details = str(e)
            img.download_status = 'ERROR'
            logger.error(str(e))
            return False

    img.save()
    readme = asset.get_readme()
    asset.set_readme(readme['decoded'].replace(link, img.bucket_url))
    asset.save()
    return img.download_status


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
