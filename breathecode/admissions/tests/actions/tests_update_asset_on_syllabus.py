"""
Test mentorhips
"""

import json
from breathecode.authenticate.models import Token
from ..mixins import AdmissionsTestCase
from ...models import Syllabus
from ...actions import update_asset_on_json


class GetOrCreateSessionTestSuite(AdmissionsTestCase):

    def test_create_session_mentor_first_no_previous_nothing(self):
        """
        When the mentor gets into the room before the mentee
        if should create a room with status 'pending'
        """

        data1 = json.load(open("breathecode/admissions/tests/actions/sample_syllabus1.json", "r"))
        data2 = json.load(open("breathecode/admissions/tests/actions/sample_syllabus2.json", "r"))
        models1 = self.bc.database.create(
            syllabus=True, syllabus_version={"json": data1}, authenticate=True, capability="crud_syllabus"
        )
        models2 = self.bc.database.create(
            syllabus=True, syllabus_version={"json": data2}, authenticate=True, capability="crud_syllabus"
        )

        changes = {
            "QUIZ": {"from": "html", "to": "html-test"},
            "LESSON": {"from": "learn-in-public", "to": "learn-in-public-test"},
        }

        for asset_type in changes:
            findings = update_asset_on_json(
                from_slug=changes[asset_type]["from"],
                to_slug=changes[asset_type]["to"],
                asset_type=asset_type,
                simulate=False,
            )

            self.assertEqual(len(findings), 2)

        syllabus = Syllabus.objects.all()
        results = {}
        for s in syllabus:
            for v in s.syllabusversion_set.all():
                for d in v.json["days"]:
                    for asset_type in d:
                        if asset_type in ["quizzes", "assignments", "projects", "replits", "lessons"]:
                            if asset_type not in results:
                                results[asset_type] = {}
                            for a in d[asset_type]:
                                if a["slug"] not in results[asset_type]:
                                    results[asset_type][a["slug"]] = 0
                                results[asset_type][a["slug"]] += 1

        # test that new slugs are present in syllabus
        def test_for_existance(results, existance):
            for asset_type in existance:
                for slug in existance[asset_type]:
                    # make sure new slugs exsists on the syllabus
                    self.assertEqual(existance[asset_type][slug], results[asset_type][slug])

        test_for_existance(
            results,
            {
                "quizzes": {
                    # one html-test should now be found on each syllabus
                    "html-test": 2,
                },
                "replits": {
                    # replits should be the same, we replaced the "html" quiz, not the "html" replit
                    "html": 2,
                },
                "lessons": {
                    "learn-in-public-test": 2,
                },
            },
        )

        # test that old slugs are gone from syllabus
        def test_for_removals(results, removals):
            for asset_type in removals:
                for slug in removals[asset_type]:
                    self.assertEqual(hasattr(results[asset_type], slug), False)

        test_for_removals(
            results,
            {
                "quizzes": ["html"],
                "lessons": ["learn-in-public"],
            },
        )
