import os
from typing import Optional
from urllib.parse import urlparse

from django.core.handlers.wsgi import WSGIRequest
from rest_framework.request import Request


def _trusted_proxy_count() -> int:
    try:
        return max(1, int(os.getenv("TRUSTED_PROXY_COUNT", "1")))
    except ValueError:
        return 1


def get_client_ip(request: WSGIRequest | Request) -> str:
    """
    Return the client IP from X-Forwarded-For.

    Each trusted proxy appends the address it received the request from, so the client IP is the entry added by
    the outermost proxy, `TRUSTED_PROXY_COUNT` positions from the end (Heroku's router is one proxy). Entries before
    it are supplied by the client and can be spoofed.
    """
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        if hops:
            return hops[-min(_trusted_proxy_count(), len(hops))]

    return request.META.get("REMOTE_ADDR") or "unknown"


def get_current_academy(request: WSGIRequest | Request, return_id: bool = True) -> Optional[int | object]:
    """
    Detect the current academy from multiple sources in priority order:
    1. Academy header (case-insensitive)
    2. academy field in request body/payload
    3. academy query parameter
    4. HTTP_ORIGIN/HTTP_REFERER matching Academy.website_url (for white label academies)
    
    Args:
        request: Django WSGIRequest or DRF Request object
        return_id: If True, returns academy_id (int). If False, returns Academy model instance.
    
    Returns:
        Optional[int | Academy]: Academy ID or Academy instance, or None if not found
    """
    from breathecode.admissions.models import Academy
    
    academy_id = None
    academy_value = None
    
    # Priority 1: Check Academy header (case-insensitive)
    if "Academy" in request.headers:
        academy_value = request.headers["Academy"]
    elif "academy" in request.headers:
        academy_value = request.headers["academy"]
    
    # Priority 2: Check request body/payload
    if not academy_value and hasattr(request, "data"):
        academy_value = request.data.get("academy")
    
    # Priority 3: Check query parameter
    if not academy_value and hasattr(request, "GET"):
        academy_value = request.GET.get("academy")
    
    # If we found a value, try to convert it to academy_id
    if academy_value:
        if isinstance(academy_value, int):
            academy_id = academy_value
        elif isinstance(academy_value, str) and academy_value.isdigit():
            academy_id = int(academy_value)
        elif isinstance(academy_value, str):
            # Try to find by slug
            academy = Academy.objects.filter(slug=academy_value).first()
            if academy:
                academy_id = academy.id
    
    # Priority 4: Detect from HTTP origin/referer for white label academies
    if not academy_id:
        origin = request.META.get("HTTP_ORIGIN") or request.META.get("HTTP_REFERER")
        
        if origin:
            try:
                parsed_origin = urlparse(origin)
                origin_base = f"{parsed_origin.scheme}://{parsed_origin.netloc}"
                
                # Try to find an academy with matching website_url
                academy = Academy.objects.filter(
                    website_url__isnull=False
                ).exclude(
                    website_url=""
                ).filter(
                    website_url__icontains=origin_base
                ).first()
                
                if academy:
                    academy_id = academy.id
            except Exception:
                # If URL parsing fails, continue without academy_id
                pass
    
    if not academy_id:
        return None
    
    if return_id:
        return academy_id
    
    # Return Academy instance
    return Academy.objects.filter(id=academy_id).first()

