import gzip
from io import BytesIO
import os
from django.utils.deprecation import MiddlewareMixin

IS_TEST = os.getenv('ENV', '') not in ['production', 'staging', 'development']


class CompressResponseMiddleware(MiddlewareMixin):

    def process_response(self, request, response):
        # If the response is already compressed, do nothing
        if 'Content-Encoding' in response.headers or IS_TEST:
            return response

        # Compress the response if it's large enough
        if response.content:
            accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
            if 'gzip' in accept_encoding:
                buffer = BytesIO()
                with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
                    f.write(response.content)
                compressed_content = buffer.getvalue()

                response.content = compressed_content
                response['Content-Encoding'] = 'gzip'
                response['Content-Length'] = str(len(compressed_content))

        return response
