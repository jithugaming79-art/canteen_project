"""Admin Dashboard Views — Campus Bites"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count, F, Avg, DecimalField, ExpressionWrapper, Case, When, Value, BooleanField, CharField
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
import csv
import decimal

from menu.models import MenuItem, Category, Review
from orders.models import Order, OrderItem
from .models import UserProfile, SystemSettings, Feedback


def admin_required(view_func):
    """Decorator: require admin role"""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'user') or not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
            messages.error(request, 'Access denied. Admin only.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    wrapper.__doc__ = view_func.__doc__
    return wrapper

def admin_or_kitchen_required(view_func):
    """Decorator: require admin OR kitchen role"""
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'user') or not hasattr(request.user, 'profile'):
            messages.error(request, 'Access denied. Staff only.')
            return redirect('home')
            
        role = request.user.profile.role
        is_admin = request.user.profile.is_admin
        
        if not is_admin and role != 'kitchen':
            messages.error(request, 'Access denied. Kitchen or Admin staff only.')
            return redirect('home')
            
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    wrapper.__doc__ = view_func.__doc__
    return wrapper


# ───────────────────────────────────────
# Overview / Dashboard
# ───────────────────────────────────────
@admin_required
def admin_overview(request):
    # Use local time for start-of-day calculations
    now = timezone.localtime(timezone.now())
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    time_range = request.GET.get('range', 'all')

    if time_range == '7days':
        start_date = today_start - timedelta(days=7)
    elif time_range == '30days':
        start_date = today_start - timedelta(days=30)
    elif time_range == 'today':
        start_date = today_start
    else:
        start_date = None
        time_range = 'all'

    # Base querysets
    orders_qs = Order.objects.exclude(status='payment_pending')
    if start_date:
        orders_qs = orders_qs.filter(created_at__gte=start_date)

    paid_orders = orders_qs.filter(is_paid=True)
    total_revenue = paid_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = orders_qs.count()
    active_orders = Order.objects.filter(
        status__in=['pending', 'confirmed', 'preparing', 'ready']
    ).count()
    total_users = User.objects.filter(is_active=True).count()

    # Today deltas
    todays_revenue = Order.objects.filter(
        created_at__gte=today_start, is_paid=True
    ).exclude(status='payment_pending').aggregate(total=Sum('total_amount'))['total'] or 0
    todays_orders = Order.objects.filter(
        created_at__gte=today_start
    ).exclude(status='payment_pending').count()

    # New users (last 7 days)
    week_ago = today_start - timedelta(days=7)
    new_users = User.objects.filter(date_joined__gte=week_ago).count()

    # Recent orders (5)
    recent_orders = Order.objects.exclude(
        status='payment_pending'
    ).select_related('user').prefetch_related('items')[:5]

    # Top sellers
    valid_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'delivered', 'collected']
    if start_date:
        top_items_qs = OrderItem.objects.filter(
            order__status__in=valid_statuses,
            order__created_at__gte=start_date,
        )
    else:
        top_items_qs = OrderItem.objects.filter(order__status__in=valid_statuses)

    top_sellers = (
        top_items_qs
        .values('item_name')
        .annotate(
            qty=Sum('quantity'),
            revenue=Sum(ExpressionWrapper(
                F('price') * F('quantity'),
                output_field=DecimalField()
            ))
        )
        .order_by('-qty')[:5]
    )

    context = {
        'time_range': time_range,
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'active_orders': active_orders,
        'total_users': total_users,
        'todays_revenue': todays_revenue,
        'todays_orders': todays_orders,
        'new_users': new_users,
        'recent_orders': recent_orders,
        'top_sellers': top_sellers,
        'active_page': 'overview',
    }
    return render(request, 'admin/admin_overview.html', context)


# ───────────────────────────────────────
# Orders Management
# ───────────────────────────────────────
@admin_or_kitchen_required
def admin_orders(request):
    # Handle bulk action
    if request.method == 'POST' and 'bulk_action' in request.POST:
        order_ids = request.POST.getlist('order_ids')
        action = request.POST.get('bulk_action')
        if order_ids and action:
            updated = 0
            for oid in order_ids:
                try:
                    order = Order.objects.get(id=oid)
                    if action == 'cancel':
                        order.status = 'cancelled'
                    else:
                        order.status = action
                    if action == 'collected':
                        order.is_paid = True
                    order.save()
                    updated += 1
                except Order.DoesNotExist:
                    continue
            messages.success(request, f'{updated} orders updated to {action}')
        return redirect('custom_admin_orders')

    # Handle single status update
    if request.method == 'POST' and 'order_id' in request.POST:
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('status')
        try:
            order = Order.objects.get(id=order_id)
            order.status = new_status
            if new_status == 'collected':
                order.is_paid = True
            order.save()
            messages.success(request, f'Order {order.token_number} → {new_status}')
        except Order.DoesNotExist:
            messages.error(request, 'Order not found')
        return redirect('custom_admin_orders')

    # Filter
    status_filter = request.GET.get('status', 'all')
    search = request.GET.get('search', '').strip()

    orders_qs = Order.objects.exclude(status='payment_pending').select_related('user').prefetch_related('items')

    if search:
        orders_qs = orders_qs.filter(
            Q(token_number__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search)
        )

    if status_filter == 'pending':
        orders_qs = orders_qs.filter(status__in=['pending', 'confirmed'])
    elif status_filter == 'preparing':
        orders_qs = orders_qs.filter(status='preparing')
    elif status_filter == 'ready':
        orders_qs = orders_qs.filter(status='ready')
    elif status_filter == 'completed':
        orders_qs = orders_qs.filter(status__in=['delivered', 'collected'])
    # else: all

    orders_qs = orders_qs.order_by('-created_at')

    # Pagination
    paginator = Paginator(orders_qs, 15)
    page = request.GET.get('page')
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        orders = paginator.page(1)
    except EmptyPage:
        orders = paginator.page(paginator.num_pages)

    # Counts
    base = Order.objects.exclude(status='payment_pending')
    counts = {
        'all': base.count(),
        'pending': base.filter(status__in=['pending', 'confirmed']).count(),
        'preparing': base.filter(status='preparing').count(),
        'ready': base.filter(status='ready').count(),
        'completed': base.filter(status__in=['delivered', 'collected']).count(),
    }

    context = {
        'orders': orders,
        'status_filter': status_filter,
        'search': search,
        'counts': counts,
        'active_page': 'orders',
    }
    return render(request, 'admin/admin_orders.html', context)


@admin_required
def admin_orders_export(request):
    """Export orders as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order ID', 'Customer', 'Email', 'Items', 'Total', 'Status', 'Payment', 'Date'])

    orders = Order.objects.exclude(status='payment_pending').select_related('user').prefetch_related('items').order_by('-created_at')

    for order in orders:
        items_str = ', '.join([f"{oi.quantity}x {oi.item_name}" for oi in order.items.all()])
        writer.writerow([
            order.token_number,
            order.user.username,
            order.user.email,
            items_str,
            float(order.total_amount),
            order.get_status_display(),
            order.get_payment_method_display(),
            order.created_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response


# ───────────────────────────────────────
# Menu Management
# ───────────────────────────────────────
@admin_or_kitchen_required
def admin_menu(request):
    # Toggle availability
    if request.method == 'POST' and 'toggle_item' in request.POST:
        item_id = request.POST.get('item_id')
        try:
            item = MenuItem.objects.get(id=item_id)
            item.is_available = not item.is_available
            item.save()
            messages.success(request, f'{item.name} → {"Available" if item.is_available else "Unavailable"}')
        except MenuItem.DoesNotExist:
            messages.error(request, 'Item not found')
        return redirect('custom_admin_menu')

    # Delete item
    if request.method == 'POST' and 'delete_item' in request.POST:
        item_id = request.POST.get('item_id')
        try:
            item = MenuItem.objects.get(id=item_id)
            name = item.name
            item.delete()
            messages.success(request, f'{name} deleted')
        except MenuItem.DoesNotExist:
            messages.error(request, 'Item not found')
        return redirect('custom_admin_menu')

    # Add item
    if request.method == 'POST' and 'add_item' in request.POST:
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        price = request.POST.get('price', '0')
        is_veg = request.POST.get('is_vegetarian') == 'on'
        prep_time = request.POST.get('preparation_time', '10')
        description = request.POST.get('description', '')
        image = request.FILES.get('image')

        try:
            category = Category.objects.get(id=category_id)
            
            try:
                validated_price = decimal.Decimal(price)
            except decimal.InvalidOperation:
                raise ValueError("Invalid price format") from None
                
            try:
                validated_prep_time = int(prep_time)
            except ValueError:
                validated_prep_time = 10
                
            item = MenuItem.objects.create(
                name=name,
                category=category,
                price=validated_price,
                is_vegetarian=is_veg,
                preparation_time=validated_prep_time,
                description=description,
                image=image,
            )
            messages.success(request, f'{item.name} added!')
        except (Category.DoesNotExist, Exception) as e:
            messages.error(request, f'Error: {e}')
        return redirect('custom_admin_menu')

    # Edit item
    if request.method == 'POST' and 'edit_item' in request.POST:
        item_id = request.POST.get('item_id')
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        price = request.POST.get('price', '0')
        is_veg = request.POST.get('is_vegetarian') == 'on'
        prep_time = request.POST.get('preparation_time', '10')
        description = request.POST.get('description', '')
        image = request.FILES.get('image')

        try:
            item = MenuItem.objects.get(id=item_id)
            if category_id:
                category = Category.objects.get(id=category_id)
                item.category = category
            if name:
                item.name = name
            try:
                item.price = decimal.Decimal(price)
            except decimal.InvalidOperation:
                raise ValueError("Invalid price format") from None
                
            item.is_vegetarian = is_veg
            
            try:
                item.preparation_time = int(prep_time)
            except ValueError:
                item.preparation_time = 10  # Safe default
            item.description = description
            if image:
                item.image = image
            item.save()
            messages.success(request, f'{item.name} updated successfully!')
        except (MenuItem.DoesNotExist, Category.DoesNotExist, Exception) as e:
            messages.error(request, f'Error: {e}')
        return redirect('custom_admin_menu')

    # Filter
    category_filter = request.GET.get('category', 'all')
    categories = Category.objects.filter(is_active=True)
    items = MenuItem.objects.select_related('category').order_by('category__name', 'name')

    if category_filter != 'all':
        items = items.filter(category__name__iexact=category_filter)

    context = {
        'items': items,
        'categories': categories,
        'category_filter': category_filter,
        'active_page': 'menu',
    }
    return render(request, 'admin/admin_menu.html', context)


# ───────────────────────────────────────
# Users Management
# ───────────────────────────────────────
@admin_required
def admin_users(request):
    search = request.GET.get('search', '').strip()

    users_qs = User.objects.select_related('profile').annotate(
        order_count=Count('orders', distinct=True),
        total_spent=Sum('orders__total_amount', filter=Q(orders__is_paid=True)),

        checked_str=Case(
            When(is_active=True, then=Value('checked')),
            default=Value(''),
            output_field=CharField(),
        ),
        disabled_str=Case(
            When(id=request.user.id, then=Value('disabled')),
            default=Value(''),
            output_field=CharField(),
        ),
    ).order_by('-date_joined')

    if search:
        users_qs = users_qs.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(profile__full_name__icontains=search)
        )

    # Pagination
    paginator = Paginator(users_qs, 20)
    page = request.GET.get('page')
    try:
        users = paginator.page(page)
    except PageNotAnInteger:
        users = paginator.page(1)
    except EmptyPage:
        users = paginator.page(paginator.num_pages)

    context = {
        'users': users,
        'search': search,
        'active_page': 'users',
    }
    return render(request, 'admin/admin_users.html', context)


@admin_required
def admin_users_api(request):
    """API for user management actions"""
    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')

        try:
            user = User.objects.get(id=user_id)
            
            # Prevent self-modification
            if user == request.user:
                return JsonResponse({'success': False, 'message': 'Cannot modify your own account'}, status=400)

            if action == 'toggle_status':
                user.is_active = not user.is_active
                user.save()
                status_text = 'Active' if user.is_active else 'Inactive'
                return JsonResponse({'success': True, 'status': status_text, 'is_active': user.is_active})
            
            elif action == 'delete':
                username = user.username
                user.delete()
                return JsonResponse({'success': True, 'message': f'User {username} deleted'})

            return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)

        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ───────────────────────────────────────
# Feedback
# ───────────────────────────────────────
@admin_required
def admin_feedback(request):
    # Handle status update
    if request.method == 'POST' and 'feedback_id' in request.POST:
        fb_id = request.POST.get('feedback_id')
        new_status = request.POST.get('status')
        admin_response = request.POST.get('admin_response', '')
        try:
            fb = Feedback.objects.get(id=fb_id)
            if new_status:
                if fb.can_transition_to(new_status):
                    fb.status = new_status
                else:
                    messages.error(request, f'Invalid status transition from {fb.status} to {new_status}')
                    return redirect('custom_admin_feedback')
            if admin_response:
                fb.admin_response = admin_response
            fb.save()
            messages.success(request, 'Feedback updated')
        except Feedback.DoesNotExist:
            messages.error(request, 'Feedback not found')
        return redirect('custom_admin_feedback')

    # Handle review response
    if request.method == 'POST' and 'review_id' in request.POST:
        review_id = request.POST.get('review_id')
        admin_response = request.POST.get('admin_response', '')
        try:
            review = Review.objects.get(id=review_id)
            if admin_response:
                review.admin_response = admin_response
                review.save()
                messages.success(request, 'Review response saved')
        except Review.DoesNotExist:
            messages.error(request, 'Review not found')
        return redirect('custom_admin_feedback')

    status_filter = request.GET.get('status', 'all')
    feedback_qs = Feedback.objects.select_related('user')

    if status_filter != 'all':
        feedback_qs = feedback_qs.filter(status=status_filter)

    # Also get recent reviews
    reviews = Review.objects.select_related('user', 'menu_item').order_by('-created_at')[:20]

    context = {
        'feedbacks': feedback_qs,
        'reviews': reviews,
        'status_filter': status_filter,
        'active_page': 'feedback',
    }
    return render(request, 'admin/admin_feedback.html', context)


# ───────────────────────────────────────
# Global Settings
# ───────────────────────────────────────
@admin_required
def admin_settings(request):
    settings = SystemSettings.get_settings()

    if request.method == 'POST':
        delivery_fee = request.POST.get('delivery_fee', settings.delivery_fee)
        maintenance_mode = request.POST.get('maintenance_mode') == 'on'

        settings.delivery_fee = delivery_fee
        settings.maintenance_mode = maintenance_mode
        settings.save()
        messages.success(request, 'Settings updated successfully!')
        return redirect('custom_admin_settings')

    context = {
        'settings': settings,
        'active_page': 'settings',
    }
    return render(request, 'admin/admin_settings.html', context)


# ───────────────────────────────────────
# Chart Data API
# ───────────────────────────────────────
@login_required
def admin_chart_data(request):
    """API endpoint for dashboard charts (Rate Limited)"""
    if not request.user.profile.is_admin:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    # Rate limit: max 60 requests per minute per admin
    cache_key = f'admin_api_limit_{request.user.id}'
    requests = cache.get(cache_key, 0)
    if requests > 60:
        return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
    cache.set(cache_key, requests + 1, 60)
    time_range = request.GET.get('range', 'all')
    now = timezone.localtime(timezone.now())
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if time_range == '7days':
        start_date = today_start - timedelta(days=7)
    elif time_range == '30days':
        start_date = today_start - timedelta(days=30)
    elif time_range == 'all':
        start_date = None
    else:
        start_date = today_start

    # Valid statuses for chart data (includes all active orders)
    chart_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'delivered', 'collected']
    base = Order.objects.exclude(status='payment_pending')
    if start_date:
        base = base.filter(created_at__gte=start_date)
    
    # Orders to include in charts (both paid and unpaid, for quantity stats)
    chart_orders = base.filter(status__in=chart_statuses)

    # Hourly / Daily trend (Revenue)
    # Perform aggregation in Python to avoid MySQL timezone issues
    # Only count Valid PAID orders for revenue trend
    revenue_orders = base.filter(is_paid=True).values('created_at', 'total_amount')
    
    from collections import defaultdict

    if time_range == 'today':
        hourly_map = defaultdict(float)
        for order in revenue_orders:
            local_dt = timezone.localtime(order['created_at'])
            hourly_map[local_dt.hour] += float(order['total_amount'] or 0)
        
        trend = [{'label': f'{h}:00', 'value': hourly_map[h]} for h in range(7, 23)]
    else:
        daily_map = defaultdict(float)
        for order in revenue_orders:
            local_dt = timezone.localtime(order['created_at'])
            daily_map[local_dt.date()] += float(order['total_amount'] or 0)
        
        # Sort by date
        sorted_dates = sorted(daily_map.keys())
        trend = [{'label': d.strftime('%b %d'), 'value': daily_map[d]} for d in sorted_dates]

    # Sales by category (Revenue only from PAID orders)
    cat_data = (
        OrderItem.objects.filter(order__in=chart_orders, menu_item__isnull=False)
        .values('menu_item__category__name')
        .annotate(revenue=Sum(
            ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()),
            filter=Q(order__is_paid=True)
        ))
        .order_by('-revenue')
    )
    categories = [
        {'name': c['menu_item__category__name'] or 'Other', 'value': float(c['revenue'] or 0)}
        for c in cat_data
    ]

    # Top sellers (Qty from all chart_orders, Revenue from PAID only)
    top_sellers_qs = (
        OrderItem.objects.filter(order__in=chart_orders)
        .values('item_name')
        .annotate(
            qty=Sum('quantity'),
            revenue=Sum(
                ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()),
                filter=Q(order__is_paid=True)
            )
        )
        .order_by('-qty')[:5]
    )
    top_sellers = [
        {'label': s['item_name'], 'value': s['qty'], 'revenue': float(s['revenue'] or 0)}
        for s in top_sellers_qs
    ]

    return JsonResponse({
        'trend': trend,
        'categories': categories,
        'top_sellers': top_sellers,
    })


# ───────────────────────────────────────
# Dashboard Stats API (for AJAX polling)
# ───────────────────────────────────────
@admin_required
def admin_dashboard_api(request):
    """JSON API returning all dashboard stats for real-time AJAX updates."""
    now = timezone.localtime(timezone.now())
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    time_range = request.GET.get('range', 'all')

    if time_range == '7days':
        start_date = today_start - timedelta(days=7)
    elif time_range == '30days':
        start_date = today_start - timedelta(days=30)
    elif time_range == 'today':
        start_date = today_start
    else:
        start_date = None
        time_range = 'all'

    # Base querysets
    orders_qs = Order.objects.exclude(status='payment_pending')
    if start_date:
        orders_qs = orders_qs.filter(created_at__gte=start_date)

    paid_orders = orders_qs.filter(is_paid=True)
    total_revenue = float(paid_orders.aggregate(total=Sum('total_amount'))['total'] or 0)
    total_orders = orders_qs.count()
    active_orders = Order.objects.filter(
        status__in=['pending', 'confirmed', 'preparing', 'ready']
    ).count()
    total_users = User.objects.filter(is_active=True).count()

    # Today deltas
    todays_revenue = float(Order.objects.filter(
        created_at__gte=today_start, is_paid=True
    ).exclude(status='payment_pending').aggregate(total=Sum('total_amount'))['total'] or 0)
    todays_orders = Order.objects.filter(
        created_at__gte=today_start
    ).exclude(status='payment_pending').count()

    # New users (last 7 days)
    week_ago = today_start - timedelta(days=7)
    new_users = User.objects.filter(date_joined__gte=week_ago).count()

    # Recent orders (5)
    recent_orders = Order.objects.exclude(
        status='payment_pending'
    ).select_related('user').prefetch_related('items').order_by('-created_at')[:5]

    recent_orders_data = []
    for order in recent_orders:
        items_list = []
        for oi in order.items.all()[:2]:
            items_list.append({
                'quantity': oi.quantity,
                'item_name': oi.item_name[:15],
            })
        recent_orders_data.append({
            'token_number': order.token_number,
            'username': order.user.username,
            'user_id': order.user.id,
            'items': items_list,
            'items_count': order.items.count(),
            'total_amount': float(order.total_amount),
            'status': order.status,
            'status_display': order.get_status_display(),
        })

    # Top sellers
    valid_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'delivered', 'collected']
    if start_date:
        top_items_qs = OrderItem.objects.filter(
            order__status__in=valid_statuses,
            order__created_at__gte=start_date,
        )
    else:
        top_items_qs = OrderItem.objects.filter(order__status__in=valid_statuses)

    top_sellers = list(
        top_items_qs
        .values('item_name')
        .annotate(
            qty=Sum('quantity'),
            revenue=Sum(
                ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()),
                filter=Q(order__is_paid=True)
            )
        )
        .order_by('-qty')[:5]
    )
    top_sellers_data = [
        {'label': s['item_name'], 'value': s['qty'], 'revenue': float(s['revenue'] or 0)}
        for s in top_sellers
    ]

    return JsonResponse({
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'active_orders': active_orders,
        'total_users': total_users,
        'todays_revenue': todays_revenue,
        'todays_orders': todays_orders,
        'new_users': new_users,
        'recent_orders': recent_orders_data,
        'top_sellers': top_sellers_data,
    })


# ───────────────────────────────────────
# Orders API (for AJAX polling)
# ───────────────────────────────────────
@admin_or_kitchen_required
def admin_orders_api(request):
    """JSON API returning orders table data for real-time AJAX updates."""
    # Check for single order detail request
    detail_id = request.GET.get('detail_id')
    if detail_id:
        try:
            order = Order.objects.get(id=detail_id)
            items = []
            for oi in order.items.all():
                items.append({
                    'name': oi.item_name,
                    'quantity': oi.quantity,
                    'price': float(oi.price),
                })
            return JsonResponse({
                'id': order.id,
                'token_number': order.token_number,
                'status': order.status,
                'status_display': order.get_status_display(),
                'total_amount': float(order.total_amount),
                'payment_status': 'Paid' if order.is_paid else 'Unpaid',
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
                'scheduled_for': order.scheduled_for.strftime('%Y-%m-%d %H:%M') if order.scheduled_for else None,
                'user': {
                    'username': order.user.username,
                    'email': order.user.email,
                    'id': order.user.id
                },
                'items': items
            })
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)

    status_filter = request.GET.get('status', 'all')
    search = request.GET.get('search', '').strip()
    page_num = request.GET.get('page', '1')

    orders_qs = Order.objects.exclude(status='payment_pending').select_related('user').prefetch_related('items')

    if search:
        orders_qs = orders_qs.filter(
            Q(token_number__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search)
        )

    if status_filter == 'pending':
        orders_qs = orders_qs.filter(status__in=['pending', 'confirmed'])
    elif status_filter == 'preparing':
        orders_qs = orders_qs.filter(status='preparing')
    elif status_filter == 'ready':
        orders_qs = orders_qs.filter(status='ready')
    elif status_filter == 'completed':
        orders_qs = orders_qs.filter(status__in=['delivered', 'collected'])

    orders_qs = orders_qs.order_by('-created_at')

    # Pagination
    paginator = Paginator(orders_qs, 15)
    try:
        orders_page = paginator.page(page_num)
    except PageNotAnInteger:
        orders_page = paginator.page(1)
    except EmptyPage:
        orders_page = paginator.page(paginator.num_pages)

    orders_data = []
    for order in orders_page:
        items_list = []
        for oi in order.items.all()[:2]:
            items_list.append({
                'quantity': oi.quantity,
                'item_name': oi.item_name[:12],
            })
        orders_data.append({
            'id': order.id,
            'token_number': order.token_number,
            'username': order.user.username,
            'email': order.user.email[:22],
            'user_id': order.user.id,
            'items': items_list,
            'items_count': order.items.count(),
            'total_amount': float(order.total_amount),
            'status': order.status,
            'status_display': order.get_status_display(),
            'created_at': order.created_at.strftime('%b %d, %H:%M'),
            'scheduled_for': order.scheduled_for.strftime('%b %d, %H:%M') if order.scheduled_for else None,
        })

    # Counts
    base = Order.objects.exclude(status='payment_pending')
    counts = {
        'all': base.count(),
        'pending': base.filter(status__in=['pending', 'confirmed']).count(),
        'preparing': base.filter(status='preparing').count(),
        'ready': base.filter(status='ready').count(),
        'completed': base.filter(status__in=['delivered', 'collected']).count(),
    }

    return JsonResponse({
        'orders': orders_data,
        'counts': counts,
        'page': orders_page.number,
        'num_pages': paginator.num_pages,
    })


# ───────────────────────────────────────
# WhatsApp Notifications
# ───────────────────────────────────────
@admin_required
def admin_whatsapp(request):
    """WhatsApp Notifications management page."""
    from notifications.models import Offer, WhatsAppLog
    from notifications.whatsapp import send_offer_to_users

    # Handle WhatsApp Actions
    if request.method == 'POST' and 'whatsapp_action' in request.POST:
        action = request.POST.get('whatsapp_action')

        if action == 'create_offer':
            title = request.POST.get('offer_title', '').strip()
            description = request.POST.get('offer_description', '').strip()
            code = request.POST.get('offer_code', '').strip().upper()
            valid_until = request.POST.get('offer_valid_until', '')
            discount_type = request.POST.get('discount_type', 'percent')
            discount_value = request.POST.get('discount_value', '').strip()
            single_item_only = request.POST.get('single_item_only') == 'on'

            if title and description and valid_until:
                offer = Offer.objects.create(
                    title=title,
                    description=description,
                    discount_code=code,
                    valid_from=timezone.now(),
                    valid_until=valid_until,
                    is_active=True,
                )

                # Auto-create a matching Coupon so the code works at checkout
                if code and discount_value:
                    from orders.models import Coupon
                    from decimal import Decimal, InvalidOperation
                    try:
                        val = Decimal(discount_value)
                        Coupon.objects.update_or_create(
                            code=code,
                            defaults={
                                'description': title,
                                'discount_type': discount_type,
                                'discount_value': val,
                                'valid_from': timezone.now(),
                                'valid_until': valid_until,
                                'is_active': True,
                                'single_item_only': single_item_only,
                            },
                        )
                    except (InvalidOperation, ValueError):
                        pass  # Skip coupon creation if value is invalid

                messages.success(request, f'Offer "{title}" created!')
            else:
                messages.error(request, 'Please fill in all required fields.')
            return redirect('custom_admin_whatsapp')

        elif action == 'send_offer':
            offer_id = request.POST.get('offer_id')
            user_ids = request.POST.getlist('user_ids')
            try:
                offer = Offer.objects.get(id=offer_id)
                if user_ids:
                    from django.contrib.auth.models import User as AuthUser
                    selected_users = AuthUser.objects.filter(id__in=user_ids)
                    results = send_offer_to_users(offer, users_queryset=selected_users)
                else:
                    messages.error(request, 'Please select at least one user.')
                    return redirect('custom_admin_whatsapp')
                sent = results.get('sent', 0)
                failed = results.get('failed', 0)
                skipped = results.get('skipped', 0)
                messages.success(request, f'WhatsApp: {sent} sent, {failed} failed, {skipped} skipped')
            except Offer.DoesNotExist:
                messages.error(request, 'Offer not found.')
            return redirect('custom_admin_whatsapp')

        elif action == 'delete_offer':
            offer_id = request.POST.get('offer_id')
            try:
                offer = Offer.objects.get(id=offer_id)
                title = offer.title
                offer.delete()
                messages.success(request, f'Offer "{title}" deleted!')
            except Offer.DoesNotExist:
                messages.error(request, 'Offer not found.')
            return redirect('custom_admin_whatsapp')

    # Data
    offers = Offer.objects.annotate(sent_count=Count('whatsapp_logs')).order_by('-created_at')[:20]
    recent_logs = WhatsAppLog.objects.select_related('user', 'offer').order_by('-sent_at')[:10]
    opted_in_count = UserProfile.objects.filter(whatsapp_opt_in=True).count()
    sent_count = WhatsAppLog.objects.filter(status='sent').count()
    failed_count = WhatsAppLog.objects.filter(status='failed').count()
    active_offers_count = Offer.objects.filter(is_active=True).count()

    context = {
        'offers': offers,
        'recent_logs': recent_logs,
        'opted_in_count': opted_in_count,
        'opted_in_users': UserProfile.objects.filter(whatsapp_opt_in=True).exclude(phone='').select_related('user'),
        'sent_count': sent_count,
        'failed_count': failed_count,
        'active_offers_count': active_offers_count,
        'active_page': 'whatsapp',
    }
    return render(request, 'admin/admin_whatsapp.html', context)

