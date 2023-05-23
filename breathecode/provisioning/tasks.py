from io import StringIO
import logging
import os

from celery import Task, shared_task
import pandas as pd

from breathecode.provisioning import actions
from breathecode.services.google_cloud.storage import Storage
from breathecode.utils.validation_exception import ValidationException

logger = logging.getLogger(__name__)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


def get_app_url():
    return os.getenv('APP_URL', '')


@shared_task(bind=False, base=BaseTaskWithRetry)
def upload(hash: str, page: int = 0):
    logger.info(f'Starting upload for hash {hash}')

    limit = 100
    start = page * 100
    end = start + limit
    context = {}

    storage = Storage()
    cloud_file = storage.file(os.getenv('DOWNLOADS_BUCKET', None), hash)
    if not cloud_file.exists():
        logger.error(f'File {hash} not found')
        return

    s = cloud_file.download().decode('utf-8')

    csvStringIO = StringIO(s)
    df = pd.read_csv(csvStringIO, sep=',', header=None)

    gitpod_fields = ['id', 'metadata', 'creditCents', 'effectiveTime', 'kind', 'metadata']
    come_from_gitpod = len(df.keys().intersection(gitpod_fields)) == len(gitpod_fields)

    codespaces_fields = ['Date', 'Product', 'SKU', 'Quantity', 'Unit Type', 'Price Per Unit ($)']
    come_from_codespaces = len(df.keys().intersection(codespaces_fields)) == len(codespaces_fields)

    try:
        if come_from_gitpod:
            for i in range(start, end):
                actions.add_gitpod_activity(context, df.iloc[i].to_dict())

        elif come_from_codespaces:
            for i in range(start, end):
                actions.add_codespaces_activity(context, df.iloc[i].to_dict())

        else:
            logger.error(f'File {hash} has an invalid format')
            return

    except ValidationException as e:
        logger.error(f'File {hash} cannot be processed due to: {str(e)}')
        return

    if len(df.iloc[start:end]) == 100:
        upload.delay(hash, page + 1)
