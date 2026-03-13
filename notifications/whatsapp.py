"""
WhatsApp messaging service with dual provider support.

Primary: Meta WhatsApp Cloud API
Backup: Twilio WhatsApp Sandbox

Falls back to dry-run mode (console logging) when no credentials are configured.
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://graph.facebook.com/v21.0"


# ─── Provider Detection ──────────────────────────────────────────────

def _meta_is_configured():
    """Check if Meta WhatsApp Cloud API credentials are set and valid."""
    token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')
    phone_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
    return bool(token and phone_id and token != 'your_token_here')


def _twilio_is_configured():
    """Check if Twilio credentials are set."""
    sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    return bool(sid and token and sid != 'your_sid_here')


def _get_provider():
    """Determine which provider to use. Returns 'meta', 'twilio', or 'dry_run'."""
    if _meta_is_configured():
        return 'meta'
    if _twilio_is_configured():
        return 'twilio'
    return 'dry_run'


# ─── Phone Formatting ────────────────────────────────────────────────

def _format_phone(phone):
    """Format phone number to international format (E.164). Assumes Indian numbers."""
    phone = phone.strip().replace(' ', '').replace('-', '')
    if phone.startswith('+'):
        return phone.lstrip('+')
    if phone.startswith('0'):
        phone = phone[1:]
    if len(phone) == 10:
        return f"91{phone}"
    return phone


def _format_phone_e164(phone):
    """Format phone to +XXXXXXXXXXX format for Twilio."""
    digits = _format_phone(phone)
    return f"+{digits}"


# ─── Meta WhatsApp Cloud API ─────────────────────────────────────────

def _meta_send_template(phone, template_name, template_params=None, header_image_url=None):
    """Send a template message via Meta Cloud API."""
    formatted_phone = _format_phone(phone)

    components = []
    if header_image_url:
        components.append({
            "type": "header",
            "parameters": [{"type": "image", "image": {"link": header_image_url}}]
        })
    if template_params:
        body_params = [{"type": "text", "text": str(p)} for p in template_params]
        components.append({"type": "body", "parameters": body_params})

    payload = {
        "messaging_product": "whatsapp",
        "to": formatted_phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en_US"},
        }
    }
    if components:
        payload["template"]["components"] = components

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    url = f"{WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        if response.status_code == 200 and 'messages' in data:
            msg_id = data['messages'][0].get('id', '')
            logger.info(f"[META] WhatsApp sent to +{formatted_phone}: {msg_id}")
            return {'success': True, 'message_id': msg_id, 'error': ''}
        else:
            error = data.get('error', {}).get('message', str(data))
            logger.error(f"[META] WhatsApp failed for +{formatted_phone}: {error}")
            return {'success': False, 'message_id': '', 'error': error}
    except requests.RequestException as e:
        logger.error(f"[META] Request error for +{formatted_phone}: {e}")
        return {'success': False, 'message_id': '', 'error': str(e)}


# ─── Twilio WhatsApp ─────────────────────────────────────────────────

def _twilio_send_message(phone, message_text):
    """Send a WhatsApp message via Twilio."""
    from twilio.rest import Client

    formatted_phone = _format_phone_e164(phone)
    twilio_number = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', '+14155238886')

    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=message_text,
            from_=f"whatsapp:{twilio_number}",
            to=f"whatsapp:{formatted_phone}"
        )
        logger.info(f"[TWILIO] WhatsApp sent to {formatted_phone}: {message.sid}")
        return {'success': True, 'message_id': message.sid, 'error': ''}
    except Exception as e:
        logger.error(f"[TWILIO] WhatsApp failed for {formatted_phone}: {e}")
        return {'success': False, 'message_id': '', 'error': str(e)}


# ─── Unified Send Functions ──────────────────────────────────────────

def send_template_message(phone, template_name, template_params=None, header_image_url=None):
    """
    Send a WhatsApp message. Tries Meta Cloud API first, falls back to Twilio, then dry-run.
    """
    provider = _get_provider()
    formatted_phone = _format_phone(phone)

    if provider == 'dry_run':
        logger.info(
            f"[DRY RUN] WhatsApp message to +{formatted_phone}\n"
            f"  Template: {template_name}\n"
            f"  Params: {template_params}\n"
            f"  Image: {header_image_url}"
        )
        return {'success': True, 'message_id': f'dry_run_{formatted_phone}', 'error': ''}

    if provider == 'meta':
        result = _meta_send_template(phone, template_name, template_params, header_image_url)
        # If Meta fails (e.g. restricted account), try Twilio as fallback
        if not result['success'] and _twilio_is_configured():
            logger.info(f"[FALLBACK] Meta failed, trying Twilio for +{formatted_phone}")
            message_text = _build_offer_text(template_params)
            return _twilio_send_message(phone, message_text)
        return result

    if provider == 'twilio':
        message_text = _build_offer_text(template_params)
        return _twilio_send_message(phone, message_text)


def send_text_message(phone, message_text):
    """Send a plain text WhatsApp message."""
    provider = _get_provider()
    formatted_phone = _format_phone(phone)

    if provider == 'dry_run':
        logger.info(f"[DRY RUN] WhatsApp text to +{formatted_phone}: {message_text}")
        return {'success': True, 'message_id': f'dry_run_{formatted_phone}', 'error': ''}

    if provider == 'twilio' or (provider == 'meta' and _twilio_is_configured()):
        return _twilio_send_message(phone, message_text)

    # Meta text message (only within 24h window)
    payload = {
        "messaging_product": "whatsapp",
        "to": formatted_phone,
        "type": "text",
        "text": {"body": message_text}
    }
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    url = f"{WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        data = response.json()
        if response.status_code == 200 and 'messages' in data:
            msg_id = data['messages'][0].get('id', '')
            return {'success': True, 'message_id': msg_id, 'error': ''}
        else:
            error = data.get('error', {}).get('message', str(data))
            return {'success': False, 'message_id': '', 'error': error}
    except requests.RequestException as e:
        return {'success': False, 'message_id': '', 'error': str(e)}


# ─── Helper ──────────────────────────────────────────────────────────

def _build_offer_text(template_params):
    """Build a plain text offer message from template parameters."""
    if not template_params or len(template_params) < 4:
        return "🎉 Check out our latest offer on CampusBites!"

    title, description, code, valid_until = template_params[:4]
    return (
        f"🎉 *{title}*\n\n"
        f"{description}\n\n"
        f"🎫 Code: {code}\n"
        f"⏰ Valid until: {valid_until}\n\n"
        f"Order now on CampusBites! 🍔"
    )


# ─── Bulk Send ───────────────────────────────────────────────────────

def send_offer_to_users(offer, users_queryset=None):
    """Send an offer notification to all opted-in users."""
    from accounts.models import UserProfile
    from .models import WhatsAppLog

    if users_queryset is None:
        profiles = UserProfile.objects.filter(
            whatsapp_opt_in=True,
        ).exclude(phone='').select_related('user')
    else:
        profiles = UserProfile.objects.filter(
            user__in=users_queryset,
            whatsapp_opt_in=True,
        ).exclude(phone='').select_related('user')

    results = {'sent': 0, 'failed': 0, 'skipped': 0}
    provider = _get_provider()
    template_name = getattr(settings, 'WHATSAPP_OFFER_TEMPLATE', 'campus_bites_offer')

    for profile in profiles:

        # Build image URL
        image_url = None
        if offer.image:
            image_url = offer.image.url
            if not image_url.startswith('http'):
                image_url = None

        result = send_template_message(
            phone=profile.phone,
            template_name=template_name,
            template_params=[
                offer.title,
                offer.description,
                offer.discount_code or 'No code needed',
                offer.valid_until.strftime('%d %b %Y, %I:%M %p'),
            ],
            header_image_url=image_url,
        )

        # Determine status
        if provider == 'dry_run':
            status = 'dry_run'
        elif result['success']:
            status = 'sent'
        else:
            status = 'failed'

        WhatsAppLog.objects.create(
            offer=offer,
            user=profile.user,
            phone=profile.phone,
            status=status,
            whatsapp_message_id=result.get('message_id', ''),
            error_message=result.get('error', ''),
        )

        if result['success']:
            results['sent'] += 1
        else:
            results['failed'] += 1

    return results
