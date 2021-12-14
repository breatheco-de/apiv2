from django.urls import path
from .views import redirect_link

app_name = 'marketing'
urlpatterns = [
    path('<str:link_slug>', redirect_link, name='slug'),
    path('p/<str:link_slug>', redirect_link, name='p_slug'),  # private shortcuts
]
