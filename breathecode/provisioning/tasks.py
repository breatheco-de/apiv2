from io import StringIO
import json
import logging
import math
import os

from celery import Task, shared_task
import pandas as pd
from breathecode.payments.services.stripe import Stripe

from breathecode.provisioning import actions
from breathecode.provisioning.models import ProvisioningActivity, ProvisioningBill
from breathecode.services.google_cloud.storage import Storage
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_provisioning_credit_price():
    return float(os.getenv('PROVISIONING_CREDIT_PRICE', 10))


def get_stripe_price_id():
    return os.getenv('STRIPE_PRICE_ID', None)


class BaseTaskWithRetry(Task):
    autoretry_for = (Exception, )
    #                                           seconds
    retry_kwargs = {'max_retries': 5, 'countdown': 60 * 5}
    retry_backoff = True


@shared_task(bind=False, base=BaseTaskWithRetry)
def calculate_bill_amounts(hash: str, *, force: bool = False):
    logger.info(f'Starting calculate_bill_amounts for hash {hash}')

    bills = ProvisioningBill.objects.filter(hash=hash)

    if force:
        bills = bills.exclude(status='PAID')

    else:
        bills = bills.exclude(status__in=['DISPUTED', 'IGNORED', 'PAID'])

    if not bills.exists():
        logger.error(f'Does not exists bills for hash {hash}')
        return

    for bill in bills:
        amount = 0
        for activity in ProvisioningActivity.objects.filter(bill=bill):
            amount += activity.price_per_unit * activity.quantity

        bill.status = 'DUE' if amount else 'PAID'

        if amount:
            credit_price = get_provisioning_credit_price()
            quantity = math.ceil(amount / credit_price)

            s = Stripe()
            bill.stripe_id, bill.stripe_url = s.create_payment_link(get_stripe_price_id(), quantity)
            bill.total_amount = quantity * credit_price

        else:
            bill.total_amount = amount

        bill.save()


PANDAS_ROWS_LIMIT = 100


@shared_task(bind=False, base=BaseTaskWithRetry)
def upload(hash: str, page: int = 0, *, force: bool = False):
    logger.info(f'Starting upload for hash {hash}')

    limit = PANDAS_ROWS_LIMIT
    start = page * limit
    end = start + limit
    context = {
        'provisioning_bills': {},
        'provisioning_vendors': {},
        'github_academy_user_logs': {},
        'profile_academies': {},
        'hash': hash,
        'limit': timezone.now(),
        'logs': {},
    }

    storage = Storage()
    cloud_file = storage.file(os.getenv('DOWNLOADS_BUCKET', None), hash)
    if not cloud_file.exists():
        logger.error(f'File {hash} not found')
        return

    bills = ProvisioningBill.objects.filter(hash=hash).exclude(status='PENDING')
    if bills.exists() and not force:
        logger.error(f'File {hash} already processed')
        return

    pending_bills = bills.exclude(status__in=['DISPUTED', 'IGNORED', 'PAID'])

    if force and pending_bills.count() != bills.count():
        logger.error(f'Cannot force upload because there are bills with status DISPUTED, IGNORED or PAID')
        return

    if force:
        for bill in pending_bills:
            ProvisioningActivity.objects.filter(bill=bill).delete()

        pending_bills.delete()

    s = cloud_file.download().decode('utf-8')

    csvStringIO = StringIO(s)
    df = pd.read_csv(csvStringIO, sep=',')

    handler = None

    fields = ['id', 'creditCents', 'effectiveTime', 'kind', 'metadata']
    if (len(df.keys().intersection(fields)) == len(fields) and len(
        {x
         for x in json.loads(df.iloc[0]['metadata'])}.intersection({'userName', 'contextURL'})) == 2):
        handler = actions.add_gitpod_activity

    if not handler:
        fields = [
            'Username', 'Date', 'Product', 'SKU', 'Quantity', 'Unit Type', 'Price Per Unit ($)', 'Multiplier'
        ]

    if not handler and len(df.keys().intersection(fields)) == len(fields):
        handler = actions.add_codespaces_activity

    if not handler:
        logger.error(f'File {hash} has an unsupported origin or the provider had changed the file format')
        return

    prev_bill = ProvisioningBill.objects.filter(hash=hash).first()
    if prev_bill:
        context['limit'] = prev_bill.created_at

    try:
        for i in range(start, end):
            try:
                handler(context, df.iloc[i].to_dict())
            except IndexError:
                break

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f'File {hash} cannot be processed due to: {str(e)}')
        return

    for bill in context['provisioning_bills'].values():
        if not ProvisioningActivity.objects.filter(bill=bill).exists():
            bill.delete()

    if len(df.iloc[start:end]) == limit:
        upload.delay(hash, page + 1)

    elif not ProvisioningActivity.objects.filter(hash=hash, status='ERROR').exists():
        calculate_bill_amounts.delay(hash)
