from breathecode.utils import Cache
from .models import Asset


class AssetCache(Cache):
    model = Asset
    depends = ['User', 'AssetTechnology', 'AssetCategory', 'KeywordCluster', 'AssetKeyword', 'Assessment']
    parents = ['AssetAlias', 'AssetErrorLog']
