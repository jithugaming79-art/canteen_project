from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from menu.models import MenuItem
from .models import Order, OrderItem
from payments.models import WalletTransaction
from accounts.models import UserProfile, SystemSettings
from canteen.utils import redirect_replace
import logging

logger = logging.getLogger(__name__)

# Cart configuration
MAX_ITEM_QUANTITY = 20  # Maximum quantity per item

# ===== CART FUNCTIONS =====

def get_cart(request):
    """Get cart from session"""
    return request.session.get('cart', {})

def save_cart(request, cart):
    """Save cart to session"""
    request.session['cart'] = cart
    request.session.modified = True

def _cart_json_response(request, cart):
    """Build a JSON response with full cart data"""
    from django.http import JsonResponse
    item_ids = [int(k) for k in cart.keys()]
    items = MenuItem.objects.filter(id__in=item_ids)
    has_veg = False
    has_nonveg = False
    cart_items_data = []
    cart_subtotal = 0
    total_items = 0
    for item in items:
        entry = cart.get(str(item.id), {})
        qty = entry.get('quantity', 1) if isinstance(entry, dict) else int(entry)
        item_total = float(item.price) * qty
        cart_subtotal += item_total
        total_items += qty
        if item.is_vegetarian:
            has_veg = True
        else:
            has_nonveg = True
        cart_items_data.append({
            'id': item.id,
            'name': item.name,
            'qty': qty,
            'price': float(item.price),
            'total': item_total,
            'is_veg': item.is_vegetarian,
            'category': item.category.name if item.category else '',
            'image': item.image.url if item.image else '',
        })
    if has_veg and has_nonveg:
        cart_type = 'mixed'
    elif has_nonveg:
        cart_type = 'nonveg'
    elif has_veg:
        cart_type = 'veg'
    else:
        cart_type = 'empty'
    return JsonResponse({
        'success': True,
        'cart_count': len(cart),
        'total_items': total_items,
        'cart_type': cart_type,
        'cart_items': cart_items_data,
        'cart_subtotal': cart_subtotal,
    })

@login_required
def view_cart(request):
    """Display cart contents"""
    cart = get_cart(request)
    cart_items = []
    total_price = 0
    
    for item_id, data in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            subtotal = item.price * data['quantity']
            cart_items.append({
                'item': item,
                'quantity': data['quantity'],
                'price': item.price,
                'subtotal': subtotal,
            })
            total_price += subtotal
        except MenuItem.DoesNotExist:
            pass
    
    context = {
        'cart': cart_items,
        'total_price': total_price,
        'total_items': sum(d['quantity'] for d in cart.values()),
    }
    return render(request, 'orders/cart.html', context)

@login_required
@require_POST
def add_to_cart(request, item_id):
    """Add item to cart"""
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1
    
    # Validate quantity limits
    quantity = max(1, min(quantity, MAX_ITEM_QUANTITY))
    
    cart = get_cart(request)
    item_id_str = str(item_id)
    
    if item_id_str in cart:
        new_quantity = cart[item_id_str]['quantity'] + quantity
        cart[item_id_str]['quantity'] = min(new_quantity, MAX_ITEM_QUANTITY)
    else:
        cart[item_id_str] = {'quantity': quantity}
    
    save_cart(request, cart)
    
    # AJAX response - return JSON instead of redirect
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax:
        from django.http import JsonResponse
        item_ids = [int(k) for k in cart.keys()]
        items = MenuItem.objects.filter(id__in=item_ids)
        has_veg = False
        has_nonveg = False
        cart_items_data = []
        cart_subtotal = 0
        for item in items:
            entry = cart.get(str(item.id), {})
            qty = entry.get('quantity', 1) if isinstance(entry, dict) else int(entry)
            item_total = float(item.price) * qty
            cart_subtotal += item_total
            if item.is_vegetarian:
                has_veg = True
            else:
                has_nonveg = True
            cart_items_data.append({
                'name': item.name,
                'qty': qty,
                'total': item_total,
                'is_veg': item.is_vegetarian,
            })
        if has_veg and has_nonveg:
            cart_type = 'mixed'
        elif has_nonveg:
            cart_type = 'nonveg'
        else:
            cart_type = 'veg'
        return JsonResponse({
            'success': True,
            'cart_count': len(cart),
            'cart_type': cart_type,
            'cart_items': cart_items_data,
            'cart_subtotal': cart_subtotal,
        })
    
    messages.success(request, 'Item added to cart!')
    next_url = request.POST.get('next', 'menu')
    return redirect(next_url)

@login_required
@require_POST
def remove_from_cart(request, item_id):
    """Remove item from cart - POST only for CSRF protection"""
    cart = get_cart(request)
    item_id_str = str(item_id)
    
    if item_id_str in cart:
        del cart[item_id_str]
        save_cart(request, cart)
    
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax:
        return _cart_json_response(request, cart)
    messages.success(request, 'Item removed from cart')
    return redirect('view_cart')

@login_required
@require_POST
def update_cart(request, item_id):
    """Update item quantity"""
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1
    
    # Apply limits
    quantity = min(quantity, MAX_ITEM_QUANTITY)
    
    cart = get_cart(request)
    item_id_str = str(item_id)
    
    if quantity <= 0:
        if item_id_str in cart:
            del cart[item_id_str]
    else:
        cart[item_id_str] = {'quantity': quantity}
    
    save_cart(request, cart)
    
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if is_ajax:
        return _cart_json_response(request, cart)
    return redirect('view_cart')

@login_required
@require_POST
def clear_cart(request):
    """Empty the cart - POST only for CSRF protection"""
    request.session['cart'] = {}
    request.session.modified = True
    messages.success(request, 'Cart cleared')
    return redirect('view_cart')

# ===== ORDER FUNCTIONS =====

@login_required
def checkout(request):
    """Checkout page"""
    cart = get_cart(request)
    if not cart:
        messages.warning(request, 'Your cart is empty')
        return redirect('menu')
    
    # Check Maintenance Mode
    settings = SystemSettings.get_settings()
    if settings.maintenance_mode:
        messages.error(request, 'The canteen is currently under maintenance. Please try again later.')
        return redirect('menu')
    
    cart_items = []
    total = 0
    total_prep_time = 0
    
    for item_id, data in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            subtotal = item.price * data['quantity']
            cart_items.append({
                'item': item,
                'quantity': data['quantity'],
                'subtotal': subtotal,
            })
            total += subtotal
            total_prep_time = max(total_prep_time, item.preparation_time)
        except MenuItem.DoesNotExist:
            pass
    
    # Calculate estimated wait time
    pending_orders = Order.objects.filter(status__in=['pending', 'confirmed', 'preparing']).count()
    queue_time = pending_orders * 3
    estimated_wait = total_prep_time + queue_time
    
    # Get delivery fee
    try:
        delivery_fee = SystemSettings.get_settings().delivery_fee
    except Exception as e:
        logger.warning(f"Error fetching delivery fee: {e}")
        delivery_fee = 10.00

    context = {
        'cart_items': cart_items,
        'total': total,
        'estimated_wait': estimated_wait,
        'pending_orders': pending_orders,
        'delivery_fee': delivery_fee,
    }
    return render(request, 'orders/checkout.html', context)

@login_required
@transaction.atomic
def place_order(request):
    """Create order from cart"""
    if request.method != 'POST':
        return redirect('checkout')
    
    cart = get_cart(request)
    if not cart:
        messages.error(request, 'Cart is empty')
        return redirect('menu')
    
    # Check Maintenance Mode
    settings = SystemSettings.get_settings()
    if settings.maintenance_mode:
        messages.error(request, 'The canteen is currently under maintenance. Please try again later.')
        return redirect('menu')
    
    payment_method = request.POST.get('payment_method', 'cash')
    special_instructions = request.POST.get('special_instructions', '')
    
    # Delivery options
    delivery_type = request.POST.get('delivery_type', 'pickup')
    delivery_location = request.POST.get('delivery_location', '').strip()
    
    # Validate delivery location for delivery orders
    if delivery_type in ['classroom', 'staffroom'] and not delivery_location:
        messages.error(request, 'Please enter your room number for delivery')
        return redirect('checkout')
    
    # Calculate delivery fee
    settings = SystemSettings.get_settings()
    delivery_fee = settings.delivery_fee if delivery_type in ['classroom', 'staffroom'] else 0
    
    # Handle preorder
    order_timing = request.POST.get('order_timing', 'now')
    scheduled_for = None
    
    if order_timing == 'preorder':
        scheduled_for_str = request.POST.get('scheduled_for')
        if not scheduled_for_str:
            messages.error(request, 'Please select a scheduled time for your preorder.')
            return redirect('checkout')

        from django.utils.dateparse import parse_datetime
        from django.utils import timezone
        import datetime
        
        scheduled_for = parse_datetime(scheduled_for_str)
        if not scheduled_for:
            messages.error(request, 'Invalid scheduled time format. Please try again.')
            return redirect('checkout')

        # Make timezone aware if naive
        if timezone.is_naive(scheduled_for):
            scheduled_for = timezone.make_aware(scheduled_for, timezone.get_current_timezone())
            
        # Basic validation: cannot be in past
        if scheduled_for < timezone.now():
             messages.error(request, 'Preorder time cannot be in the past')
             return redirect('checkout')
             
        # Ensure it's at least 30 mins in future
        if scheduled_for < timezone.now() + datetime.timedelta(minutes=30):
             messages.error(request, 'Please schedule at least 30 minutes in advance')
             return redirect('checkout')

    # Calculate subtotal
    subtotal = 0
    for item_id, data in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            subtotal += item.price * data['quantity']
        except MenuItem.DoesNotExist:
            pass
    
    # Total with delivery fee
    total = subtotal + delivery_fee
    
    # Create order
    order = Order.objects.create(
        user=request.user,
        payment_method=payment_method,
        total_amount=total,
        special_instructions=special_instructions,
        delivery_type=delivery_type,
        delivery_location=delivery_location,
        delivery_fee=delivery_fee,
        scheduled_for=scheduled_for,
    )
    
    # Create order items
    for item_id, data in cart.items():
        try:
            item = MenuItem.objects.get(id=item_id)
            OrderItem.objects.create(
                order=order,
                menu_item=item,
                item_name=item.name,
                price=item.price,
                quantity=data['quantity'],
            )
        except MenuItem.DoesNotExist:
            pass
    
    # Clear cart
    request.session['cart'] = {}
    request.session.modified = True
    
    # Confirmation email deferred until payment completion
    
    # Redirect based on payment method
    if payment_method == 'wallet':
        # Direct wallet debit - no separate payment page
        profile = UserProfile.objects.select_for_update().get(user=request.user)
        if profile.wallet_balance >= total:
            profile.wallet_balance -= total
            profile.save()
            
            WalletTransaction.objects.create(
                user=request.user,
                amount=total,
                transaction_type='debit',
                description=f'Payment for order {order.token_number}',
            )
            
            order.is_paid = True
            order.status = 'confirmed'
            order.save()
            
            messages.success(request, f'₹{total} paid from wallet. Order placed!')
            return redirect_replace(reverse('order_detail', args=[order.id]))
        else:
            # Insufficient balance - cancel the order and redirect back
            order.delete()
            messages.error(request, f'Insufficient wallet balance. You need ₹{total} but have ₹{profile.wallet_balance}.')
            return redirect('checkout')
    elif payment_method == 'online':
        return redirect_replace(reverse('process_online_payment', args=[order.id]))
    else:
        return redirect_replace(reverse('payment_page', args=[order.id]))

@login_required
def order_history(request):
    """Show user's orders with pagination"""

    
    orders_list = Order.objects.filter(user=request.user)
    paginator = Paginator(orders_list, 10)  # 10 orders per page
    
    page = request.GET.get('page')
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)
    
    return render(request, 'orders/order_history.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    """Show order details"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})

@login_required
def order_status_api(request, order_id):
    """Return order status as JSON for AJAX polling"""
    from django.http import JsonResponse
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return JsonResponse({
        'status': order.status,
        'status_display': order.get_status_display(),
    })

@login_required
@require_POST
@transaction.atomic
def cancel_order(request, order_id):
    """Cancel pending order with automatic wallet refund"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status not in ['pending', 'confirmed']:
        messages.error(request, 'Cannot cancel this order - already being prepared')
        return redirect('order_history')
    
    # Process refund if order was paid via wallet
    if order.is_paid and order.payment_method == 'wallet':
        # Lock user profile for atomic update
        profile = UserProfile.objects.select_for_update().get(user=request.user)
        profile.wallet_balance += order.total_amount
        profile.save()
        
        # Record refund transaction
        WalletTransaction.objects.create(
            user=request.user,
            amount=order.total_amount,
            transaction_type='credit',
            description=f'Refund for cancelled order {order.token_number}',
        )
        messages.info(request, f'₹{order.total_amount} refunded to your wallet')
    
    order.status = 'cancelled'
    order.save()
    messages.success(request, 'Order cancelled successfully')
    
    return redirect('order_history')


@login_required
def reorder(request, order_id):
    """Reorder items from a previous order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    cart = get_cart(request)
    items_added = 0
    unavailable_items = []
    
    for order_item in order.items.all():
        if order_item.menu_item and order_item.menu_item.is_available:
            item_id_str = str(order_item.menu_item.id)
            if item_id_str in cart:
                cart[item_id_str]['quantity'] += order_item.quantity
            else:
                cart[item_id_str] = {'quantity': order_item.quantity}
            items_added += order_item.quantity
        else:
            unavailable_items.append(order_item.item_name)
    
    save_cart(request, cart)
    
    if items_added > 0:
        messages.success(request, f'{items_added} items added to cart!')
    if unavailable_items:
        messages.warning(request, f'Some items are unavailable: {", ".join(unavailable_items)}')
    
    return redirect('view_cart')

