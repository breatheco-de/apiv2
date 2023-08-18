import copy
from types import ModuleType
from typing import TypeVar, TypedDict
from django.urls.resolvers import URLPattern

__all__ = ['Router']

T = TypeVar('T')


class Route(TypedDict):
    path: str
    # deleted: bool
    route: URLPattern


class Version(TypedDict):
    deprecated: bool
    routes: dict[str, Route]


class Router:
    """Router that support versioning."""

    _module: ModuleType
    _version: int
    _versions: dict[str, Version]

    def __init__(self, app_name, prefix=None, namespace=None):
        assert app_name, 'App name is required'

        if not namespace:
            namespace = app_name

        if not prefix:
            prefix = app_name

        # self._module = sys.modules[name]
        self._version = 1
        self._versions = {}
        self._excludes = {}
        self.prefix = prefix
        self.namespace = namespace
        self.app_name = app_name

    def set_version(self, v) -> 'Router':
        """Set the version of next routes."""

        assert isinstance(v, int), 'Version must be an integer'

        self._version = v
        return self

    def deprecate(self, *routes) -> 'Router':
        """Deprecate many routes, if routes=None, all routes are deprecated."""

        if len(routes) == 0:
            self._excludes[self._version] += self._versions[self._version]['routes'].keys()

        else:
            self._excludes[self._version] += list(routes)

        self._excludes[self._version] = list(set(self._excludes[self._version]))

        return self

    def release(self, routes: list[URLPattern], deprecated=False, drop=False) -> 'Router':
        if drop:
            self._version += 1
            return self

        r = []
        self._excludes[self._version] = []
        self._versions[self._version] = {
            'deprecated': deprecated,
        }

        for route in routes:
            r.append({
                'path': route.pattern._route,
                'deleted': False,
                'route': route,
            })

        self._versions[self._version]['routes'] = r

        self._version += 1

        return self

    def build(self) -> 'Router':

        v = self._version - len(self._versions)
        result = {}
        endpoints = {}

        for key, version in self._versions.items():
            if version['deprecated']:
                continue

            ver_repr = f'v{v}'
            # result[var_name] = {}

            for route in version['routes']:
                if route['deleted']:
                    continue

                endpoints[route['path']] = copy.deepcopy(route['route'])

                # if version != 1:
                #     endpoints[route].name = ver_repr + ':' + endpoints[route].name

            result[ver_repr] = endpoints.values()

            for exclude in self._excludes[key]:
                if exclude in endpoints:
                    del endpoints[exclude]

            v += 1

        return result
