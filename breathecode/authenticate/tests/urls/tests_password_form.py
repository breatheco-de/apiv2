# """
# Test cases for /user
# """
# from django.urls.base import reverse_lazy
# from rest_framework import status
# from .mixin import AuthTestCase

# class AuthenticateTestSuite(AuthTestCase):
#     """Authentication test suite"""
#     def test_change_password_without_token(self):
#         """logout test without token"""
#         password = 'Pain!$%'
#         url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
#         data = {'password1': password, 'password2': password}
#         # return client.post(url, data)
#         response = self.client.post(url, data)

#         self.assertContains(response, 'Invalid or expired token')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#     def test_change_password_but_has_less_of_7_characters(self):
#         """logout test without token"""
#         password = 'Pain!$%'
#         url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
#         data = {'password1': password, 'password2': 'password'}
#         response = self.client.post(url, data)

#         self.assertContains(response, 'Ensure this value has at least 8 characters (it has 7)')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#     def test_change_password_but_passwords_dont_match(self):
#         """logout test without token"""
#         password = 'Pain!$%Rinnegan'
#         url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
#         data = {'password1': password, 'password2': 'PainWithoutRinnegan'}
#         response = self.client.post(url, data)

#         # &#x27; is '
#         self.assertContains(response, 'Passwords don&#x27;t match')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#     def test_change_password_form(self):
#         """logout test without token"""
#         url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'companyid'})
#         response = self.client.get(url)

#         self.assertContains(response, '<label for="id_password1">Password1:</label>')
#         self.assertContains(response, '<label for="id_password2">Password2:</label>')
#         self.assertContains(response, '<input type="password" name="password1"')
#         self.assertContains(response, '<input type="password" name="password2"')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)

#     def test_change_password(self):
#         """logout test without token"""
#         self.login()
#         url_token = reverse_lazy('authenticate:token')
#         data_token = { 'email': self.email, 'password': self.password }
#         response_token = self.client.post(url_token, data_token)
#         token = response_token.data['token']

#         password = 'Pain!$%Rinnegan'
#         url = reverse_lazy('authenticate:pick_password', kwargs={'token': 'compagithubnyid'})
#         data = {'token': token, 'password1': password, 'password2': password}
#         response = self.client.post(url, data)

#         self.assertContains(response, 'You password has been reset successfully,
#             you can close this window.')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
