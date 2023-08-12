from datetime import datetime
from io import BytesIO
import logging
import math
import os
from typing import Any
from dateutil.relativedelta import relativedelta

from celery import Task
import pandas as pd
from breathecode.payments.services.stripe import Stripe
from breathecode.utils.decorators import task, AbortTask

from breathecode.provisioning import actions
from breathecode.provisioning.models import ProvisioningBill, ProvisioningConsumptionEvent, ProvisioningUserConsumption
from breathecode.services.google_cloud.storage import Storage
from django.utils import timezone

from breathecode.utils.io.file import cut_csv

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


MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
    'November', 'December'
]


@task()
def calculate_bill_amounts(hash: str, *, force: bool = False, **_: Any):
    logger.info(f'Starting calculate_bill_amounts for hash {hash}')

    bills = ProvisioningBill.objects.filter(hash=hash)

    if force:
        bills = bills.exclude(status='PAID')

    else:
        bills = bills.exclude(status__in=['DISPUTED', 'IGNORED', 'PAID'])

    if not bills.exists():
        logger.error(f'Does not exists bills for hash {hash}')
        return

    if bills[0].vendor.name == 'Gitpod':
        fields = ['id', 'credits', 'startTime', 'endTime', 'kind', 'userName', 'contextURL']

    elif bills[0].vendor.name == 'Codespaces':
        fields = [
            'Username', 'Date', 'Product', 'SKU', 'Quantity', 'Unit Type', 'Price Per Unit ($)', 'Multiplier',
            'Owner'
        ]

    storage = Storage()
    cloud_file = storage.file(os.getenv('PROVISIONING_BUCKET', None), hash)
    if not cloud_file.exists():
        logger.error(f'File {hash} not found')
        return

    csvStringIO = BytesIO()
    cloud_file.download(csvStringIO)
    csvStringIO = cut_csv(csvStringIO, first=1)
    csvStringIO.seek(0)

    df1 = pd.read_csv(csvStringIO, sep=',', usecols=fields)

    csvStringIO = BytesIO()
    cloud_file.download(csvStringIO)
    csvStringIO = cut_csv(csvStringIO, last=1)
    csvStringIO.seek(0)

    df2 = pd.read_csv(csvStringIO, sep=',', usecols=fields)

    if bills[0].vendor.name == 'Gitpod':
        first = df2['startTime'][0].split('-')
        last = df1['startTime'][0].split('-')

    elif bills[0].vendor.name == 'Codespaces':
        first = df1['Date'][0].split('-')
        last = df2['Date'][0].split('-')

    first[2] = first[2].split('T')[0]
    last[2] = last[2].split('T')[0]

    month = MONTHS[int(first[1]) - 1]

    import pytz

    first = datetime(int(first[0]), int(first[1]), int(first[2]), 0, 0, 0, 0, pytz.UTC)
    last = datetime(int(last[0]), int(last[1]), int(last[2]))

    for bill in bills:
        amount = 0
        for activity in ProvisioningUserConsumption.objects.filter(bills=bill, status='PERSISTED'):
            consumption_amount = 0
            consumption_quantity = 0
            for item in activity.events.all():
                consumption_amount += item.price.get_price(item.quantity)
                consumption_quantity += item.quantity

            activity.amount = consumption_amount
            activity.quantity = consumption_quantity
            activity.save()

            amount += consumption_amount

        bill.status = 'DUE' if amount else 'PAID'

        if amount:
            credit_price = get_provisioning_credit_price()
            quantity = math.ceil(amount / credit_price)
            new_price = quantity * credit_price

            s = Stripe()
            bill.stripe_id, bill.stripe_url = s.create_payment_link(get_stripe_price_id(), quantity)
            bill.fee = new_price - amount
            bill.total_amount = new_price

        else:
            bill.total_amount = amount

        bill.started_at = first
        bill.ended_at = last
        bill.title = f'{month} {first.year}'
        bill.save()


PANDAS_ROWS_LIMIT = 100


def reverse_upload(hash: str, **_: Any):
    logger.info(f'Canceling upload for hash {hash}')

    ProvisioningConsumptionEvent.objects.filter(provisioninguserconsumption__hash=hash).delete()
    ProvisioningUserConsumption.objects.filter(hash=hash).delete()
    ProvisioningBill.objects.filter(hash=hash).delete()


@task(reverse=reverse_upload)
def upload(hash: str, *, page: int = 0, force: bool = False, task_manager_id: int = 0, **_: Any):
    logger.info(f'Starting upload for hash {hash}')

    limit = PANDAS_ROWS_LIMIT
    start = page * limit
    end = start + limit
    context = {
        'provisioning_bills': {},
        'provisioning_vendors': {},
        'github_academy_user_logs': {},
        'provisioning_activity_prices': {},
        'provisioning_activity_kinds': {},
        'currencies': {},
        'profile_academies': {},
        'hash': hash,
        'limit': timezone.now(),
        'logs': {},
    }

    storage = Storage()
    cloud_file = storage.file(os.getenv('PROVISIONING_BUCKET', None), hash)
    if not cloud_file.exists():
        logger.error(f'File {hash} not found')
        return

    bills = ProvisioningBill.objects.filter(hash=hash).exclude(status='PENDING')
    if bills.exists() and not force:
        logger.error(f'File {hash} already processed')
        return

    pending_bills = bills.exclude(status__in=['DISPUTED', 'IGNORED', 'PAID'])

    if force and pending_bills.count() != bills.count():
        logger.error('Cannot force upload because there are bills with status DISPUTED, IGNORED or PAID')
        return

    if force:
        for bill in pending_bills:
            ProvisioningUserConsumption.objects.filter(bills=bill).delete()

        pending_bills.delete()

    csvStringIO = BytesIO()
    cloud_file.download(csvStringIO)
    csvStringIO = cut_csv(csvStringIO, start=start, end=end)
    csvStringIO.seek(0)

    df = pd.read_csv(csvStringIO, sep=',')

    handler = None

    # edit it
    fields = ['id', 'credits', 'startTime', 'endTime', 'kind', 'userName', 'contextURL']
    if len(df.keys().intersection(fields)) == len(fields):
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
        i = 0
        for position in range(start, end):
            try:
                handler(context, df.iloc[i].to_dict(), position)
                i += 1

            except IndexError:
                break

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f'File {hash} cannot be processed due to: {str(e)}')
        return

    for bill in context['provisioning_bills'].values():
        if not ProvisioningUserConsumption.objects.filter(bills=bill).exists():
            bill.delete()

    if len(df) == limit:
        upload.delay(hash, page=page + 1, task_manager_id=task_manager_id)

    elif not ProvisioningUserConsumption.objects.filter(hash=hash, status='ERROR').exists():
        calculate_bill_amounts.delay(hash)


@task()
def archive_provisioning_bill(bill_id: int, **_: Any):
    logger.info(f'Starting archive_provisioning_bills for bill id {bill_id}')

    now = timezone.now()
    bill = ProvisioningBill.objects.filter(id=bill_id,
                                           status='PAID',
                                           paid_at__lte=now - relativedelta(months=1),
                                           archived_at__isnull=True).first()

    if not bill:
        raise AbortTask(f'Bill {bill_id} not found or requirements not met')

    bill.archived_at = now
    bill.save()
