from __future__ import annotations

import re

SECRET_PATTERNS = (
    re.compile(
        r"(?i)\b([\w-]*(?:api[_-]?key|token|secret|password))\s*[=:](?!=)\s*[\"']?([A-Za-z0-9_./+\-]{6,})"
    ),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bnvapi-[A-Za-z0-9_-]{12,}\b"),
    re.compile(
        r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----.*?-----END (?:[A-Z]+ )?PRIVATE KEY-----",
        re.DOTALL,
    ),
)


def redact(text: str, replacement: str = "[REDACTED]") -> str:
    result = text
    for pattern in SECRET_PATTERNS:
        if pattern.groups:
            result = pattern.sub(lambda match: f"{match.group(1)}={replacement}", result)
        else:
            result = pattern.sub(replacement, result)
    return result
