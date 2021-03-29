class ScriptNotification(Exception):
    def __init__(self, details, status=None):
        self.status_code = 1
        self.status = status
        super().__init__(details)
