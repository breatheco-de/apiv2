class MessagesMock:
    request = None
    message = None
    call_list = []

    def reset(self):
        self.request = None
        self.message = None
        self.call_list = []

    def success(self, request, message):
        self.request = request
        self.message = message
        self.call_list.append("success")

    def error(self, request, message):
        self.request = request
        self.message = message
        self.call_list.append("error")
