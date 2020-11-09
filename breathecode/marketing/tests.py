from django.test import TestCase
from django.apps import apps
from django.urls.base import reverse_lazy
from mixer.backend.django import mixer
# Create your tests here.

#@override_settings(STATICFILES_STORAGE=None)
class MarketingTestSuite(TestCase):
    """
    Endpoint tests for Invites
    """
    def setUp(self):
        pass
        # user = mixer.blend('auth.User')
        # user.set_password('pass1234')
        # user.save()

        # params = { "user": user }
        # github = mixer.blend('authenticate.CredentialsGithub', **params)
        # github.save()

    # def test_get_users(self):
    #     url = reverse_lazy('authenticate:user')
    #     response = self.client.get(url)
    #     users = response.json()
        
    #     # total_users = User.objects.all().count()
    #     self.assertEqual(1,len(users),"The total users should match the database")


    # def test_geolocal(self):
    #     results = get_geolocal("25.760158", "-80.200154")
    #     self.assertEqual('Miami',results['country'], "Geolocalization test failed")
        