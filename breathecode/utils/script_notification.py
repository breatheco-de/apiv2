class ScriptNotification(Exception):
    def __init__(self, details, slug=None, status=None):
        self.status_code = 1
        self.status = status
        self.slug = slug
        super().__init__(details)
