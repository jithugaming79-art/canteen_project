"""
Self-Contained Phone OTP Authentication Backend.

Generates and verifies 6-digit OTPs using Django's cache.
No external service required — fully free.
In production, plug in an SMS gateway (Twilio, MSG91, etc.)
to send OTPs via SMS. For development, the OTP is returned
to the frontend and shown as a toast.
"""
import secrets
import logging
from django.core.cache import cache
from django.contrib.auth.models import User
from accounts.models import UserProfile

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────
OTP_LENGTH = 6
OTP_EXPIRY = 300            # 5 minutes
MAX_OTP_REQUESTS = 5        # Max requests per phone per window
OTP_RATE_WINDOW = 600       # 10 minutes
MAX_VERIFY_ATTEMPTS = 5     # Max wrong OTP attempts before lockout


def _cache_key(phone, suffix):
    return f'phone_otp_{suffix}_{phone}'


# ── Rate Limiting ──────────────────────────────────────
def check_phone_rate_limit(phone):
    """Return True if this phone is allowed to request an OTP."""
    key = _cache_key(phone, 'rate')
    attempts = cache.get(key, 0)
    if attempts >= MAX_OTP_REQUESTS:
        return False
    cache.set(key, attempts + 1, OTP_RATE_WINDOW)
    return True


# ── OTP Generation ─────────────────────────────────────
def generate_otp(phone):
    """
    Generate a 6-digit OTP, store it in cache, return it.
    In production, send via SMS here instead of returning.
    """
    otp = ''.join([secrets.choice('0123456789') for _ in range(OTP_LENGTH)])

    # Store OTP in cache
    cache.set(_cache_key(phone, 'code'), otp, OTP_EXPIRY)
    # Reset verify attempts
    cache.set(_cache_key(phone, 'verify_attempts'), 0, OTP_EXPIRY)

    # Mask phone number to prevent exposing PII in logs
    masked_phone = f"{phone[:3]}****{phone[-3:]}" if len(phone) >= 6 else "****"
    logger.info(f"OTP generated for {masked_phone}")
    return otp


# ── OTP Verification ──────────────────────────────────
def verify_otp(phone, otp):
    """
    Verify the user-supplied OTP against the cached one.
    Returns (success: bool, error_message: str | None)
    """
    # Check verify attempt count
    attempts_key = _cache_key(phone, 'verify_attempts')
    attempts = cache.get(attempts_key, 0)
    if attempts >= MAX_VERIFY_ATTEMPTS:
        return False, 'Too many wrong attempts. Please request a new OTP.'

    stored_otp = cache.get(_cache_key(phone, 'code'))

    if stored_otp is None:
        return False, 'OTP expired. Please request a new one.'

    if otp != stored_otp:
        cache.set(attempts_key, attempts + 1, OTP_EXPIRY)
        remaining = MAX_VERIFY_ATTEMPTS - attempts - 1
        return False, f'Invalid OTP. {remaining} attempt(s) remaining.'

    # Success — clear the OTP so it can't be reused
    cache.delete(_cache_key(phone, 'code'))
    cache.delete(attempts_key)
    return True, None


# ── User Lookup / Creation ─────────────────────────────
def get_or_create_user_by_phone(phone):
    """
    Find existing user by phone number, or create a new one.
    Returns (user, created) tuple.
    """
    # Normalize: strip +91, spaces, keep last 10 digits
    clean_phone = phone.replace('+91', '').replace(' ', '').strip()
    if len(clean_phone) > 10:
        clean_phone = clean_phone[-10:]

    # Try to find existing user
    try:
        profile = UserProfile.objects.filter(phone=clean_phone).first()
        if profile:
            return profile.user, False
    except Exception:
        pass

    # Create new user
    username = f'phone_{clean_phone}'
    counter = 0
    base_username = username
    while User.objects.filter(username=username).exists():
        counter += 1
        username = f'{base_username}_{counter}'

    user = User.objects.create_user(
        username=username,
        password=None,   # No password for phone-only users
    )
    user.profile.phone = clean_phone
    user.profile.role = 'student'
    user.profile.save()

    logger.info(f"Created new user via phone auth: {username}")
    return user, True
