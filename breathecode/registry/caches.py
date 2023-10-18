from breathecode.utils import Cache
from .models import Asset, AssetComment, AssetTechnology, AssetKeyword, KeywordCluster, AssetCategory, ContentVariable


class AssetCache(Cache):
    model = Asset
    # KeywordCluster?
    depends = [
        'User', 'AssetTechnology', 'AssetCategory', 'KeywordCluster', 'AssetKeyword', 'Assessment', 'Academy'
    ]
    parents = ['AssetAlias', 'AssetComment', 'SEOReport', 'AssetImage', 'OriginalityScan', 'AssetErrorLog']


class AssetCommentCache(Cache):
    model = AssetComment
    depends = ['Asset', 'User']
    parents = []


class TechnologyCache(Cache):
    model = AssetTechnology
    depends = ['Asset']
    parents = ['Asset']


class ContentVariableCache(Cache):
    model = ContentVariable
    depends = ['Academy']
    parents = []


class CategoryCache(Cache):
    model = AssetCategory
    depends = ['Academy']
    parents = ['AssetCategory']


class KeywordCache(Cache):
    model = AssetKeyword
    depends = ['KeywordCluster', 'Academy']
    parents = ['KeywordCluster']


class KeywordClusterCache(Cache):
    model = KeywordCluster
    depends = ['Academy']
    parents = []
