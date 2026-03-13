"""Email notification utilities for order updates"""
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def send_order_confirmation_email(order):
    """Send email when order is placed"""
    if not order.user.email:
        return False
    
    subject = f'Order Confirmed - {order.token_number}'
    
    # Create HTML message
    message = f"""
Hi {order.user.username}!

Your order has been confirmed!

Order Token: {order.token_number}
Total: ₹{order.total_amount}
Payment Method: {order.get_payment_method_display()}

Items:
"""
    for item in order.items.all():
        message += f"  • {item.quantity}x {item.item_name} - ₹{item.get_subtotal()}\n"
    
    message += f"""
{f'Special Instructions: ' + order.special_instructions if order.special_instructions else ''}

Thank you for ordering with CampusBites!
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f'Failed to send order confirmation email for {order.token_number}: {e}')
        return False


def send_order_ready_email(order):
    """Send email when order is ready for pickup"""
    if not order.user.email:
        return False
    
    subject = f'🔔 Order Ready - {order.token_number}'
    
    message = f"""
Hi {order.user.username}!

Great news! Your order is READY for pickup!

Order Token: {order.token_number}

Please head to the counter and show your token number or QR code.

Thank you for ordering with CampusBites!
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f'Failed to send order ready email for {order.token_number}: {e}')
        return False

