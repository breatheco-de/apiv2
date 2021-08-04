class ScriptNotification(Exception):
    def __init__(self, details, slug=None, status=None, title=None):
        self.status_code = 1
        self.status = status
        self.title = title
        self.slug = slug
        super().__init__(details)
