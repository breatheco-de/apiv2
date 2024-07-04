"""
Test /answer
"""

import pytest
from random import randint
from unittest.mock import MagicMock, call, patch

from ...models import ProvisioningVendor
from ...actions import get_provisioning_vendor
from ..mixins import ProvisioningTestCase


def apply_get_env(configuration={}):

    def get_env(key, value=None):
        return configuration.get(key, value)

    return get_env


class ProvisioningTestSuite(ProvisioningTestCase):
    """
    🔽🔽🔽 Clean readme content in several ways
    """

    def test__get_provisioning_vendor(self):

        model = self.bc.database.create(
            cohort=1,
            profile_academy=1,
        )
        model2 = self.bc.database.create(profile_academy=1)
        model3 = self.bc.database.create(
            academy=model.profile_academy.academy,
            provisioning_vendor={
                "name": "gitpod",
            },
            provisioning_profile={"cohorts": [model.cohort.id]},
        )

        vendor = get_provisioning_vendor(model.user.id, model.profile_academy, model.cohort)
        self.assertEqual(vendor.id, model3.provisioning_vendor.id)

        with pytest.raises(Exception):
            vendor = get_provisioning_vendor(model.user.id, model2.profile_academy, model.cohort)

    def test__get_provisioning_vendor_two_vendors_same_member(self):
        """
        Add to ProvisioningProfiles on purpose for the same member
        it should give an exception
        """
        model = self.bc.database.create(
            cohort=1,
            profile_academy=1,
        )
        vendor1 = self.bc.database.create(
            provisioning_vendor={
                "name": "gitpod",
            },
        )
        vendor2 = self.bc.database.create(
            provisioning_vendor={
                "name": "github",
            },
        )

        profile1 = self.bc.database.create(
            provisioning_vendor=vendor1,
            academy=model.profile_academy.academy,
            provisioning_profile={"members": [model.profile_academy.id]},
        )

        profile2 = self.bc.database.create(
            provisioning_vendor=vendor2,
            academy=model.profile_academy.academy,
            provisioning_profile={"members": [model.profile_academy.id]},
        )

        with pytest.raises(Exception):
            vendor = get_provisioning_vendor(model.user.id, model.profile_academy, model.cohort)

    def test__get_provisioning_vendor_two_vendors_same_cohort(self):
        """
        Add to ProvisioningProfiles on purpose for the same cohort
        it should give an exception
        """
        model = self.bc.database.create(
            cohort=1,
            profile_academy=1,
        )
        vendor1 = self.bc.database.create(
            provisioning_vendor={
                "name": "gitpod",
            },
        )
        vendor2 = self.bc.database.create(
            provisioning_vendor={
                "name": "github",
            },
        )

        profile1 = self.bc.database.create(
            provisioning_vendor=vendor1,
            academy=model.profile_academy.academy,
            provisioning_profile={"cohorts": [model.cohort.id]},
        )

        profile2 = self.bc.database.create(
            provisioning_vendor=vendor2,
            academy=model.profile_academy.academy,
            provisioning_profile={"cohorts": [model.cohort.id]},
        )

        with pytest.raises(Exception):
            vendor = get_provisioning_vendor(model.user.id, model.profile_academy, model.cohort)

    def test__get_provisioning_vendor_member_has_priority(self):
        """
        Let's add 3 profiles that could be mathcing the same user
        but the "members" filter should have priority
        """
        model = self.bc.database.create(cohort=1, profile_academy=1, provisioning_vendor=False)
        vendor1 = self.bc.database.create(
            provisioning_vendor=1,
            provisioning_vendor_kwargs={
                "name": "gitpod",
            },
        )
        vendor2 = self.bc.database.create(
            provisioning_vendor=1,
            provisioning_vendor_kwargs={
                "name": "github",
            },
        )

        profile1 = self.bc.database.create(
            academy=model.profile_academy.academy,
            provisioning_profile=1,
            provisioning_profile_kwargs={
                "vendor": vendor1.provisioning_vendor,
                "members": None,
                "cohorts": None,
                "academy": model.profile_academy.academy,
            },
        )

        profile2 = self.bc.database.create(
            academy=model.profile_academy.academy,
            provisioning_profile=1,
            provisioning_profile_kwargs={"vendor": vendor2.provisioning_vendor, "members": [model.profile_academy.id]},
        )

        profile3 = self.bc.database.create(
            academy=model.profile_academy.academy,
            provisioning_profile=1,
            provisioning_profile_kwargs={"vendor": vendor1.provisioning_vendor, "cohorts": [model.cohort.id]},
        )

        vendor = get_provisioning_vendor(model.user.id, model.profile_academy, model.cohort)
        self.assertEqual(vendor.name, vendor2.provisioning_vendor.name)

    def test__get_provisioning_vendor_cohort_has_second_priority(self):
        """
        Let's add 2 profiles that could be mathcing the same user
        but the "cohort" filter should have priority because there are no members
        """
        model = self.bc.database.create(cohort=1, profile_academy=1, provisioning_vendor=False)
        vendor1 = self.bc.database.create(
            provisioning_vendor=1,
            provisioning_vendor_kwargs={
                "name": "gitpod",
            },
        )
        vendor2 = self.bc.database.create(
            provisioning_vendor=1,
            provisioning_vendor_kwargs={
                "name": "github",
            },
        )

        profile1 = self.bc.database.create(
            academy=model.profile_academy.academy,
            provisioning_profile=1,
            provisioning_profile_kwargs={
                "vendor": vendor1.provisioning_vendor,
                "members": None,
                "cohorts": None,
                "academy": model.profile_academy.academy,
            },
        )

        profile2 = self.bc.database.create(
            academy=model.profile_academy.academy,
            provisioning_profile=1,
            provisioning_profile_kwargs={"vendor": vendor2.provisioning_vendor, "cohorts": [model.cohort.id]},
        )

        vendor = get_provisioning_vendor(model.user.id, model.profile_academy, model.cohort)
        self.assertEqual(vendor.name, vendor2.provisioning_vendor.name)
