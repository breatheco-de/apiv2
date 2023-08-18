import importlib
from typing import TypeVar
from django.urls import include, path

from breathecode.utils.urls import mount_app_openapi

__all__ = ['versioning', 'NAMESPACES']

T = TypeVar('T')

NAMESPACES = set()


def versioning(*args):
    routes = []
    schemas = []

    for module in args:
        m = importlib.import_module(module)
        router = m.router
        namespace = router.namespace
        prefix = router.prefix
        app_name = router.app_name
        for version, data in router.build().items():
            # data['routes']
            n = namespace
            if version != 'v1':
                n = version + ':' + n

            route = path(f'{version}/{prefix}/', include((data, app_name), namespace=n))
            routes.append(route)
            NAMESPACES.add(n)

            ##
            schema = mount_app_openapi(f'{version}/{prefix}/', data, n)
            schemas.append(schema)

    return routes, schemas
