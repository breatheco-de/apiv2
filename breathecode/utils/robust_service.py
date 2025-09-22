import logging
import time
from typing import Optional
from capyc.rest_framework.exceptions import ValidationException
from capyc.core.i18n import translation

from linked_services.django.service import Service as BaseService

logger = logging.getLogger(__name__)


class ServiceTimeoutException(ValidationException):
    """Custom exception for service timeouts with proper HTTP status code."""

    def __init__(self, service_name: str, path: str, timeout: float, duration: float):
        super().__init__(
            translation(
                "en",
                en=f"The {service_name} service request timed out after {duration:.1f}s (limit: {timeout}s). Please try again.",
                es=f"La solicitud al servicio {service_name} se agotó después de {duration:.1f}s (límite: {timeout}s). Por favor intenta de nuevo.",
                slug="service-timeout",
            ),
            code=504,
            slug="service-timeout",
        )


SERVICE_TIMEOUTS = {
    "rigobot": 15,
    "learnpack": 15,
}


def get_service_timeout(service_name: str, default: int = 20) -> int:
    """
    Get the appropriate timeout for a service.

    Args:
        service_name: Name of the service (e.g., 'rigobot', 'github')
        default: Default timeout if service is not in our configuration

    Returns:
        Timeout in seconds for the specified service
    """
    timeout = SERVICE_TIMEOUTS.get(service_name, default)
    logger.debug(f"Using timeout {timeout}s for service {service_name}")
    return timeout


def create_robust_service(
    service_name: str, user_id: Optional[int] = None, proxy: bool = False, timeout: Optional[int] = None
) -> "Service":
    """
    Create a robust service instance with timeout protection.

    This is a convenience function that creates a Service instance with proper timeout handling.
    Use this instead of directly importing linked_services.Service to get timeout protection.

    Args:
        service_name: Name of the service (e.g., 'rigobot', 'github', 'learnpack')
        user_id: User ID for authentication
        proxy: Whether to use proxy mode
        timeout: Custom timeout in seconds. If None, uses service-specific default.

    Returns:
        Service instance with timeout protection

    Example:
        # Synchronous usage
        with create_robust_service('rigobot', user_id=1) as s:
            response = s.get('/v1/some/endpoint')

        # Asynchronous usage
        async with create_robust_service('rigobot', user_id=1) as s:
            response = await s.get('/v1/some/endpoint')
    """
    return Service(service_name, user_id, proxy, timeout)


class Service(BaseService):
    """
    Enhanced Service class with timeout protection.

    This is a drop-in replacement for linked_services.Service that adds:
    - Automatic timeout handling to prevent Heroku timeouts (30s limit)
    - Detailed logging of request durations and failures
    - Proper timeout exception handling for both sync and async requests
    - Service-specific timeout configuration
    - Same interface as the original Service class

    The timeout is applied at the HTTP request level, ensuring that:
    1. Requests are cancelled before Heroku's 30-second timeout
    2. Proper Timeout exceptions are raised with detailed logging
    3. Request durations are tracked and logged for monitoring

    Args:
        service_name (str): Name of the service (e.g., 'rigobot', 'learnpack')
        user_id (int, optional): User ID for authentication
        proxy (bool): Whether to use proxy mode
        timeout (int): Timeout in seconds. If None, uses service-specific default.

    Example:
        # Synchronous usage with automatic timeout
        with Service('rigobot', user_id=1) as s:
            response = s.get('/v1/some/endpoint')  # Will timeout after 15s (rigobot default)

        # Asynchronous usage with custom timeout
        async with Service('rigobot', user_id=1, timeout=10) as s:
            response = await s.get('/v1/some/endpoint')  # Will timeout after 10s
    """

    def __init__(
        self, service_name: str, user_id: Optional[int] = None, proxy: bool = False, timeout: Optional[int] = None
    ):
        """
        Initialize RobustService.

        Args:
            service_name: Name of the service (e.g., 'rigobot', 'learnpack')
            user_id: User ID for authentication
            proxy: Whether to use proxy mode (stored for compatibility, but not used in parent constructor)
            timeout: Custom timeout in seconds. If None, uses service-specific default.
        """
        try:
            super().__init__(service_name, user_id, proxy=proxy)
        except TypeError:
            super().__init__(service_name, user_id)
            self.proxy = proxy

        if timeout is None:
            self.timeout = get_service_timeout(service_name)
        else:
            self.timeout = timeout

        self.service_name = service_name

        logger.info(f"Created robust service for {service_name} with timeout {self.timeout}s")

    def get(self, path: str, **kwargs):
        """
        GET request with timeout protection.

        Args:
            path: API endpoint path
            **kwargs: Additional arguments passed to the original get method

        Returns:
            Response object from the service
        """
        start_time = time.time()
        request_timeout = kwargs.pop("timeout", self.timeout)

        logger.debug(f"Making GET request to {self.service_name}{path} with timeout {request_timeout}s")

        try:
            response = super().get(path, timeout=request_timeout, **kwargs)

            duration = time.time() - start_time
            logger.debug(f"GET {self.service_name}{path} completed successfully in {duration:.2f}s")

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"GET {self.service_name}{path} failed with unexpected error after {duration:.2f}s: {e}")

            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                logger.error(
                    f"GET {self.service_name}{path} timed out after {duration:.2f}s (limit: {request_timeout}s): {e}"
                )
                raise ServiceTimeoutException(self.service_name, path, request_timeout, duration)

            raise

    def post(self, path: str, **kwargs):
        """
        POST request with timeout protection.

        Args:
            path: API endpoint path
            **kwargs: Additional arguments passed to the original post method

        Returns:
            Response object from the service
        """
        start_time = time.time()
        request_timeout = kwargs.pop("timeout", self.timeout)

        logger.debug(f"Making POST request to {self.service_name}{path} with timeout {request_timeout}s")

        try:
            response = super().post(path, timeout=request_timeout, **kwargs)

            duration = time.time() - start_time
            logger.debug(f"POST {self.service_name}{path} completed successfully in {duration:.2f}s")

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"POST {self.service_name}{path} failed with unexpected error after {duration:.2f}s: {e}")

            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                logger.error(
                    f"POST {self.service_name}{path} timed out after {duration:.2f}s (limit: {request_timeout}s): {e}"
                )
                raise ServiceTimeoutException(self.service_name, path, request_timeout, duration)

            raise

    def put(self, path: str, **kwargs):
        """
        PUT request with timeout protection.

        Args:
            path: API endpoint path
            **kwargs: Additional arguments passed to the original put method

        Returns:
            Response object from the service
        """
        start_time = time.time()
        request_timeout = kwargs.pop("timeout", self.timeout)

        logger.debug(f"Making PUT request to {self.service_name}{path} with timeout {request_timeout}s")

        try:
            response = super().put(path, timeout=request_timeout, **kwargs)

            duration = time.time() - start_time
            logger.debug(f"PUT {self.service_name}{path} completed successfully in {duration:.2f}s")

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"PUT {self.service_name}{path} failed with unexpected error after {duration:.2f}s: {e}")

            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                logger.error(
                    f"PUT {self.service_name}{path} timed out after {duration:.2f}s (limit: {request_timeout}s): {e}"
                )
                raise ServiceTimeoutException(self.service_name, path, request_timeout, duration)

            raise

    def delete(self, path: str, **kwargs):
        """
        DELETE request with timeout protection.

        Args:
            path: API endpoint path
            **kwargs: Additional arguments passed to the original delete method

        Returns:
            Response object from the service
        """
        start_time = time.time()
        request_timeout = kwargs.pop("timeout", self.timeout)

        logger.debug(f"Making DELETE request to {self.service_name}{path} with timeout {request_timeout}s")

        try:
            response = super().delete(path, timeout=request_timeout, **kwargs)

            duration = time.time() - start_time
            logger.debug(f"DELETE {self.service_name}{path} completed successfully in {duration:.2f}s")

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"DELETE {self.service_name}{path} failed with unexpected error after {duration:.2f}s: {e}")

            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                logger.error(
                    f"DELETE {self.service_name}{path} timed out after {duration:.2f}s (limit: {request_timeout}s): {e}"
                )
                raise ServiceTimeoutException(self.service_name, path, request_timeout, duration)

            raise

    async def async_get(self, path: str, **kwargs):
        """
        Async GET request with timeout protection.

        Args:
            path: API endpoint path
            **kwargs: Additional arguments passed to the original async get method

        Returns:
            Response object from the service
        """
        start_time = time.time()
        request_timeout = kwargs.pop("timeout", self.timeout)

        logger.debug(f"Making async GET request to {self.service_name}{path} with timeout {request_timeout}s")

        try:
            response = await super().get(path, timeout=request_timeout, **kwargs)

            duration = time.time() - start_time
            logger.debug(f"Async GET {self.service_name}{path} completed successfully in {duration:.2f}s")

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Async GET {self.service_name}{path} failed with unexpected error after {duration:.2f}s: {e}")

            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                logger.error(
                    f"Async GET {self.service_name}{path} timed out after {duration:.2f}s (limit: {request_timeout}s): {e}"
                )
                raise ServiceTimeoutException(self.service_name, path, request_timeout, duration)

            raise

    async def async_post(self, path: str, **kwargs):
        """
        Async POST request with timeout protection.

        Args:
            path: API endpoint path
            **kwargs: Additional arguments passed to the original async post method

        Returns:
            Response object from the service
        """
        start_time = time.time()
        request_timeout = kwargs.pop("timeout", self.timeout)

        logger.debug(f"Making async POST request to {self.service_name}{path} with timeout {request_timeout}s")

        try:
            response = await super().post(path, timeout=request_timeout, **kwargs)

            duration = time.time() - start_time
            logger.debug(f"Async POST {self.service_name}{path} completed successfully in {duration:.2f}s")

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Async POST {self.service_name}{path} failed with unexpected error after {duration:.2f}s: {e}"
            )

            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                logger.error(
                    f"Async POST {self.service_name}{path} timed out after {duration:.2f}s (limit: {request_timeout}s): {e}"
                )
                raise ServiceTimeoutException(self.service_name, path, request_timeout, duration)

            raise
