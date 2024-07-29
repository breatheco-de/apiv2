__all__ = ["ScriptNotification"]


class ScriptNotification(Exception):

    def __init__(self, details, slug=None, status=None, title=None, btn_url=None, btn_label=None):
        self.status_code = 1
        self.status = status
        self.title = title
        self.slug = slug
        self.btn_url = btn_url
        self.btn_label = btn_label
        super().__init__(details)


class WrongScriptConfiguration(Exception):
    pass
