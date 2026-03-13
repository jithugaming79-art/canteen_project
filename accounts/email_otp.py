"""
Email OTP Verification Utility.
Generates 6-digit OTP codes, stores them in cache, and sends them via email.
"""
import secrets
import logging
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

OTP_EXPIRY_SECONDS = 600  # 10 minutes
OTP_MAX_ATTEMPTS = 5      # Max wrong attempts before lockout
OTP_RESEND_COOLDOWN = 60  # Seconds between resend requests


def generate_otp():
    # Cryptographically secure 6-digit OTP
    return ''.join([secrets.choice('0123456789') for _ in range(6)])


def _cache_key(email):
    """Return the cache key for storing OTP data for a given email."""
    return f'email_otp_{email.lower().strip()}'


def _attempts_key(email):
    """Return the cache key for tracking wrong OTP attempts."""
    return f'email_otp_attempts_{email.lower().strip()}'


def _resend_key(email):
    """Return the cache key for resend cooldown."""
    return f'email_otp_resend_{email.lower().strip()}'


def store_otp(email, otp):
    """Store OTP in cache with expiry."""
    cache.set(_cache_key(email), otp, OTP_EXPIRY_SECONDS)
    cache.delete(_attempts_key(email))  # Reset attempts on new OTP


def verify_otp(email, entered_otp):
    """
    Verify the entered OTP against the stored one.
    Returns: (success: bool, message: str)
    """
    email = email.lower().strip()
    attempts_key = _attempts_key(email)
    attempts = cache.get(attempts_key, 0)

    if attempts >= OTP_MAX_ATTEMPTS:
        return False, 'Too many wrong attempts. Please request a new code.'

    stored_otp = cache.get(_cache_key(email))

    if stored_otp is None:
        return False, 'Verification code has expired. Please request a new one.'

    if str(entered_otp).strip() == str(stored_otp):
        # Success — clear OTP and attempts
        cache.delete(_cache_key(email))
        cache.delete(attempts_key)
        return True, 'Email verified successfully!'

    # Wrong OTP
    cache.set(attempts_key, attempts + 1, OTP_EXPIRY_SECONDS)
    remaining = OTP_MAX_ATTEMPTS - (attempts + 1)
    return False, f'Invalid code. {remaining} attempt(s) remaining.'


def can_resend(email):
    """Check if resend cooldown has passed."""
    return cache.get(_resend_key(email)) is None


def mark_resend(email):
    """Set resend cooldown."""
    cache.set(_resend_key(email), True, OTP_RESEND_COOLDOWN)


def send_otp_email(email, otp):
    """
    Send the OTP code to the user's email.
    Uses Django's email backend (SMTP in production, console in dev).
    """
    subject = 'CampusBites \u2014 Verify Your Email'
    message = (
        f'Hi there!\n\n'
        f'Your CampusBites verification code is:\n\n'
        f'    {otp}\n\n'
        f'This code is valid for 10 minutes. '
        f'Do not share this code with anyone.\n\n'
        f'If you did not register on CampusBites, please ignore this email.\n\n'
        f'\u2014 Team CampusBites'
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@campusbites.com')

    try:
        send_mail(subject, message, from_email, [email], fail_silently=False)
        logger.info(f"OTP email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {e}")
        return False


# ─── Password Reset OTP (separate cache keys) ───────────────────────────

def _pw_cache_key(email):
    """Cache key for password reset OTP."""
    return f'pw_reset_otp_{email.lower().strip()}'


def _pw_attempts_key(email):
    """Cache key for password reset OTP wrong attempt count."""
    return f'pw_reset_attempts_{email.lower().strip()}'


def _pw_resend_key(email):
    """Cache key for password reset OTP resend cooldown."""
    return f'pw_reset_resend_{email.lower().strip()}'


def store_pw_reset_otp(email, otp):
    """Store password reset OTP in cache with expiry."""
    cache.set(_pw_cache_key(email), otp, OTP_EXPIRY_SECONDS)
    cache.delete(_pw_attempts_key(email))


def verify_pw_reset_otp(email, entered_otp):
    """
    Verify password reset OTP.
    Returns: (success: bool, message: str)
    """
    email = email.lower().strip()
    attempts_key = _pw_attempts_key(email)
    attempts = cache.get(attempts_key, 0)

    if attempts >= OTP_MAX_ATTEMPTS:
        return False, 'Too many wrong attempts. Please request a new code.'

    stored_otp = cache.get(_pw_cache_key(email))

    if stored_otp is None:
        return False, 'Verification code has expired. Please request a new one.'

    if str(entered_otp).strip() == str(stored_otp):
        cache.delete(_pw_cache_key(email))
        cache.delete(attempts_key)
        return True, 'Code verified successfully!'

    cache.set(attempts_key, attempts + 1, OTP_EXPIRY_SECONDS)
    remaining = OTP_MAX_ATTEMPTS - (attempts + 1)
    return False, f'Invalid code. {remaining} attempt(s) remaining.'


def can_resend_pw_reset(email):
    """Check if password reset OTP resend cooldown has passed."""
    return cache.get(_pw_resend_key(email)) is None


def mark_resend_pw_reset(email):
    """Set password reset OTP resend cooldown."""
    cache.set(_pw_resend_key(email), True, OTP_RESEND_COOLDOWN)


def send_pw_reset_otp_email(email, otp):
    """Send password reset OTP to user's email."""
    subject = 'CampusBites — Reset Your Password'
    message = (
        f'Hi there!\n\n'
        f'You requested to reset your CampusBites password.\n\n'
        f'Your password reset code is:\n\n'
        f'    {otp}\n\n'
        f'This code is valid for 10 minutes. '
        f'Do not share this code with anyone.\n\n'
        f'If you did not request a password reset, please ignore this email.\n\n'
        f'— Team CampusBites'
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@campusbites.com')

    try:
        send_mail(subject, message, from_email, [email], fail_silently=False)
        logger.info(f"Password reset OTP sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset OTP to {email}: {e}")
        return False

