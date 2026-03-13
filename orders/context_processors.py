from menu.models import MenuItem


def cart_type_processor(request):
    """Determine if cart contains veg, non-veg, mixed, or is empty. Also provide cart details for dropdown."""
    cart = request.session.get('cart', {})
    if not cart:
        return {'cart_type': 'empty', 'cart_items': [], 'cart_subtotal': 0}

    item_ids = [int(k) for k in cart.keys()]
    items = MenuItem.objects.filter(id__in=item_ids)

    has_veg = False
    has_nonveg = False
    cart_items = []
    cart_subtotal = 0

    for item in items:
        cart_entry = cart.get(str(item.id), {})
        # Cart stores {'quantity': N} dicts
        if isinstance(cart_entry, dict):
            qty = cart_entry.get('quantity', 1)
        else:
            qty = int(cart_entry)
        item_total = float(item.price) * qty
        cart_subtotal += item_total
        if item.is_vegetarian:
            has_veg = True
        else:
            has_nonveg = True
        cart_items.append({
            'id': item.id,
            'name': item.name,
            'price': float(item.price),
            'qty': qty,
            'total': item_total,
            'image': item.image if item.image else None,
            'is_veg': item.is_vegetarian,
        })

    # Determine cart type: mixed (both veg+nonveg), nonveg only, or veg only
    if has_veg and has_nonveg:
        cart_type = 'mixed'
    elif has_nonveg:
        cart_type = 'nonveg'
    else:
        cart_type = 'veg'

    return {
        'cart_type': cart_type,
        'cart_items': cart_items,
        'cart_subtotal': cart_subtotal,
    }
