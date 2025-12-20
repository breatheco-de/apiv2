from breathecode.utils import serpy


class ActivitySerializer(serpy.Serializer):
    id = serpy.Field()
    user_id = serpy.Field()
    kind = serpy.Field()
    related = serpy.Field()
    meta = serpy.MethodField()
    academy = serpy.MethodField()
    timestamp = serpy.Field()

    def get_meta(self, obj):
        res = {}

        # Handle BigQuery Row object - it's dict-like
        if obj.meta:
            # Use .keys() for Row objects, or iterate directly for dicts
            keys = obj.meta.keys() if hasattr(obj.meta, 'keys') else obj.meta
            for key in keys:
                value = obj.meta.get(key) if hasattr(obj.meta, 'get') else obj.meta[key]
                if value is not None:
                    res[key] = value

        return res

    def get_academy(self, obj):
        """Return academy ID if present in meta."""
        if not obj.meta:
            return None
        
        # BigQuery Row objects support .get() method
        return obj.meta.get("academy") if hasattr(obj.meta, 'get') else None
