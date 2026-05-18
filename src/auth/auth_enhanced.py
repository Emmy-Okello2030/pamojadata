"""
Enhanced Authentication Module - Security Hardening
Provides additional security utilities and middleware for the auth system.
"""

import re
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

def sanitize_input(value: str, max_length: int = 255, allowed_chars: Optional[str] = None) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        value: The input string to sanitize
        max_length: Maximum allowed length
        allowed_chars: Regex pattern for allowed characters (None = alphanumeric + basic punctuation)
    
    Returns:
        Sanitized string
    """
    if not isinstance(value, str):
        return ""
    
    value = value.strip()[:max_length]
    
    if allowed_chars is None:
        # Default: alphanumeric, spaces, hyphens, underscores, dots, @
        allowed_chars = r"^[\w\s\-\.@]+$"
    
    if not re.match(allowed_chars, value):
        raise ValueError("Input contains disallowed characters")
    
    return value


def validate_session_binding(session_ip: str, session_agent: str, current_ip: str, current_agent: str) -> bool:
    """
    Validate that a session is being used from the same IP/User-Agent.
    This helps detect session hijacking.
    
    Args:
        session_ip: IP address from session creation
        session_agent: User-Agent from session creation
        current_ip: Current request IP
        current_agent: Current request User-Agent
    
    Returns:
        True if binding is valid (or not configured), False if suspicious
    """
    # IP binding: Allow if same IP or if session IP is empty (not recorded)
    if session_ip and current_ip and session_ip != current_ip:
        return False
    
    # User-Agent binding: Allow if same or if not recorded
    if session_agent and current_agent and session_agent != current_agent:
        return False
    
    return True


def rate_limit_check(attempts: list, window_seconds: int = 300, max_attempts: int = 10) -> bool:
    """
    Check if rate limit has been exceeded.
    
    Args:
        attempts: List of attempt timestamps (ISO format strings)
        window_seconds: Time window to check (default 5 minutes)
        max_attempts: Maximum attempts allowed in window
    
    Returns:
        True if within limit, False if exceeded
    """
    if not attempts:
        return True
    
    now = datetime.now(timezone.utc)
    recent = []
    
    for attempt_str in attempts:
        try:
            attempt_time = datetime.fromisoformat(attempt_str)
            seconds_ago = (now - attempt_time).total_seconds()
            if seconds_ago < window_seconds:
                recent.append(attempt_time)
        except (ValueError, TypeError):
            continue
    
    return len(recent) < max_attempts


def generate_csrf_token(session_id: str, user_id: int) -> str:
    """
    Generate a CSRF token (though Streamlit handles this automatically).
    Provided for completeness in case of future API expansion.
    
    Args:
        session_id: Session identifier
        user_id: User ID
    
    Returns:
        CSRF token
    """
    import secrets
    import hashlib
    
    combined = f"{session_id}:{user_id}:{datetime.now(timezone.utc).isoformat()}"
    token = secrets.token_hex(16)
    return token


def log_security_event(event_type: str, user_id: Optional[int], details: Dict[str, Any], severity: str = "info") -> None:
    """
    Log security-related events for audit purposes.
    
    Args:
        event_type: Type of security event (e.g., "failed_login", "privilege_escalation_attempt")
        user_id: User ID (if applicable)
        details: Additional details about the event
        severity: Event severity ("info", "warning", "critical")
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    log_entry = {
        "timestamp": timestamp,
        "event_type": event_type,
        "user_id": user_id,
        "severity": severity,
        "details": details
    }
    # In production, this would write to a dedicated security log file or SIEM
    print(f"[SECURITY] {severity.upper()}: {event_type} - {json.dumps(log_entry)}")


def validate_password_complexity(password: str) -> tuple[bool, str]:
    """
    Enhanced password complexity validation.
    
    Args:
        password: Password to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long."
    
    if len(password) > 128:
        return False, "Password must not exceed 128 characters."
    
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()-_=+[]{}|;:,<.>/?" for c in password)
    
    if not (has_lower and has_upper and has_digit and has_special):
        return False, "Password must contain uppercase, lowercase, numbers, and special characters."
    
    # Check for common patterns
    common_patterns = ["password", "admin", "123456", "qwerty", "pamoja"]
    if any(pattern in password.lower() for pattern in common_patterns):
        return False, "Password contains common patterns. Please choose a stronger password."
    
    return True, ""


def get_password_strength_score(password: str) -> int:
    """
    Calculate password strength score (0-100).
    
    Args:
        password: Password to score
    
    Returns:
        Strength score from 0 to 100
    """
    score = 0
    
    if len(password) >= 12:
        score += 10
    if len(password) >= 16:
        score += 10
    if len(password) >= 20:
        score += 10
    
    if any(c.islower() for c in password):
        score += 15
    if any(c.isupper() for c in password):
        score += 15
    if any(c.isdigit() for c in password):
        score += 15
    if any(c in "!@#$%^&*()-_=+[]{}|;:,<.>/?" for c in password):
        score += 15
    
    # Penalize common patterns
    if any(pattern in password.lower() for pattern in ["password", "admin", "123456"]):
        score -= 20
    
    return min(100, max(0, score))


def is_suspicious_login_pattern(login_history: list, current_ip: str, current_time: datetime) -> bool:
    """
    Detect suspicious login patterns (e.g., impossible travel).
    
    Args:
        login_history: List of recent login records with IP and timestamp
        current_ip: Current login IP
        current_time: Current login time
    
    Returns:
        True if suspicious, False otherwise
    """
    if not login_history:
        return False
    
    # Simple check: if last login was from different IP less than 1 minute ago
    # (would require impossible travel), flag as suspicious
    last_login = login_history[0]
    time_diff = (current_time - datetime.fromisoformat(last_login.get("timestamp", ""))).total_seconds()
    
    if time_diff < 60 and last_login.get("ip") != current_ip:
        return True
    
    return False
