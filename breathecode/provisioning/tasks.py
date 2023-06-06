from io import StringIO
import json
import logging
import os

from celery import Task, shared_task
import pandas as pd
from breathecode.admissions.models import CohortUser
from breathecode.authenticate.models import CredentialsGithub, PendingGithubUser

from breathecode.provisioning import actions
from breathecode.provisioning.models import ProvisioningActivity, ProvisioningBill
from breathecode.services.google_cloud.storage import Storage
from breathecode.utils.validation_exception import ValidationException
from django.utils import timezone

logger = logging.getLogger(__name__)


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

        bill.total_amount = amount
        bill.status = 'DUE' if amount else 'PAID'
        bill.save()


PANDAS_ROWS_LIMIT = 100


@shared_task(bind=False, base=BaseTaskWithRetry)
def link_pending_github_users_to_bills(hash):
    logger.info(f'Starting link_pending_github_users_to_bills for hash {hash}')
    bills = ProvisioningBill.objects.filter(hash=hash).exclude(status__in=['DISPUTED', 'IGNORED', 'PAID'])

    if not bills.exists():
        logger.warning(f'Does not exists bills for hash {hash}')
        return

    pending_github_users = PendingGithubUser.objects.filter(hashes__icontains=hash, status='PENDING')
    if not pending_github_users.exists():
        logger.warning(f'Does not exists pending github users for hash {hash}')
        return

    no_academies = pending_github_users.filter(academy__isnull=True)
    with_academies = pending_github_users.filter(academy__isnull=False)

    for bill in bills:
        belongs_to_bill = with_academies.filter(academy=bill.academy)

        bill.pending_users.clear()
        bill.pending_users.add(*no_academies, *belongs_to_bill)

    logger.error('There are pending github users that cannot be linked to a academy bill')


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

    elif PendingGithubUser.objects.filter(hashes__icontains=hash).exists():
        link_pending_github_users_to_bills.delay(hash)

    else:
        calculate_bill_amounts.delay(hash)
