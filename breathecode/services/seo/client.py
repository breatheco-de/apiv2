import os, ast, requests, json, logging
import breathecode.services.seo.actions as actions
from breathecode.registry.models import SEOReport
from breathecode.utils import APIException
from django.utils import timezone
from slugify import slugify

logger = logging.getLogger(__name__)


class SEOAnalyzer:
    asset = None
    excluded = []
    influence = {'keyword_density': 1}

    def __init__(self, asset, exclude=[]):
        if asset is None:
            raise Exception('Invalid Asset')

        self.asset = asset
        self.excluded = [*exclude, '__init__']

        total_influence = 0
        for slug in self.influence:
            total_influence += self.influence[slug]
        if total_influence != 1:
            raise Exception(
                f'Total influence from all SEO reports should sum 1 but its {str(total_influence)}')

    def _get_actions(self):
        actions = []
        dir_path = os.path.dirname(os.path.realpath(__file__))
        files = os.listdir(dir_path + '/actions')
        for file_name in files:
            if '.py' not in file_name:
                continue
            actions.append(file_name[0:-3])
        return actions

    def start(self):
        rating = 0
        log = []
        actions = self._get_actions()
        for act in actions:
            if act in self.excluded:
                continue
            else:
                report = self.execute_report(act)
                rating += report.get_rating() * self.influence[report.report_type]
                log += report.get_log()

        self.asset.last_seo_scan_at = timezone.now()
        self.asset.optimization_rating = rating
        self.asset.seo_json_status = {'rating': rating, 'log': log}
        self.asset.save()
        return self.asset.seo_json_status

    def execute_report(self, script_slug):

        logger.debug(f'Executing SEP Report => {script_slug}')
        report = SEOReport(
            report_type=script_slug,
            asset=self.asset,
            rating=0,
        )
        if hasattr(actions, script_slug):

            fn = getattr(actions, script_slug)

            try:
                fn(self, report)
                report.rating = report.get_rating()
                report.log = report.get_log()
                report.status = 'OK'
                report.save()

            except Exception as e:
                logger.exception('Error report error')
                report.rating = None
                report.log = str(e)
                report.status = 'ERROR'
                report.save()

        else:
            message = f'SEO Report `{script_slug}` is not implemented'
            logger.debug(message)
            report.rating = None
            report.status = 'ERROR'
            report.log = message
            report.save()

        return report
