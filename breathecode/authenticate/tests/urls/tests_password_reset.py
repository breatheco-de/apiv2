"""
Test cases for /user
"""
import os
from breathecode.authenticate.models import Token
from unittest.mock import call, patch
from django.urls.base import reverse_lazy
from rest_framework import status
from ..mixins.new_auth_test_case import AuthTestCase


class AuthenticateTestSuite(AuthTestCase):
    """Authentication test suite"""
    @patch('breathecode.notify.actions.send_email_message')
    def test_password_reset__post__without_data(self, mock):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('authenticate:password_reset')
        model = self.generate_models()
        data = {}
        response = self.client.post(url, data)
        content = response.content.decode('utf-8')

        self.assertNotEqual(content.find('<title>Document</title>'), -1)
        self.assertNotEqual(content.find('Email is required'), -1)
        self.assertNotEqual(
            content.find(
                '<label for="id_password1">Password1:</label></th><td><ul class="errorlist"><li>This field is required.</li>'
            ), -1)
        self.assertNotEqual(
            content.find(
                '<label for="id_password2">Password2:</label></th><td><ul class="errorlist"><li>This field is required.</li>'
            ), -1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_user_dict(), [])
        self.assertEqual(mock.call_args_list, [])

    @patch('breathecode.notify.actions.send_email_message')
    def test_password_reset__post__with_bad_passwords(self, mock):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('authenticate:password_reset')
        model = self.generate_models()
        data = {
            'password1': 'pass1',
            'password2': 'pass2',
        }
        response = self.client.post(url, data)
        content = response.content.decode('utf-8')

        self.assertNotEqual(content.find('<title>Document</title>'), -1)
        self.assertNotEqual(
            content.find(
                '<label for="id_password1">Password1:</label></th><td><ul class="errorlist"><li>Ensure this value has at least 8 characters (it has 5).</li></ul>'
            ), -1)
        self.assertNotEqual(
            content.find(
                '<label for="id_password2">Password2:</label></th><td><ul class="errorlist"><li>Ensure this value has at least 8 characters (it has 5).</li></ul>'
            ), -1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_user_dict(), [])
        self.assertEqual(mock.call_args_list, [])

    @patch('breathecode.notify.actions.send_email_message')
    def test_password_reset__post__passwords_dont_match(self, mock):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('authenticate:password_reset')
        model = self.generate_models()
        data = {
            'password1': 'pass12341',
            'password2': 'pass12342',
        }
        response = self.client.post(url, data)
        content = response.content.decode('utf-8')

        self.assertNotEqual(content.find('<title>Document</title>'), -1)
        self.assertNotEqual(content.find('Email is required'), -1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_user_dict(), [])
        self.assertEqual(mock.call_args_list, [])

    @patch('breathecode.notify.actions.send_email_message')
    def test_password_reset__post__passwords_dont_match___(self, mock):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('authenticate:password_reset')
        model = self.generate_models()
        data = {
            'password1': 'pass1234',
            'password2': 'pass1234',
        }
        response = self.client.post(url, data)
        content = response.content.decode('utf-8')

        self.assertNotEqual(content.find('<title>Document</title>'), -1)
        self.assertNotEqual(content.find('Email is required'), -1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_user_dict(), [])
        self.assertEqual(mock.call_args_list, [])

    @patch('breathecode.notify.actions.send_email_message')
    def test_password_reset__post__with_email(self, mock):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('authenticate:password_reset')
        model = self.generate_models()
        data = {
            'email': 'konan@naturo.io',
        }
        response = self.client.post(url, data)
        content = response.content.decode('utf-8')

        self.assertNotEqual(
            content.find('Check your email for a password reset!'), -1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_user_dict(), [])
        self.assertEqual(mock.call_args_list, [])

    @patch('breathecode.notify.actions.send_email_message')
    def test_password_reset__post__with_email__with_user(self, mock):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('authenticate:password_reset')
        model = self.generate_models(user=True)
        data = {'email': model['user'].email}
        response = self.client.post(url, data)
        content = response.content.decode('utf-8')
        token = Token.objects.filter(id=1).values_list('key',
                                                       flat=True).first()

        self.assertNotEqual(
            content.find('Check your email for a password reset!'), -1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_user_dict(), [{
            **self.model_to_dict(model, 'user')
        }])

        self.assertEqual(mock.call_args_list, [
            call(
                'pick_password', model['user'].email, {
                    "SUBJECT":
                    "You asked to reset your password at BreatheCode",
                    "LINK":
                    os.getenv('API_URL', '') + f"/v1/auth/password/{token}"
                })
        ])

    @patch('breathecode.notify.actions.send_email_message')
    def test_password_reset__post__with_email_in_uppercase__with_user(
            self, mock):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('authenticate:password_reset')
        model = self.generate_models(user=True)
        data = {
            'email': model['user'].email.upper(),
        }
        response = self.client.post(url, data)
        content = response.content.decode('utf-8')
        token = Token.objects.filter(id=1).values_list('key',
                                                       flat=True).first()

        self.assertNotEqual(
            content.find('Check your email for a password reset!'), -1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.all_user_dict(), [{
            **self.model_to_dict(model, 'user')
        }])

        self.assertEqual(mock.call_args_list, [
            call(
                'pick_password', model['user'].email, {
                    "SUBJECT":
                    "You asked to reset your password at BreatheCode",
                    "LINK":
                    os.getenv('API_URL', '') + f"/v1/auth/password/{token}"
                })
        ])

    @patch('breathecode.notify.actions.send_email_message')
    def test_password_reset__post__with_callback__with_email(self, mock):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('authenticate:password_reset')
        model = self.generate_models()
        data = {
            'email': 'konan@naturo.io',
            'callback': 'https://naturo.io/',
        }
        response = self.client.post(url, data)

        self.assertEqual(
            response.url,
            'https://naturo.io/?msg=Check%20your%20email%20for%20a%20password%20reset!'
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.all_user_dict(), [])
        self.assertEqual(mock.call_args_list, [])

    @patch('breathecode.notify.actions.send_email_message')
    def test_password_reset__post__with_callback__with_email__with_user(
            self, mock):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('authenticate:password_reset')
        model = self.generate_models(user=True)
        data = {
            'email': model['user'].email,
            'callback': 'https://naturo.io/',
        }
        response = self.client.post(url, data)
        token = Token.objects.filter(id=1).values_list('key',
                                                       flat=True).first()

        self.assertEqual(
            response.url,
            'https://naturo.io/?msg=Check%20your%20email%20for%20a%20password%20reset!'
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.all_user_dict(), [{
            **self.model_to_dict(model, 'user')
        }])

        self.assertEqual(mock.call_args_list, [
            call(
                'pick_password', model['user'].email, {
                    "SUBJECT":
                    "You asked to reset your password at BreatheCode",
                    "LINK":
                    os.getenv('API_URL', '') + f"/v1/auth/password/{token}"
                })
        ])

    @patch('breathecode.notify.actions.send_email_message')
    def test_password_reset__post__with_callback__with_email_in_uppercase__with_user(
            self, mock):
        """Test /cohort/:id without auth"""
        self.headers(academy=1)
        url = reverse_lazy('authenticate:password_reset')
        model = self.generate_models(user=True)
        data = {
            'email': model['user'].email.upper(),
            'callback': 'https://naturo.io/',
        }
        response = self.client.post(url, data)
        token = Token.objects.filter(id=1).values_list('key',
                                                       flat=True).first()

        self.assertEqual(
            response.url,
            'https://naturo.io/?msg=Check%20your%20email%20for%20a%20password%20reset!'
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(self.all_user_dict(), [{
            **self.model_to_dict(model, 'user')
        }])

        self.assertEqual(mock.call_args_list, [
            call(
                'pick_password', model['user'].email, {
                    "SUBJECT":
                    "You asked to reset your password at BreatheCode",
                    "LINK":
                    os.getenv('API_URL', '') + f"/v1/auth/password/{token}"
                })
        ])
