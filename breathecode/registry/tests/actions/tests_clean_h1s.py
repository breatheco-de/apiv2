"""
Test clean_h1s
"""
from logging import Logger
from unittest.mock import MagicMock, PropertyMock, call, patch
import pytest

from rest_framework.test import APIClient
from breathecode.registry.models import Asset
from breathecode.registry.actions import clean_h1s
from breathecode.tests.mixins.breathecode_mixin.breathecode import Breathecode
# from ..mixins import RegistryTestCase


@pytest.fixture(autouse=True)
def setup(db):
    from linked_services.django.actions import reset_app_cache
    reset_app_cache()
    yield


md_without_frontmatter = """
---
title: "Working with or manipulating strings with Python"
status: "published"
syntaxis: ["python"]
tags: ["python","string-concatenation"]

---

# Hello World with React boilerplate
<p>
  <a href="https://gitpod.io#https://github.com/4GeeksAcademy/react-hello.git"><img src="https://raw.githubusercontent.com/4GeeksAcademy/react-hello/master/open-in-gitpod.svg?sanitize=true" />
  </a>
</p>
"""

md_without_frontmatter_no_h1 = """
---
title: "Working with or manipulating strings with Python"
status: "published"
syntaxis: ["python"]
tags: ["python","string-concatenation"]

---

<p>
  <a href="https://gitpod.io#https://github.com/4GeeksAcademy/react-hello.git"><img src="https://raw.githubusercontent.com/4GeeksAcademy/react-hello/master/open-in-gitpod.svg?sanitize=true" />
  </a>
</p>
"""


def test__without_frontmatter(bc: Breathecode):

    model = bc.database.create(
        asset={
            'readme_url':
            'https://github.com/breatheco-de/content/blob/master/src/content/lesson/how-to-networkt-yourself-into-a-software-development-job.es.md',
            'readme_raw': Asset.encode(md_without_frontmatter),
            'readme': Asset.encode(md_without_frontmatter)
        })

    asset = clean_h1s(model['asset'])
    readme = asset.get_readme()

    assert readme['decoded'] == md_without_frontmatter_no_h1

    # assert bc.database.list_of('media.Media') == []
    # assert Logger.warning.call_args_list == [call('Asset with slug slug not found')]
    # assert Logger.error.call_args_list == [call('Asset with slug slug not found', exc_info=True)]
