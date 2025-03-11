from unittest.mock import MagicMock, patch

import pytest
from django.urls.base import reverse_lazy
from django.utils import timezone

from breathecode.tests.mixins.breathecode_mixin import Breathecode
from breathecode.utils.api_view_extensions.extensions import lookup_extension

UTC_NOW = timezone.now()

# enable this file to use the database
pytestmark = pytest.mark.usefixtures("db")


def get_serializer(asset, data={}):
    asset_translations = {}
    for translation in asset.all_translations.all():
        asset_translations[translation.lang or "null"] = translation.slug

    return {
        "id": asset.id,
        "slug": asset.slug,
        "title": asset.title,
        "asset_type": asset.asset_type,
        "enable_table_of_content": asset.enable_table_of_content,
        "interactive": asset.interactive,
        "category": {
            "id": asset.category.id,
            "slug": asset.category.slug,
            "title": asset.category.title,
        },
        "description": asset.description,
        "assets_related": (
            [
                {
                    "id": related.id,
                    "slug": related.slug,
                    "lang": related.lang,
                    "asset_type": related.asset_type,
                    "status": related.status,
                    "published_at": related.published_at,
                    "category": {
                        "id": related.category.id,
                        "slug": related.category.slug,
                        "title": related.category.title,
                    },
                    "technologies": (
                        [get_serializer_technology(tech) for tech in related.technologies.all()]
                        if related.technologies
                        else []
                    ),
                }
                for related in asset.assets_related.all()
            ]
            if asset.assets_related
            else []
        ),
        "difficulty": asset.difficulty,
        "duration": asset.duration,
        "external": asset.external,
        "gitpod": asset.gitpod,
        "graded": asset.graded,
        "intro_video_url": asset.intro_video_url,
        "lang": asset.lang,
        "preview": asset.preview,
        "published_at": asset.published_at,
        "readme_url": asset.readme_url,
        "solution_video_url": asset.solution_video_url,
        "solution_url": asset.solution_url,
        "status": asset.status,
        "url": asset.url,
        "translations": asset_translations,
        "technologies": [tech.slug for tech in asset.technologies.all()] if asset.technologies else [],
        "seo_keywords": [seo_keyword.slug for seo_keyword in asset.seo_keywords.all()] if asset.seo_keywords else [],
        "visibility": asset.visibility,
        "enable_table_of_content": asset.enable_table_of_content,
        "interactive": asset.interactive,
        "learnpack_deploy_url": asset.learnpack_deploy_url,
        **data,
    }


def get_expanded_serializer(asset, data={}):
    return {
        **get_serializer(asset),
        "config": asset.config,
        "agent": asset.agent,
        "with_solutions": asset.with_solutions,
        "with_video": asset.with_solutions,
        "updated_at": asset.updated_at,
        "template_url": asset.template_url,
        "dependencies": asset.dependencies,
        **data,
    }


def get_serializer_technology(technology, data={}):
    return {
        "slug": technology.slug,
        "title": technology.title,
        "description": technology.description,
        "icon_url": technology.icon_url,
        "is_deprecated": technology.is_deprecated,
        "visibility": technology.visibility,
        **data,
    }


def get_mid_serializer(asset, data={}):
    return {
        **get_serializer(asset),
        "agent": asset.agent,
        "with_solutions": asset.with_solutions,
        "with_video": asset.with_solutions,
        "updated_at": asset.updated_at,
        **data,
    }


readme = "LS0tCnRpdGxlOiAiV29ya2luZyB3aXRoIG9yIG1hbmlwdWxhdGluZyBzdHJpbmdzIHdpdGggUHl0aG9uIgpzdGF0dXM6ICJwdWJsaXNoZWQiCnN1YnRpdGxlOiAiU3RyaW5nIGNvbmNhdGVuYXRpb24gaXMgdGhlIFdlYiBEZXZlbG9wZXIncyBicmVhZCBhbmQgYnV0dGVyLCBvdXIgam9iIGlzIHRvIGNvbmNhdGVuYXRlIHN0cmluZ3MgdG8gY3JlYXRlIEhUTUwvQ1NTIGRvY3VtZW50cyBwcm9ncmFtbWF0aWNhbGx5IgphdXRob3JzOiBbImFsZXNhbmNoZXpyIl0KY292ZXJfbG9jYWw6ICJodHRwczovL2dpdGh1Yi5jb20vYnJlYXRoZWNvLWRlL2NvbnRlbnQvYmxvYi9tYXN0ZXIvc3JjL2NvbnRlbnQvbGVzc29uLy4uLy4uL2Fzc2V0cy9pbWFnZXMvNGNjNmZhMGItMjUzMC00MDUyLWFhN2UtOGRhYzAzNzg4YWMzLnBuZz9yYXc9dHJ1ZSIKdGV4dENvbG9yOiAid2hpdGUiCmRhdGU6ICIyMDIwLTEwLTE5VDE2OjM2OjMxKzAwOjAwIgpzeW50YXhpczogWyJweXRob24iXQp0YWdzOiBbInB5dGhvbiIsInN0cmluZy1jb25jYXRlbmF0aW9uIl0KCi0tLQoKIyMgV2hhdCBpcyBhIHN0cmluZz8KCkEgYnVuY2ggb2YgbGV0dGVycyBhbmQgY2hhcmFjdGVycyBhbGwgdG9nZXRoZXIgaW4gYSBwYXJ0aWN1bGFyIG9yZGVyLCB0aGUgb25seSB3YXkgdG8gc3RvcmUgYW55IGNoYXJhY3RlcnMgdGhhdCBhcmUgbm90IGEgbnVtYmVyLCBhcmUgYSBmdW5kYW1lbnRhbCBwYXJ0IG9mIGV2ZXJ5IG1ham9yIHByb2dyYW0uCgpTdHJpbmdzIGFyZSBhbHNvIHBhcnQgb2YgdGhlIG1vc3QgcHJpbWl0aXZlIG9yIGJhc2ljIHNldCBvZiBkYXRhLXR5cGVzOiAKCnwgVHlwZSAgICAgIHwgRXhhbXBsZSAgICAgICAgICAgfCBSZXByZXNlbnRhdGlvbiAgICAgICAgICAgICAgICB8CnwgLS0tICAgICAgIHwgLS0tICAgICAgICAgICAgICAgfCAtLS0gICAgICAgICAgICAgICAgICAgICAgICAgICB8CnwgU3RyaW5nICAgIHwgYCJIZWxsbyBXb3JsZCJgICAgfCBzdHIgICAgICAgICAgICAgICAgICAgICAgICAgICB8IGp1c3QgY2hhcmFjdGVycyBpbiBhIHNlcXVlbmNlICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgfAp8IE51bWJlciAgICB8IGAyMy4zNGAgICAgICAgICAgIHwgaW50LCBmbG9hdCwgY29tcGxleCAgICAgICAgICAgfCBqdXN0IG51bWJlcnMgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgIHwKfCBTZXF1ZW5jZSAgfCBgWzIsMywxLDU2LDQuMzRdYCB8IGxpc3QsIHR1cGxlLCByYW5nZSAgICAgICAgICAgIHwgSXRlcmFibGUgbGlzdCBvZiB2YWx1ZXMgd2l0aCBudW1lcmljYWwgaW5kZXhlcyBmb3IgcG9zaXRpb25zICB8CnwgU2V0ICAgICAgIHwgYHsnMSwnMicsJzQ1J31gICAgfCBzZXQsIGZyb3plbnNldCAgICAgICAgICAgICAgICB8IExpa2UgU2VxdWVuY2UgYnV0IHVub3JkZXJlZCBhbmQgd2l0aCBkdXBsaWNhdGUgZWxlbWVudHMgICAgICAgfAp8IE1hcHBpbmcgICB8IGB7Im5hbWUiOiAiQm9iIn1gIHwgZGljdCAgICAgICAgICAgICAgICAgICAgICAgICAgfCBMaWtlIFNlcXVlbmNlIGJ1dCBpbmRleGVzIGFyZSBjaGFyYWN0ZXJzIGludGVhZCBvZiBpbmNyZW1lbnRhbCBudW1iZXJzIHwKfCBCb29sZWFuICAgfCBgVHJ1ZWAgb3IgYEZhbHNlYCB8IGJvb2wgICAgICAgICAgICAgICAgICAgICAgICAgIHwganVzdCBUcnVlIG9yIEZhbHNlIHwKfCBCaW5hcnkgICAgfCBgMDEwMDEwMTAxMTFgICAgICB8IGJ5dGVzLCBieXRlYXJyYXksIG1lbW9yeXZpZXcgIHwgSWRlYWwgZm9yIGxvdyBsZXZlbCBvcGVyYXRpb25zICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICB8CgojIyBIb3cgdG8gY3JlYXRlIGEgc3RyaW5nCgpUbyBjcmVhdGUgYSBzdHJpbmcgaW4gcHl0aG9uIGp1c3QgcHV0IGEgYnVuY2ggb2YgY2hhcmFjdGVycyB3aXRoaW4gcXVvdGVzIGxpa2UgdGhpcyBgImhlbGxvImAgb3IgZXZlbiBsaWtlIHRoaXMgYCIyMzIzMiJgLgoKYGBgcHl0aG9uCm5hbWUgPSAiQm9iIgphZ2UgPSAiMjMiICMgPC0tLSB0aGlzIGlzIHN0aWxsIGEgc3RyaW5nIChpdCdzIHdpdGhpbiBxdW90ZXMpCmBgYAoKV2hlbiBjb2RpbmcgYSB3ZWIgYXBwbGljYXRpb24sIGV2ZXJ5dGhpbmcgdGhlIHVzZXIgdHlwZXMgaW4gZm9ybXMgaXQncyBjb25zaWRlcmVkIGEgYHN0cmluZ2AsIGV2ZW4gaWYgdGhlIHVzZXIgdHlwZXMgdGhlIG51bWJlciBgMmAgKHR3bykgaXQgd2lsbCBzdGlsbCBiZSBjb25zaWRlcmVkIHRoZSBzdHJpbmcgYCIyImAgIGFuZCBub3QgYSByZWFsIG51bWJlciwgdGhlIGRldmVsb3BlciB3aWxsIGhhdmUgdG8gZXhwbGljaXRlbHkgY29udmVydCBvciBwYXJzZSB0aGF0IHN0cmluZyBpbnRvIGEgbnVtYmVyIHVzaW5nIHRoZSBmdW5jdGlvbiBgaW50KClgICBvciBgZmxvYXQoKWAuCgo+IDpsaW5rOiBIb3cgdG8gW2NvbnZlcnQgc3RyaW5ncyBpbnRvIGludGVnZXJzIHdpdGggcHl0aG9uXShodHRwczovL2d1aWRlLmZyZWVjb2RlY2FtcC5vcmcvcHl0aG9uL2hvdy10by1jb252ZXJ0LXN0cmluZ3MtaW50by1pbnRlZ2Vycy1pbi1weXRob24vKSAoMyBtaW4gcmVhZCkuCgpUaGUgbW9zdCBjb21tb24gdXNlIGZvciBhIHN0cmluZyBpcyBwcmludGluZyBpdCB1c2luZyB0aGUgZnVuY3Rpb24gYHByaW50YAoKYGBgcHl0aG9uCnByaW50KCJIZWxsbyBXb3JsZCEiKQojIFRoZSBmdW5jdGlvbiBwcmludCgpIHJlY2VpdmVzIGEgc3RyaW5nIGFuZCBkaXNwbGF5cyBpdCBvbiB0aGUgY29tbWFuZCBsaW5lL3Rlcm1pbmFsLgogYGBgCgojIyBIb3cgZG8gd2UgdXNlIHN0cmluZ3M/CgojIyMgU3RyaW5nIGNvbmNhdGVuYXRpb24gKHN1bW1pbmcgc3RyaW5ncykKClB5dGhvbiBhbGxvd3MgdG8gc3VtIHRvZ2V0aGVyIHN0cmluZ3MgdXNpbmcgdGhlIHBsdXMgYCtgIG9wZXJhdG9yLiBUaGUgZm9sbG93aW5nIGZyYWdtZW50IGRlbW9uc3RyYXRlcyBob3cgdG8gYWRkIHR3byBzdHJpbmdzIHRvIGNyZWF0ZSBhICoqZnVsbCBuYW1lKiogZnJvbSAqKmZpcnN0KiogYW5kICoqbGFzdCBuYW1lcyoqLgoKYGBgcHl0aG9uCmZpcnN0X25hbWUgPSAiQWxlamFuZHJvIgpsYXN0X25hbWUgPSAiU2FuY2hleiIKZnVsbF9uYW1lID0gZmlyc3RfbmFtZSArICIgIiArIGxhc3RfbmFtZQpwcmludCgiTXkgbmFtZSBpcyAiK2Z1bGxfbmFtZSkKCiMgT3V0cHV0OiAiTXkgbmFtZSBpcyBBbGVqYW5kcm8gU2FuY2hleiIKIGBgYAoKSW4gdGhpcyBleGFtcGxlIGAiTXkgbmFtZSBpcyAiYCBpdCdzIGJlaW5nIGNvbmNhdGVuYXRlZCB3aXRoIHRoZSB2YWx1ZSBvbiB0aGUgdmFyaWFibGUgYGZ1bGxfbmFtZWAuCgojIyMgVGhlIGxlbmd0aCBvZiB0aGUgc3RyaW5nCgpZb3Ugb2Z0ZW4gd2FudCB0byBrbm93IHdoYXQgdGhlIGxlbmd0aCAoc2l6ZSkgb2YgYSBzdHJpbmcgaXMsIGZvciBleGFtcGxlOiBUd2l0dGVyIGRvZXMgbm90IGFsbG93IHR3ZWV0cyB3aXRoIG1vcmUgdGhhbiAyNDAgY2hhcmFjdGVycy4KCmBgYHB5dGhvbgp0d2VldCA9ICJHb29kIG1vcm5pbmchIgpwcmludCgiVGhlIHZhcmlhYmxlIHR3ZWV0IGNvbnRhaW5zICIrc3RyKGxlbih0d2VldCkpKyIgY2hhcmFjdGVycyIpCgojIE91dHB1dDogVGhlIHZhcmlhYmxlIHR3ZWV0IGNvbnRhaW5zIDEzIGNoYXJhY3RlcnMKYGBgCgoKIyMjIEV4dHJhY3RpbmcgY2hhcmFjdGVycwoKQWZ0ZXIgd2UgYWxzbyBuZWVkIHRvIGtub3cgdGhlIHZhbHVlIG9mIHRoZSBzdHJpbmcgaW4gYSBwYXJ0aWN1bGFyIHBvc2l0aW9uLCBmb3IgZXhhbXBsZTogSWYgYSBzdHJpbmcgZW5kcyB3aXRoIGEgcXVlc3Rpb24gbWFyayBpdCdzIHByb2JhYmx5IGEgcXVlc3Rpb246CgpgYGBweXRob24KcXVlc3Rpb24gPSAiSG93IGFyZSB5b3U/IgpzaXplID0gbGVuKHF1ZXN0aW9uKQpwcmludCgiVGhlIHN0cmluZ3Mgc3RhcnQgd2l0aCAiICsgcXVlc3Rpb25bMF0pCiMgT3V0cHV0OiBUaGUgc3RyaW5ncyBzdGFydCB3aXRoIEgKcHJpbnQoIlRoZSBzdHJpbmdzIGVuZHMgd2l0aCAiICsgcXVlc3Rpb25bc2l6ZSAtIDFdKQojIE91dHB1dDogVGhlIHN0cmluZ3MgZW5kcyB3aXRoID8KCmBgYAoKPiA6cG9pbnRfdXA6IFRoaXMgbWV0aG9kIG9mIGNoYXJhY3RlciBleHRyYWN0aW9uIG9uIHN0cmluZ3MgaXMgdmVyeSBzaW1pbGFyIHRvIHRoZSBvbmUgdXNlZCBvbiBsaXN0cyB0byBleHRyYWN0IGFuIGVsZW1lbnQgZnJvbSBhIHBhcnRpY3VsYXIgcG9zaXRpb24gaW4gdGhlIGxpc3QuICAgCgpZb3UgY2FuIGFsc28gZXh0cmFjdCBzZXZlcmFsIGNoYXJhY3RlcnMgYXQgb25jZS4gVGhlIHJhbmdlIG9mIHRoZSBtZXRob2Qgc3RhcnRzIHdpdGggdGhlIGluZGV4IG9mIHRoZSBmaXJzdCBjaGFyYWN0ZXIgdG8gYmUgZXh0cmFjdGVkIGFuZCBlbmRzIHdpdGggdGhlIGluZGV4IEFGVEVSIHRoZSBsYXN0IGNoYXJhY3RlciB0byBiZSBleHRyYWN0ZWQ6CgpgYGBweXRob24KbmFtZSA9ICJNeSBuYW1lIGlzIEFsZWphbmRybyBTYW5jaGV6IgpwcmludCgiRXh0cmFjdGVkICIgKyBuYW1lWzExOjIwXSkKIyBPdXRwdXQ6IEV4dHJhY3RlZCBBbGVqYW5kcm8KCnByaW50KCJFeHRyYWN0ZWQgIiArIG5hbWVbMTE6XSkKIyBPdXRwdXQ6IEV4dHJhY3RlZCBBbGVqYW5kcm8gU2FuY2hlegoKcHJpbnQoIkV4dHJhY3RlZCAiICsgbm9tYnJlWzoxMF0pCiMgT3V0cHV0OiBFeHRyYWN0ZWQgTXkgbmFtZSBpcyAKYGBgCgojIyMgQ29tcGFyaW5nIHN0cmluZ3MKCklmIHlvdSB3YW50IHRvIGNvbXBhcmUgdHdvIHN0cmluZ3MgeW91IGNhbiB1c2UgdGhlIGA9PWAgIChkb3VibGUgZXF1YWwpIGFuZCBpdCB3aWxsIHJldHVybiBgVHJ1ZWAgIGlmIHRoZSBzdHJpbmdzIGFyZSBFWEFDVExZIHRoZSBzYW1lLCBzdHJpbmcgY29tcGFyaXNvbiBpcyBjYXNlIHNlbnNpdGl2ZSwgIkJvYiIgaXMgbm90IGVxdWFsIHRvICJib2IiLgoKYGBgcHl0aG9uCm5hbWUxID0gInBlcGUiOwpuYW1lMiA9ICJqdWFuIjsKaWYgbmFtZTEgPT0gbmFtZTI6CiAgICBwcmludCgiVGhpcyBpcyBGYWxzZSwgSSB3aWxsIG5vdCBnZXQgcHJpbnRlZCIpCmlmIG5hbWUxID09ICJwZXBlIjoKICAgIHByaW50KCJUaGlzIGlzIFRydWUsIEkgd2lsbCBnZXQgcHJpbnRlZCIpCmlmIG5hbWUxICE9IG5hbWUyOgogICAgcHJpbnQoIlRoaXMgaXMgVHJ1ZSwgSSB3aWxsIGdldCBwcmludGVkIikKYGBgCgojIyMgQ29udmVydGluZyB0byBsb3dlciBvciB1cHBlciBjYXNlLgoKYGBgcHl0aG9uCmxvd2VyY2FzZWRfc3RyaW5nID0gbmFtZTEubG93ZXIoKSAjIHdpbGwgY29udmVydCB0byBsb3dlcmNhc2UKdXBwZXJjYXNlZF9zdHJpbmcgPSBuYW1lMi51cHBlcigpICMgd2lsbCBjb252ZXJ0IHRvIHVwcGVyY2FzZQpgYGAKCj4gOnBvaW50X3VwOiBpdCBpcyBnb29kIHByYWN0aWNlIHRvIGFsd2F5cyBsb3dlcmNhc2Ugc3RyaW5ncyBiZWZvcmUgY29tcGFyaW5nIHRoZW0gd2l0aCBvdGhlcnMsIHRoYXQgd2F5IHdlIHdpbGwgYXZvaWQgbWlzc2luZyBjYXNlIHNlbnNpdGl2ZSBkaWZmZXJlbmNlcy4KCiMjIyBDb252ZXJ0IHN0cmluZ3MgdG8gbnVtYmVycyAoYW5kIHZpY2UgdmVyc2EpCgpgYGBweXRob24KbnVtYmVyID0gMy40ICMgSSBhbSBhIG51bWJlcgpudW1iZXJfYXNfc3RyaW5nID0gc3RyKG51bWJlcikgIyBJIGFtIGEgc3RyaW5nIHdpdGggdmFsdWUgIjMuNCIKYGBgCgojIyMgTW9yZSBpbmZvcm1hdGlvbiBhYm91dCBzdHJpbmdzCgpJZiB5b3Ugd2FudCB0byBsZWFybiBtb3JlLCB3ZSBzdWdnZXN0IHlvdSBzdGFydCBwcmFjdGljaW5nIGluc3RlYWQgb2YgcmVhZGluZyBiZWNhdXNlIHRoZXJlIGlzIG5vdGhpbmcgbXVjaCB0byByZWFkIGFib3V0IHN0cmluZ3MsIGhlcmUgaXMgYSBzbWFsbCAzIG1pbiBbdmlkZW8gZXhwbGFpbmluZyBzdHJpbmdzXShodHRwczovL3d3dy55b3V0dWJlLmNvbS93YXRjaD92PWlBelNoa0t6cEpvKS4gCgpLZWVwIHByYWN0aWNpbmchCg=="


def test_with_no_assets(bc: Breathecode, client):

    url = reverse_lazy("registry:asset")
    response = client.get(url)
    json = response.json()

    assert json == []
    assert bc.database.list_of("registry.Asset") == []


def test_one_asset(bc: Breathecode, client):

    model = bc.database.create(asset={"status": "PUBLISHED"})

    url = reverse_lazy("registry:asset")
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset)]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == [bc.format.to_dict(model.asset)]


def test_many_assets(bc: Breathecode, client):

    model = bc.database.create(asset=(3, {"status": "PUBLISHED"}))

    url = reverse_lazy("registry:asset")
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(asset) for asset in model.asset]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets_expand_technologies(bc: Breathecode, client):

    technology = {"slug": "learn-react", "title": "Learn React"}
    model = bc.database.create(
        asset_technology=(1, technology),
        asset=(
            3,
            {
                "technologies": 1,
                "status": "PUBLISHED",
            },
        ),
    )

    url = reverse_lazy("registry:asset") + f"?expand=technologies"
    response = client.get(url)
    json = response.json()

    expected = [
        get_expanded_serializer(
            asset,
            data={
                "updated_at": bc.datetime.to_iso_string(asset.updated_at),
                "technologies": [get_serializer_technology(model.asset_technology)],
            },
        )
        for asset in model.asset
    ]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets_expand_readme_no_readme_url(bc: Breathecode, client):

    technology = {"slug": "learn-react", "title": "Learn React"}

    model = bc.database.create(
        asset_technology=(1, technology),
        asset=(
            1,
            {"technologies": 1, "status": "PUBLISHED", "readme": readme},
        ),
    )

    url = reverse_lazy("registry:asset") + f"?expand=readme"
    response = client.get(url)
    json = response.json()

    asset_readme = model.asset.get_readme()

    expected = [
        get_expanded_serializer(
            model.asset,
            data={
                "updated_at": bc.datetime.to_iso_string(model.asset.updated_at),
                "readme": {"decoded": asset_readme["decoded"], "html": None},
            },
        )
    ]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == [bc.format.to_dict(model.asset)]


def test_assets_expand_readme(bc: Breathecode, client):

    technology = {"slug": "learn-react", "title": "Learn React"}
    readme_url = "https://github.com/4GeeksAcademy/03-probability-binomial-with-python.md"

    model = bc.database.create(
        asset_technology=(1, technology),
        asset=(
            1,
            {"technologies": 1, "status": "PUBLISHED", "readme": readme, "readme_url": readme_url},
        ),
    )

    url = reverse_lazy("registry:asset") + f"?expand=readme"
    response = client.get(url)
    json = response.json()

    asset_readme = model.asset.get_readme(parse=True, remove_frontmatter=True)

    expected = [
        get_expanded_serializer(
            model.asset,
            data={
                "updated_at": bc.datetime.to_iso_string(model.asset.updated_at),
                "readme": {"decoded": asset_readme["decoded"], "html": asset_readme["html"]},
            },
        )
    ]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == [bc.format.to_dict(model.asset)]


def test_assets_expand_readme_ipynb(bc: Breathecode, client):

    technology = {"slug": "learn-react", "title": "Learn React"}
    readme_url_ipynb = "https://github.com/4GeeksAcademy/03-probability-binomial-with-python.ipynb"
    html = "<h1>hello</h1>"

    model = bc.database.create(
        asset_technology=(1, technology),
        asset=(
            1,
            {"technologies": 1, "status": "PUBLISHED", "readme": readme, "readme_url": readme_url_ipynb, "html": html},
        ),
    )

    url = reverse_lazy("registry:asset") + f"?expand=readme"
    response = client.get(url)
    json = response.json()

    asset_readme = model.asset.get_readme()

    expected = [
        get_expanded_serializer(
            model.asset,
            data={
                "updated_at": bc.datetime.to_iso_string(model.asset.updated_at),
                "readme": {"decoded": asset_readme["decoded"], "html": model.asset.html},
            },
        )
    ]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == [bc.format.to_dict(model.asset)]


def test_assets_expand_readme_and_technologies(bc: Breathecode, client):

    technology = {"slug": "learn-react", "title": "Learn React"}
    readme_url = "https://github.com/4GeeksAcademy/03-probability-binomial-with-python.md"
    model = bc.database.create(
        asset_technology=(1, technology),
        asset=(
            1,
            {"technologies": 1, "status": "PUBLISHED", "readme": readme, "readme_url": readme_url},
        ),
    )

    url = reverse_lazy("registry:asset") + f"?expand=technologies,readme"
    response = client.get(url)
    json = response.json()

    asset_readme = model.asset.get_readme(parse=True, remove_frontmatter=True)

    expected = [
        get_expanded_serializer(
            model.asset,
            data={
                "updated_at": bc.datetime.to_iso_string(model.asset.updated_at),
                "readme": {
                    "decoded": asset_readme["decoded"],
                    "html": asset_readme["html"],
                },
                "technologies": [get_serializer_technology(model.asset_technology)],
            },
        )
    ]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == [bc.format.to_dict(model.asset)]


def test_assets_with_slug(bc: Breathecode, client):

    assets = [
        {
            "slug": "randy",
            "status": "PUBLISHED",
        },
        {
            "slug": "jackson",
            "status": "PUBLISHED",
        },
    ]
    model = bc.database.create(asset=assets)

    url = reverse_lazy("registry:asset") + "?slug=randy"
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[0])]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets_with_lang(bc: Breathecode, client):

    assets = [
        {
            "lang": "us",
            "status": "PUBLISHED",
        },
        {
            "lang": "es",
            "status": "PUBLISHED",
        },
    ]
    model = bc.database.create(asset=assets)

    url = reverse_lazy("registry:asset") + "?language=en"
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[0])]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets__hidden_all_non_visibilities(bc: Breathecode, client):

    assets = [
        {
            "visibility": "PUBLIC",
            "status": "PUBLISHED",
        },
        {
            "visibility": "PRIVATE",
            "status": "PUBLISHED",
        },
        {
            "visibility": "UNLISTED",
            "status": "PUBLISHED",
        },
    ]
    model = bc.database.create(asset=assets)

    url = reverse_lazy("registry:asset")
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[0])]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets_with_bad_academy(bc: Breathecode, client):

    model = bc.database.create(asset=2)

    url = reverse_lazy("registry:asset") + "?academy=banana"
    response = client.get(url)
    json = response.json()

    expected = {"detail": "academy-id-must-be-integer", "status_code": 400}

    assert json == expected
    assert response.status_code == 400
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets_with_academy(bc: Breathecode, client):

    academies = bc.database.create(academy=2)
    assets = [
        {
            "academy": academies.academy[0],
            "status": "PUBLISHED",
        },
        {
            "academy": academies.academy[1],
            "status": "PUBLISHED",
        },
    ]
    model = bc.database.create(asset=assets)

    url = reverse_lazy("registry:asset") + "?academy=2"
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[1])]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


def test_assets_with_category(bc: Breathecode, client):

    categories = [{"slug": "how-to"}, {"slug": "como"}]
    model_categories = bc.database.create(asset_category=categories)
    assets = [
        {
            "category": model_categories.asset_category[0],
            "status": "PUBLISHED",
        },
        {
            "category": model_categories.asset_category[1],
            "status": "PUBLISHED",
        },
    ]
    model = bc.database.create(asset=assets)

    url = reverse_lazy("registry:asset") + "?category=how-to"
    response = client.get(url)
    json = response.json()

    expected = [get_serializer(model.asset[0])]

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)


@patch(
    "breathecode.utils.api_view_extensions.extensions.lookup_extension.compile_lookup",
    MagicMock(wraps=lookup_extension.compile_lookup),
)
def test_lookup_extension(bc: Breathecode, client):

    assets = [
        {
            "asset_type": "LESSON",
            "status": "PUBLISHED",
        },
        {
            "asset_type": "PROJECT",
            "status": "PUBLISHED",
        },
    ]
    model = bc.database.create(asset=assets)

    args, kwargs = bc.format.call(
        "en",
        strings={
            "iexact": [
                "test_status",
                "sync_status",
            ],
            "in": ["difficulty", "status", "asset_type", "category__slug", "technologies__slug", "seo_keywords__slug"],
        },
        ids=["author", "owner"],
        bools={
            "exact": ["with_video", "interactive", "graded"],
        },
        overwrite={
            "category": "category__slug",
            "technologies": "technologies__slug",
            "seo_keywords": "seo_keywords__slug",
        },
    )

    query = bc.format.lookup(*args, **kwargs)
    url = reverse_lazy("registry:asset") + "?" + bc.format.querystring(query)

    assert [x for x in query] == [
        "author",
        "owner",
        "test_status",
        "sync_status",
        "difficulty",
        "status",
        "asset_type",
        "category",
        "technologies",
        "seo_keywords",
        "with_video",
        "interactive",
        "graded",
    ]

    response = client.get(url)

    json = response.json()

    expected = []

    assert json == expected
    assert bc.database.list_of("registry.Asset") == bc.format.to_dict(model.asset)
