"""Shared menu service functions to avoid code duplication."""
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from menu.models import MenuItem

logger = logging.getLogger(__name__)


def toggle_menu_item_availability(item_id):
    """Toggle a menu item's availability and broadcast via WebSocket.
    
    Returns:
        tuple: (success: bool, item: MenuItem or None, message: str)
    """
    try:
        item = MenuItem.objects.get(id=item_id)
        item.is_available = not item.is_available
        item.save()

        # Broadcast update via WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'menu_updates',
            {
                'type': 'menu_update',
                'item_id': item.id,
                'is_available': item.is_available,
                'item_name': item.name
            }
        )

        status = "Available" if item.is_available else "Out of Stock"
        logger.info(f"Menu item '{item.name}' toggled to {status}")
        return True, item, f'{item.name} is now {status}'

    except MenuItem.DoesNotExist:
        logger.warning(f"Menu toggle failed: item_id={item_id} not found")
        return False, None, 'Item not found'
