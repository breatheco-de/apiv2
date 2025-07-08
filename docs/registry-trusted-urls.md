# Registry Trusted URLs System

The BreatheCode registry module includes a trusted URL system that allows skipping validation for specific domains and URLs that are known to be reliable but may have intermittent connectivity issues.

## Overview

During asset validation, the system checks all URLs found in README files. Some external domains may have temporary connectivity issues, rate limiting, or other problems that cause validation to fail even though the URLs are valid and trusted.

The trusted URL system provides a way to skip validation for these problematic but reliable URLs.

## Configuration

### Trusted Domains

Add domains to the `TRUSTED_DOMAINS` set in `breathecode/registry/utils.py`:

```python
TRUSTED_DOMAINS = {
    'exploit-db.com',
    'docs.python.org',
    'developer.mozilla.org',
    'stackoverflow.com',
}
```

Any URL from these domains will be skipped during validation, regardless of the specific path.

### Trusted URLs

Add specific URLs to the `TRUSTED_URLS` set in `breathecode/registry/utils.py`:

```python
TRUSTED_URLS = {
    'https://example.com/specific/path',
    'https://another-site.com/another/path',
}
```

Only these exact URLs (ignoring query strings and fragments) will be skipped during validation.

## How It Works

1. **Domain Matching**: The system extracts the domain from the URL and checks if it's in the trusted domains list
2. **www. Handling**: The `www.` prefix is automatically removed for domain comparison
3. **URL Normalization**: Query strings and fragments are removed when comparing against trusted URLs
4. **Case Insensitive**: Domain comparison is case-insensitive

## Examples

```python
# These URLs will be trusted if 'exploit-db.com' is in TRUSTED_DOMAINS:
'https://exploit-db.com/exploits/12345'
'http://www.exploit-db.com/some/path?query=test#fragment'
'https://exploit-db.com/'

# These URLs will NOT be trusted:
'https://untrusted-domain.com/path'
'https://example.com/path'  # (unless specifically added)
```

## Dynamic Configuration

You can also add trusted domains and URLs at runtime:

```python
from breathecode.registry.utils import add_trusted_domain, add_trusted_url

# Add a domain
add_trusted_domain('new-trusted-domain.com')

# Add a specific URL
add_trusted_url('https://example.com/special/path?param=value')
```

## Validation Output

When a trusted URL is encountered, you'll see this message in the validation output:

```
✅ Skipping validation for trusted URL: https://exploit-db.com/exploits/12345
```

## Benefits

- **Reliability**: Avoid false negatives from temporarily unreachable but valid URLs
- **Performance**: Skip time-consuming network requests for known good URLs
- **Maintenance**: Reduce manual intervention when trusted sites have temporary issues

## Security Considerations

- Only add domains and URLs that you absolutely trust
- Regularly review the trusted lists to ensure they're still appropriate
- Consider the security implications of skipping validation for external content

## Usage Guidelines

1. **Add domains sparingly**: Only add domains that frequently cause validation issues but are known to be reliable
2. **Document additions**: Add comments explaining why a domain/URL was added to the trusted list
3. **Monitor regularly**: Periodically check if trusted domains are still necessary
4. **Prefer domains over URLs**: When possible, trust entire domains rather than specific URLs for easier maintenance 