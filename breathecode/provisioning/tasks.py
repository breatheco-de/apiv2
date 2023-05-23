from io import StringIO
import logging
from datetime import datetime, timedelta
import os
import traceback
from typing import Optional
from django.utils import timezone

from celery import Task, shared_task
import pandas as pd
from breathecode.authenticate.actions import get_user_settings

from breathecode.notify import actions as notify_actions
from breathecode.provisioning import actions
from breathecode.payments.services.stripe import Stripe
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from breathecode.payments.signals import consume_service
from breathecode.services.google_cloud.storage import Storage
from breathecode.utils.decorators import task
from breathecode.utils.i18n import translation
from breathecode.utils.validation_exception import ValidationException

from .models import AbstractIOweYou, Bag, Consumable, ConsumptionSession, Invoice, PlanFinancing, PlanServiceItem, PlanServiceItemHandler, Service, ServiceStockScheduler, Subscription, SubscriptionServiceItem
from breathecode.payments.signals import reimburse_service_units

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
