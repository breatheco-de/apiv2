class AttrDict(dict):
    """support use one dict like one javascript object"""
    def __init__(self, **kwargs):
        dict.__init__(self, **kwargs)

    def __setattr__(self, name, value):
        self[name] = value

    def __getattr__(self, name):
        return self[name]
