import os, logging, re
import breathecode.services.seo.actions as actions
from breathecode.registry.models import SEOReport
from django.utils import timezone

logger = logging.getLogger(__name__)


class SEOAnalyzer:
    asset = None
    excluded = []
    shared_state = {}
    influence = {"general_structure": 0.2, "keyword_density": 0.375, "internal_linking": 0.375, "images_use": 0.05}

    def __init__(self, asset, exclude=None):

        if exclude is None:
            exclude = []

        if asset is None:
            raise Exception("Invalid Asset")

        self.asset = asset
        self.excluded = [*exclude, "__init__"]

        total_influence = 0
        for slug in self.influence:
            total_influence += self.influence[slug]
        if total_influence != 1:
            raise Exception(f"Total influence from all SEO reports should sum 1 but its {str(total_influence)}")

    def _get_actions(self):
        actions = []
        dir_path = os.path.dirname(os.path.realpath(__file__))
        files = os.listdir(dir_path + "/actions")
        for file_name in files:
            if ".py" not in file_name:
                continue
            actions.append(file_name[0:-3])
        return sorted(actions, key=str.lower)

    def start(self):
        rating = 0
        log = []
        actions = self._get_actions()

        self.asset.last_seo_scan_at = timezone.now()
        self.asset.save()

        # Start reports fro scratch
        SEOReport.objects.filter(asset__slug=self.asset.slug).delete()

        for act in actions:
            if act in self.excluded:
                continue
            else:
                report = self.execute_report(act)

                if report.report_type not in self.influence:
                    logger.error(f"Influence for report {report.report_type} its not specified")
                    self.influence[report.report_type] = 0

                rating += report.get_rating() * self.influence[report.report_type]
                log += report.get_log()

        self.asset.last_seo_scan_at = timezone.now()
        self.asset.optimization_rating = rating
        self.asset.seo_json_status = {"rating": rating, "log": log}
        self.asset.save()
        return self.asset.seo_json_status

    def execute_report(self, script_slug):

        action_name = re.sub(r"_[0-9]+_", "", script_slug)

        logger.debug(f"Executing SEP Report => {script_slug}")
        report = SEOReport(
            report_type=action_name,
            asset=self.asset,
            rating=0,
        )
        report.__shared_state = self.shared_state

        if hasattr(actions, action_name):

            fn = getattr(actions, action_name)

            try:

                if self.asset.seo_keywords is None or self.asset.seo_keywords.count() == 0:
                    raise Exception("Asset has not keywords associated")

                if self.asset.readme is None:
                    raise Exception("Asset has not content")

                fn(self, report)
                report.rating = report.get_rating()

                try:
                    report.how_to_fix = fn.description.strip()
                except AttributeError:
                    pass

                report.log = report.get_log()
                report.status = "OK"
                report.save()

                self.shared_state = report.__shared_state

            except Exception as e:
                logger.exception("Report error")
                report.rating = None
                report.log = str(e)
                report.status = "ERROR"
                report.save()

        else:
            message = f"SEO Report `{action_name}` is not implemented"
            logger.debug(message)
            report.rating = None
            report.status = "ERROR"
            report.log = message
            report.save()

        return report
