from breathecode.utils import ValidationException
from rest_framework.permissions import AllowAny
import yaml
import requests
import os
from django.urls import reverse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from yaml.loader import FullLoader

__all__ = ['get_root_schema_view']
cache = None


class Cache:
    pass


def get_root_schema_view(elements, extend={}):
    host = os.getenv('API_URL', '')
    if host.endswith('/'):
        host = host[:-1]

    @api_view()
    @permission_classes([AllowAny])
    def view(request):
        result = {
            'info': {
                'description': '',
                'title': '',
                'version': '',
                **extend
            },
            'openapi': '3.0.0',
            'paths': {},
            'components': {
                'securitySchemes': {
                    'ApiKeyAuth': {
                        'type': 'apiKey',
                        'in': 'header',
                        'name': 'Authorization',
                    },
                }
            },
        }

        if hasattr(Cache, 'openapi'):
            return Response(Cache.openapi)

        schema_urls = [reverse(f'{element}-openapi-schema') for element in elements]

        schema_dicts = []
        for element in schema_urls:
            response = requests.get(host + element)

            if response.status_code >= 300:
                raise ValidationException(f'Unhandled {element}', 500, slug='unhandled-app')
            content = response.content.decode('utf-8')

            schema_dicts.append(yaml.load(content, Loader=FullLoader))

        for element in schema_dicts:
            for key in element['paths']:
                result['paths'][key] = element['paths'][key]
                for key2 in result['paths'][key]:
                    result['paths'][key][key2]['security'] = [{'ApiKeyAuth': []}]

        setattr(Cache, 'openapi', result)

        return Response(result)

    return view
