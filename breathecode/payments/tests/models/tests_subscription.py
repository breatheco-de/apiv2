from django import forms

from ..mixins import PaymentsTestCase


class SignalTestSuite(PaymentsTestCase):
    """
    🔽🔽🔽 GET without auth
    """

    def test__without_auth(self):
        model = self.bc.database.create(subscription=1)

        with self.assertRaisesMessage(forms.ValidationError, "{'__all__': ['subscription-as-fully-paid']}"):
            model.subscription.status = "FULLY_PAID"
            model.subscription.save()
