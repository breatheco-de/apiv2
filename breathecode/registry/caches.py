from breathecode.utils import Cache
from .models import Asset, AssetComment, AssetTechnology, AssetKeyword, KeywordCluster, AssetCategory


class AssetCache(Cache):
    model = Asset
    depends = ['User', 'AssetTechnology', 'AssetCategory', 'KeywordCluster', 'AssetKeyword', 'Assessment']
    parents = ['AssetAlias', 'AssetErrorLog']


class AssetCommentCache(Cache):
    model = AssetComment
    depends = ['Asset', 'User']
    parents = []


class TechnologyCache(Cache):
    model = AssetTechnology
    depends = []
    parents = []


class CategoryCache(Cache):
    model = AssetCategory
    depends = []
    parents = []


class KeywordCache(Cache):
    model = AssetKeyword
    depends = []
    parents = ['KeywordCluster']


class KeywordClusterCache(Cache):
    model = KeywordCluster
    depends = ['KeywordCluster']
    parents = []
