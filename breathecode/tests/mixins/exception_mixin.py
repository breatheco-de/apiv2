class ExceptionMixin():
    """Headers mixin"""
    def assertException(self, callback, message: str, exception=Exception):
        if not callable(callback):
            raise Exception('function is not callable')

        try:
            callback()
            assert False
        except Exception as e:
            self.assertEqual(str(e), message)
