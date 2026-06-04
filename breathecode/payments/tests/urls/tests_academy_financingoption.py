"""
Tests for /v1/payments/academy/financingoption endpoints
"""

from breathecode.payments.tests.mixins import PaymentsTestCase


class AcademyFinancingOptionTestSuite(PaymentsTestCase):
    """Test suite for FinancingOption CRUD operations"""

    def test_get_financing_options__no_auth(self):
        """Test GET without authentication returns 401"""
        url = "/v1/payments/academy/financingoption"
        response = self.client.get(url, headers={"academy": 1})
        
        self.assertEqual(response.status_code, 401)

    def test_get_financing_options__no_capability(self):
        """Test GET without read_subscription capability returns 403"""
        model = self.bc.database.create(user=1, role=1, academy=1, profile_academy=1)
        
        self.client.force_authenticate(model.user)
        url = "/v1/payments/academy/financingoption"
        response = self.client.get(url, headers={"academy": 1})
        
        self.assertEqual(response.status_code, 403)

    def test_get_financing_options__empty(self):
        """Test GET with no financing options returns empty list"""
        model = self.bc.database.create(user=1, role=1, capability="read_subscription", profile_academy=1)
        
        self.client.force_authenticate(model.user)
        url = "/v1/payments/academy/financingoption"
        response = self.client.get(url, headers={"academy": 1})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_financing_options__list_academy_owned(self):
        """Test GET returns financing options owned by academy"""
        model = self.bc.database.create(
            user=1, role=1, capability="read_subscription", profile_academy=1, financing_option=2, currency=1
        )
        
        # Set one as academy-owned, one as global
        model.financing_option[0].academy = model.academy
        model.financing_option[0].save()
        
        self.client.force_authenticate(model.user)
        url = "/v1/payments/academy/financingoption"
        response = self.client.get(url, headers={"academy": 1})
        
        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 2)
        self.assertIn(json[0]["id"], [model.financing_option[0].id, model.financing_option[1].id])

    def test_get_financing_option__by_id(self):
        """Test GET specific financing option by ID"""
        model = self.bc.database.create(
            user=1, role=1, capability="read_subscription", profile_academy=1, financing_option=1, currency=1
        )
        
        self.client.force_authenticate(model.user)
        url = f"/v1/payments/academy/financingoption/{model.financing_option.id}"
        response = self.client.get(url, headers={"academy": 1})
        
        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json["id"], model.financing_option.id)
        self.assertEqual(json["monthly_price"], model.financing_option.monthly_price)
        self.assertEqual(json["how_many_months"], model.financing_option.how_many_months)

    def test_post_financing_option__no_capability(self):
        """Test POST without crud_subscription capability returns 403"""
        model = self.bc.database.create(user=1, role=1, capability="read_subscription", profile_academy=1)
        
        self.client.force_authenticate(model.user)
        url = "/v1/payments/academy/financingoption"
        data = {"monthly_price": 299.00, "how_many_months": 12, "currency": "USD"}
        response = self.client.post(url, data, format="json", headers={"academy": 1})
        
        self.assertEqual(response.status_code, 403)

    def test_post_financing_option__success(self):
        """Test POST creates financing option for academy"""
        model = self.bc.database.create(user=1, role=1, capability="crud_subscription", profile_academy=1, currency=1)
        
        self.client.force_authenticate(model.user)
        url = "/v1/payments/academy/financingoption"
        data = {
            "monthly_price": 299.00,
            "how_many_months": 12,
            "currency": model.currency.code,
        }
        response = self.client.post(url, data, format="json", headers={"academy": 1})
        
        json = response.json()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(json["monthly_price"], 299.00)
        self.assertEqual(json["how_many_months"], 12)
        self.assertEqual(json["currency"]["code"], model.currency.code)
        self.assertEqual(json["academy"]["id"], model.academy.id)

    def test_post_financing_option__no_currency(self):
        """Test POST without currency returns 400"""
        model = self.bc.database.create(user=1, role=1, capability="crud_subscription", profile_academy=1)
        
        self.client.force_authenticate(model.user)
        url = "/v1/payments/academy/financingoption"
        data = {"monthly_price": 299.00, "how_many_months": 12}
        response = self.client.post(url, data, format="json", headers={"academy": 1})
        
        json = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("currency", json["detail"].lower())

    def test_post_financing_option__invalid_currency(self):
        """Test POST with invalid currency returns 400"""
        model = self.bc.database.create(user=1, role=1, capability="crud_subscription", profile_academy=1)
        
        self.client.force_authenticate(model.user)
        url = "/v1/payments/academy/financingoption"
        data = {"monthly_price": 299.00, "how_many_months": 12, "currency": "INVALID"}
        response = self.client.post(url, data, format="json", headers={"academy": 1})
        
        json = response.json()
        self.assertEqual(response.status_code, 400)
        self.assertIn("currency", json["detail"].lower())

    def test_put_financing_option__success(self):
        """Test PUT updates financing option"""
        model = self.bc.database.create(
            user=1, role=1, capability="crud_subscription", profile_academy=1, financing_option=1, currency=1
        )
        
        # Set as academy-owned
        model.financing_option.academy = model.academy
        model.financing_option.save()
        
        self.client.force_authenticate(model.user)
        url = f"/v1/payments/academy/financingoption/{model.financing_option.id}"
        data = {"monthly_price": 399.00}
        response = self.client.put(url, data, format="json", headers={"academy": 1})
        
        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json["monthly_price"], 399.00)

    def test_put_financing_option__not_owned_by_academy(self):
        """Test PUT on financing option owned by different academy returns 404"""
        academy2 = self.bc.database.create(academy=1, skip_objects=["financing_option"]).academy
        model = self.bc.database.create(
            user=1, role=1, capability="crud_subscription", profile_academy=1, financing_option=1, currency=1
        )
        
        # Set as owned by different academy
        model.financing_option.academy = academy2
        model.financing_option.save()
        
        self.client.force_authenticate(model.user)
        url = f"/v1/payments/academy/financingoption/{model.financing_option.id}"
        data = {"monthly_price": 399.00}
        response = self.client.put(url, data, format="json", headers={"academy": model.academy.id})
        
        self.assertEqual(response.status_code, 404)

    def test_delete_financing_option__success(self):
        """Test DELETE removes financing option"""
        model = self.bc.database.create(
            user=1, role=1, capability="crud_subscription", profile_academy=1, financing_option=1, currency=1
        )
        
        # Set as academy-owned
        model.financing_option.academy = model.academy
        model.financing_option.save()
        
        self.client.force_authenticate(model.user)
        url = f"/v1/payments/academy/financingoption/{model.financing_option.id}"
        response = self.client.delete(url, headers={"academy": 1})
        
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.bc.database.list_of("payments.FinancingOption"), [])

    def test_delete_financing_option__in_use_by_plan(self):
        """Test DELETE on financing option used by plan returns 400"""
        model = self.bc.database.create(
            user=1, role=1, capability="crud_subscription", profile_academy=1, financing_option=1, currency=1
        )
        
        # Create plan manually to avoid validation issues
        from breathecode.payments.models import Plan

        plan = Plan(
            slug="test-plan",
            currency=model.currency,
            is_renewable=False,
            trial_duration=0,
            owner=model.academy,
        )
        plan.save()
        
        # Set as academy-owned and link to plan
        model.financing_option.academy = model.academy
        model.financing_option.save()
        plan.financing_options.add(model.financing_option)
        
        self.client.force_authenticate(model.user)
        url = f"/v1/payments/academy/financingoption/{model.financing_option.id}"
        response = self.client.delete(url, headers={"academy": 1})
        
        json = response.json()
        self.assertEqual(response.status_code, 400)
        # Check for error in detail field (slug format)
        self.assertTrue("slug" in json or "detail" in json)

    def test_delete_financing_option__global_option(self):
        """Test DELETE on global financing option (academy=None) returns 404"""
        model = self.bc.database.create(
            user=1, role=1, capability="crud_subscription", profile_academy=1, financing_option=1, currency=1
        )
        
        # Keep as global (academy=None is default)
        
        self.client.force_authenticate(model.user)
        url = f"/v1/payments/academy/financingoption/{model.financing_option.id}"
        response = self.client.delete(url, headers={"academy": 1})
        
        self.assertEqual(response.status_code, 404)

    def test_filter_by_currency(self):
        """Test filtering financing options by currency"""
        model = self.bc.database.create(
            user=1, role=1, capability="read_subscription", profile_academy=1, financing_option=2, currency=2
        )
        
        # Set different currencies
        model.currency[0].code = "USD"
        model.currency[0].save()
        model.currency[1].code = "EUR"
        model.currency[1].save()
        
        model.financing_option[0].academy = model.academy
        model.financing_option[0].currency = model.currency[0]
        model.financing_option[0].save()
        
        model.financing_option[1].academy = model.academy
        model.financing_option[1].currency = model.currency[1]
        model.financing_option[1].save()
        
        self.client.force_authenticate(model.user)
        url = "/v1/payments/academy/financingoption?currency=USD"
        response = self.client.get(url, headers={"academy": 1})
        
        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0]["currency"]["code"], "USD")

    def test_filter_by_months(self):
        """Test filtering financing options by number of months"""
        model = self.bc.database.create(
            user=1, role=1, capability="read_subscription", profile_academy=1, financing_option=2, currency=1
        )
        
        model.financing_option[0].academy = model.academy
        model.financing_option[0].how_many_months = 6
        model.financing_option[0].save()
        
        model.financing_option[1].academy = model.academy
        model.financing_option[1].how_many_months = 12
        model.financing_option[1].save()
        
        self.client.force_authenticate(model.user)
        url = "/v1/payments/academy/financingoption?how_many_months=12"
        response = self.client.get(url, headers={"academy": 1})
        
        json = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0]["how_many_months"], 12)
