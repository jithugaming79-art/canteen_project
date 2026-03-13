from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Order)
def order_updated_signal(sender, instance, created, **kwargs):
    """Notify kitchen when order is created or status changes"""
    logger.info(f"Order #{instance.id} signal: created={created}, status={instance.status}")
    
    # Don't notify kitchen for payment_pending orders (not yet paid)
    if instance.status == 'payment_pending':
        return
    
    channel_layer = get_channel_layer()
    
    # Prepare data for WebSocket
    data = {
        'id': instance.id,
        'token': instance.token_number,
        'status': instance.status,
        'items': [{'name': item.item_name, 'qty': item.quantity} for item in instance.items.all()],
        'special_instructions': instance.special_instructions,
        'created_at': instance.created_at.strftime("%Y-%m-%dT%H:%M:%S"),
        'delivery_type': instance.delivery_type,
        'delivery_location': instance.delivery_location,
        'new_order': not created and instance.status in ['pending', 'confirmed']
    }
    
    # Send message to kitchen group
    async_to_sync(channel_layer.group_send)(
        'kitchen_group',
        {
            'type': 'order_update',
            'message': 'New Order' if data['new_order'] else 'Order Updated',
            'data': data
        }
    )
