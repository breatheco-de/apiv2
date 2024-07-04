from breathecode.utils import Cache
from .models import (
    Asset,
    AssetComment,
    AssetTechnology,
    AssetKeyword,
    KeywordCluster,
    AssetCategory,
    ContentVariable,
    AssetAlias,
)


class AssetCache(Cache):
    model = Asset


class AssetCommentCache(Cache):
    model = AssetComment


class AssetAliasCache(Cache):
    model = AssetAlias


class TechnologyCache(Cache):
    model = AssetTechnology


class ContentVariableCache(Cache):
    model = ContentVariable


class CategoryCache(Cache):
    model = AssetCategory


class KeywordCache(Cache):
    model = AssetKeyword


class KeywordClusterCache(Cache):
    model = KeywordCluster
