from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from orders.models import Order
from accounts.models import UserProfile
from .models import Payment, WalletTransaction
import uuid
import json
import logging
import requests as http_requests
from django.urls import reverse
from canteen.utils import redirect_replace

logger = logging.getLogger(__name__)

# Dodo Payments configuration
DODO_API_KEY = settings.DODO_PAYMENTS_API_KEY
DODO_MODE = settings.DODO_PAYMENTS_MODE
DODO_BASE_URL = 'https://test.dodopayments.com' if DODO_MODE == 'test_mode' else 'https://live.dodopayments.com'

# Wallet configuration
MAX_WALLET_BALANCE = 10000  # Maximum wallet balance allowed
MAX_SINGLE_TOPUP = 5000     # Maximum single topup amount
MIN_TOPUP_AMOUNT = 10       # Minimum topup amount

# Cache for the product ID
_dodo_product_id_cache = None


def _get_dodo_headers():
    """Get authorization headers for Dodo Payments API."""
    return {
        'Authorization': f'Bearer {DODO_API_KEY}',
        'Content-Type': 'application/json',
    }


def _get_or_create_dodo_product():
    """Get or create a generic 'Canteen Order' product in Dodo Payments."""
    global _dodo_product_id_cache

    # Check settings first
    if settings.DODO_PRODUCT_ID:
        return settings.DODO_PRODUCT_ID

    # Check cache
    if _dodo_product_id_cache:
        return _dodo_product_id_cache

    # Try to find existing product
    try:
        resp = http_requests.get(
            f'{DODO_BASE_URL}/products',
            headers=_get_dodo_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            products = resp.json()
            if isinstance(products, list):
                for p in products:
                    if p.get('name') == 'Canteen Order':
                        _dodo_product_id_cache = p['product_id']
                        logger.info(f'Found existing Dodo product: {_dodo_product_id_cache}')
                        return _dodo_product_id_cache
            elif isinstance(products, dict) and 'items' in products:
                for p in products['items']:
                    if p.get('name') == 'Canteen Order':
                        _dodo_product_id_cache = p['product_id']
                        logger.info(f'Found existing Dodo product: {_dodo_product_id_cache}')
                        return _dodo_product_id_cache
    except Exception as e:
        logger.warning(f'Error listing Dodo products: {e}')

    # Create new product
    try:
        resp = http_requests.post(
            f'{DODO_BASE_URL}/products',
            headers=_get_dodo_headers(),
            json={
                'name': 'Canteen Order',
                'description': 'CampusBites canteen order payment',
                'price': {
                    'currency': 'INR',
                    'discount': 0,
                    'price': 100,
                    'purchasing_power_parity': False,
                    'type': 'one_time_price',
                    'pay_what_you_want': True,
                    'suggested_price': None,
                    'tax_inclusive': True,
                },
                'is_recurring': False,
                'tax_category': 'digital_products',
            },
            timeout=15,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            _dodo_product_id_cache = data.get('product_id')
            logger.info(f'Created Dodo product: {_dodo_product_id_cache}')
            return _dodo_product_id_cache
        else:
            logger.error(f'Failed to create Dodo product: {resp.status_code} {resp.text}')
    except Exception as e:
        logger.error(f'Error creating Dodo product: {e}')

    return None


def _get_client_ip(request):
    """Extract real client IP address, respecting reverse proxies."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@login_required
def payment_page(request, order_id):
    """Show payment options"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.is_paid:
        messages.info(request, 'Order already paid')
        return redirect('order_detail', order_id=order.id)

    wallet_balance = request.user.profile.wallet_balance
    wallet_sufficient = wallet_balance >= order.total_amount
    wallet_shortfall = max(order.total_amount - wallet_balance, 0)

    context = {
        'order': order,
        'wallet_balance': wallet_balance,
        'wallet_sufficient': wallet_sufficient,
        'wallet_shortfall': wallet_shortfall,
    }
    return render(request, 'payments/payment_page.html', context)


@login_required
@transaction.atomic
def process_cash_payment(request, order_id):
    """Process cash payment"""
    if request.method != 'POST':
        return redirect('payment_page', order_id=order_id)

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.is_paid:
        messages.info(request, 'Order already paid')
        return redirect('order_detail', order_id=order.id)

    Payment.objects.create(
        order=order,
        amount=order.total_amount,
        method='cash',
        status='pending',
        ip_address=_get_client_ip(request),
    )

    order.transition_to('pending')
    order.save()

    # Send confirmation email after payment
    from orders.utils import send_order_confirmation_email
    send_order_confirmation_email(order)

    messages.success(request, 'Order confirmed! Pay at counter.')
    return redirect_replace(reverse('order_detail', args=[order.id]))


@login_required
@transaction.atomic
def process_wallet_payment(request, order_id):
    """Process wallet payment with atomic transaction to prevent race conditions"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Lock the profile row to prevent concurrent modifications
    profile = UserProfile.objects.select_for_update().get(user=request.user)

    if profile.wallet_balance < order.total_amount:
        messages.error(request, 'Insufficient wallet balance')
        return redirect('payment_page', order_id=order_id)

    # Deduct from wallet (now atomic)
    profile.wallet_balance -= order.total_amount
    profile.save()

    txn_ref = str(uuid.uuid4()).replace('-', '').upper()[:12]

    # Record transaction
    WalletTransaction.objects.create(
        user=request.user,
        amount=order.total_amount,
        transaction_type='debit',
        description=f'Payment for order #{order.token_number}',
        reference_id=txn_ref,
    )

    # Create payment record
    Payment.objects.create(
        order=order,
        amount=order.total_amount,
        method='wallet',
        status='completed',
        transaction_id=txn_ref,
        ip_address=_get_client_ip(request),
        gateway_response={'source': 'canteen_wallet', 'ref': txn_ref},
    )

    order.is_paid = True
    order.transition_to('confirmed')
    order.save()

    # Send confirmation email after payment
    from orders.utils import send_order_confirmation_email
    send_order_confirmation_email(order)

    messages.success(request, '✓ Payment successful!')
    return redirect_replace(reverse('order_detail', args=[order.id]))


@login_required
def wallet_view(request):
    """Show wallet balance, monthly summary, and paginated transactions"""
    all_txns = WalletTransaction.objects.filter(user=request.user)

    # Monthly summary
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_txns = all_txns.filter(created_at__gte=month_start)
    month_credits = month_txns.filter(transaction_type='credit').aggregate(
        total=Sum('amount'))['total'] or 0
    month_debits = month_txns.filter(transaction_type='debit').aggregate(
        total=Sum('amount'))['total'] or 0

    # Filter
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'credit':
        transactions_list = all_txns.filter(transaction_type='credit')
    elif filter_type == 'debit':
        transactions_list = all_txns.filter(transaction_type='debit')
    else:
        transactions_list = all_txns

    paginator = Paginator(transactions_list, 15)
    page = request.GET.get('page')
    try:
        transactions = paginator.page(page)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)

    balance = request.user.profile.wallet_balance
    cap_pct = min(int((balance / MAX_WALLET_BALANCE) * 100), 100)

    context = {
        'balance': balance,
        'transactions': transactions,
        'month_credits': month_credits,
        'month_debits': month_debits,
        'filter_type': filter_type,
        'max_wallet': MAX_WALLET_BALANCE,
        'cap_pct': cap_pct,
    }
    return render(request, 'payments/wallet.html', context)


@login_required
def add_money_to_wallet(request):
    """Create a Dodo Payments link for wallet top-up."""
    if request.method != 'POST':
        return redirect('/profile/#wallet')

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        amount = int(request.POST.get('amount', 0))
    except (ValueError, TypeError):
        if is_ajax:
            return JsonResponse({'error': 'Invalid amount'}, status=400)
        messages.error(request, 'Invalid amount')
        return redirect('/profile/#wallet')

    # Validate amount limits
    if amount < MIN_TOPUP_AMOUNT:
        msg = f'Minimum topup amount is ₹{MIN_TOPUP_AMOUNT}'
        if is_ajax:
            return JsonResponse({'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('/profile/#wallet')

    if amount > MAX_SINGLE_TOPUP:
        msg = f'Maximum single topup is ₹{MAX_SINGLE_TOPUP}'
        if is_ajax:
            return JsonResponse({'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('/profile/#wallet')

    # Check wallet balance limit
    profile = request.user.profile
    if profile.wallet_balance + amount > MAX_WALLET_BALANCE:
        msg = f'Wallet balance cannot exceed ₹{MAX_WALLET_BALANCE}'
        if is_ajax:
            return JsonResponse({'error': msg}, status=400)
        messages.error(request, msg)
        return redirect('/profile/#wallet')

    # Get or create the Dodo product
    product_id = _get_or_create_dodo_product()
    if not product_id:
        msg = 'Payment gateway configuration error. Please try again later.'
        if is_ajax:
            return JsonResponse({'error': msg}, status=502)
        messages.error(request, msg)
        return redirect('/profile/#wallet')

    try:
        return_url = request.build_absolute_uri(reverse('wallet_topup_success'))
        topup_ref = str(uuid.uuid4()).replace('-', '').upper()[:12]
        total_paise = amount * 100

        payload = {
            'billing': {
                'city': 'Campus',
                'country': 'IN',
                'state': 'KA',
                'street': 'Campus Address',
                'zipcode': '560001',
            },
            'customer': {
                'email': request.user.email or f'{request.user.username}@campusbites.com',
                'name': request.user.get_full_name() or request.user.username,
            },
            'product_cart': [
                {
                    'product_id': product_id,
                    'quantity': 1,
                    'amount': total_paise,
                }
            ],
            'payment_link': True,
            'return_url': return_url,
            'metadata': {
                'wallet_topup': 'true',
                'user_id': str(request.user.id),
                'amount': str(amount),
                'topup_ref': topup_ref,
            },
        }

        resp = http_requests.post(
            f'{DODO_BASE_URL}/payments',
            headers=_get_dodo_headers(),
            json=payload,
            timeout=15,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            payment_link = data.get('payment_link')
            payment_id = data.get('payment_id')

            if payment_link:
                # Store the pending topup in session for verification
                request.session['wallet_topup'] = {
                    'payment_id': payment_id,
                    'amount': amount,
                    'ref': topup_ref,
                }

                if is_ajax:
                    return JsonResponse({'url': payment_link})
                return redirect(payment_link)
            else:
                raise Exception('No payment link returned from Dodo Payments')
        else:
            logger.error(f'Dodo Payments wallet topup error: {resp.status_code} {resp.text}')
            raise Exception(f'Dodo API returned {resp.status_code}')

    except Exception as e:
        logger.error(f'Dodo Payments wallet topup error for user {request.user.id}: {e}')
        msg = 'Unable to connect to payment gateway. Please try again.'
        if is_ajax:
            return JsonResponse({'error': msg}, status=502)
        messages.error(request, msg)
        return redirect('/profile/#wallet')


@login_required
@transaction.atomic
def wallet_topup_success(request):
    """Handle return from Dodo Payments after wallet top-up."""
    topup_data = request.session.get('wallet_topup')

    if not topup_data:
        messages.error(request, 'No pending top-up found')
        return redirect('wallet')

    payment_id = topup_data.get('payment_id')
    amount = topup_data.get('amount')
    topup_ref = topup_data.get('ref')

    if not payment_id:
        messages.error(request, 'Invalid top-up session')
        return redirect('wallet')

    try:
        # Verify payment status with Dodo
        resp = http_requests.get(
            f'{DODO_BASE_URL}/payments/{payment_id}',
            headers=_get_dodo_headers(),
            timeout=10,
        )

        if resp.status_code == 200:
            data = resp.json()
            dodo_status = data.get('status', '').lower()

            if dodo_status in ('succeeded', 'completed', 'paid'):
                # Check idempotency — don't double-credit
                existing = WalletTransaction.objects.filter(reference_id=topup_ref).first()
                if existing:
                    # Already credited, clear session and redirect
                    del request.session['wallet_topup']
                    messages.info(request, 'Top-up already processed')
                    return redirect('/profile/#wallet')

                # Lock profile to prevent race conditions
                profile = UserProfile.objects.select_for_update().get(user=request.user)
                profile.wallet_balance += amount
                profile.save()

                WalletTransaction.objects.create(
                    user=request.user,
                    amount=amount,
                    transaction_type='credit',
                    description='Wallet top-up via Dodo Payments',
                    reference_id=topup_ref,
                )

                # Clear session data
                del request.session['wallet_topup']

                messages.success(request, f'₹{amount} added to wallet!')
                return redirect('/profile/#wallet')
            else:
                messages.warning(request, 'Payment not yet confirmed. Please wait or try again.')
                return redirect('/profile/#wallet')
        else:
            logger.error(f'Dodo wallet topup verify error: {resp.status_code} {resp.text}')
            messages.error(request, 'Payment verification failed. Please contact support.')
            return redirect('/profile/#wallet')

    except Exception as e:
        logger.error(f'Dodo wallet topup verification error for payment {payment_id}: {e}')
        messages.error(request, 'Payment verification failed. Please contact support.')
        return redirect('/profile/#wallet')



@login_required
def process_online_payment(request, order_id):
    """Create a Dodo Payments payment link and redirect the user."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if order.is_paid:
        if is_ajax:
            return JsonResponse({'error': 'Order already paid'}, status=400)
        messages.info(request, 'Order already paid')
        return redirect('order_detail', order_id=order.id)

    # Get or create the Dodo product
    product_id = _get_or_create_dodo_product()
    if not product_id:
        error_msg = 'Payment gateway configuration error. Please try again later.'
        if is_ajax:
            return JsonResponse({'error': error_msg}, status=502)
        messages.error(request, error_msg)
        return redirect('payment_page', order_id=order_id)

    try:
        # Build return URL
        return_url = request.build_absolute_uri(f'/payment/{order.id}/dodo/success/')

        # Total amount in smallest currency unit (paise for INR)
        total_paise = int(order.total_amount * 100)

        # Create payment via Dodo Payments REST API
        payload = {
            'billing': {
                'city': 'Campus',
                'country': 'IN',
                'state': 'KA',
                'street': 'Campus Address',
                'zipcode': '560001',
            },
            'customer': {
                'email': request.user.email or f'{request.user.username}@campusbites.com',
                'name': request.user.get_full_name() or request.user.username,
            },
            'product_cart': [
                {
                    'product_id': product_id,
                    'quantity': 1,
                    'amount': total_paise,
                }
            ],
            'payment_link': True,
            'return_url': return_url,
            'metadata': {
                'order_id': str(order.id),
                'user_id': str(request.user.id),
                'token_number': str(order.token_number),
            },
        }

        resp = http_requests.post(
            f'{DODO_BASE_URL}/payments',
            headers=_get_dodo_headers(),
            json=payload,
            timeout=15,
        )

        if resp.status_code in (200, 201):
            data = resp.json()
            payment_link = data.get('payment_link')
            payment_id = data.get('payment_id')

            if payment_link:
                # Store the dodo payment ID for later verification
                Payment.objects.create(
                    order=order,
                    amount=order.total_amount,
                    method='dodo',
                    status='pending',
                    dodo_payment_id=payment_id,
                    ip_address=_get_client_ip(request),
                    gateway_response={
                        'gateway': 'dodo_payments',
                        'payment_id': payment_id,
                        'payment_link': payment_link,
                    },
                )

                if is_ajax:
                    return JsonResponse({'url': payment_link})
                return redirect_replace(payment_link)
            else:
                raise Exception('No payment link returned from Dodo Payments')
        else:
            logger.error(f'Dodo Payments error: {resp.status_code} {resp.text}')
            raise Exception(f'Dodo API returned {resp.status_code}')

    except Exception as e:
        logger.error(f'Dodo Payments error for order {order.id}: {e}')
        if is_ajax:
            return JsonResponse({'error': 'Unable to connect to payment gateway. Please try again.'}, status=502)
        messages.error(request, 'Unable to connect to payment gateway. Please try again.')
        return redirect('payment_page', order_id=order_id)


@login_required
@transaction.atomic
def dodo_success(request, order_id):
    """Handle return from Dodo Payments after payment."""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.is_paid:
        messages.info(request, 'Order already paid')
        return redirect_replace(reverse('order_detail', args=[order.id]))

    # Find the pending dodo payment for this order
    try:
        payment = Payment.objects.filter(
            order=order, method='dodo', status='pending'
        ).latest('created_at')
    except Payment.DoesNotExist:
        messages.error(request, 'Payment record not found')
        return redirect('payment_page', order_id=order_id)

    if not payment.dodo_payment_id:
        messages.error(request, 'Invalid payment session')
        return redirect('payment_page', order_id=order_id)

    try:
        # Verify payment status with Dodo
        resp = http_requests.get(
            f'{DODO_BASE_URL}/payments/{payment.dodo_payment_id}',
            headers=_get_dodo_headers(),
            timeout=10,
        )

        if resp.status_code == 200:
            data = resp.json()
            dodo_status = data.get('status', '').lower()

            if dodo_status in ('succeeded', 'completed', 'paid'):
                payment.status = 'completed'
                payment.transaction_id = payment.dodo_payment_id
                payment.gateway_response = {
                    'gateway': 'dodo_payments',
                    'payment_id': payment.dodo_payment_id,
                    'status': dodo_status,
                    'verified_at': timezone.now().isoformat(),
                }
                payment.save()

                order.is_paid = True
                order.transition_to('confirmed')
                order.save()

                # Send confirmation email after payment
                from orders.utils import send_order_confirmation_email
                send_order_confirmation_email(order)

                messages.success(request, f'✓ Payment successful! Transaction ID: {payment.dodo_payment_id}')
                return redirect_replace(reverse('order_detail', args=[order.id]))
            else:
                messages.warning(request, 'Payment not yet confirmed. Please wait or try again.')
                return redirect('payment_page', order_id=order_id)
        else:
            logger.error(f'Dodo verify error: {resp.status_code} {resp.text}')
            messages.error(request, 'Payment verification failed. Please contact support.')
            return redirect('payment_page', order_id=order_id)

    except Exception as e:
        logger.error(f'Dodo verification error for payment {payment.dodo_payment_id}: {e}')
        messages.error(request, 'Payment verification failed. Please contact support.')
        return redirect('payment_page', order_id=order_id)


@csrf_exempt
@require_POST
def dodo_webhook(request):
    """Handle Dodo Payments webhook events for reliable payment confirmation."""
    try:
        payload = json.loads(request.body)
    except (ValueError, json.JSONDecodeError):
        logger.warning('Dodo webhook: invalid JSON payload')
        return HttpResponse(status=400)

    event_type = payload.get('type', '')
    data = payload.get('data', {})

    # Handle payment.succeeded event
    if event_type in ('payment.succeeded', 'payment.completed'):
        payment_id = data.get('payment_id')
        metadata = data.get('metadata', {})
        order_id = metadata.get('order_id')

        # Check if this is a wallet top-up
        if metadata.get('wallet_topup') == 'true':
            user_id = metadata.get('user_id')
            amount = int(metadata.get('amount', 0))
            topup_ref = metadata.get('topup_ref', '')

            if user_id and amount > 0 and topup_ref:
                try:
                    with transaction.atomic():
                        # Idempotency check
                        if not WalletTransaction.objects.filter(reference_id=topup_ref).exists():
                            from django.contrib.auth.models import User
                            user = User.objects.get(id=int(user_id))
                            profile = UserProfile.objects.select_for_update().get(user=user)
                            profile.wallet_balance += amount
                            profile.save()

                            WalletTransaction.objects.create(
                                user=user,
                                amount=amount,
                                transaction_type='credit',
                                description='Wallet top-up via Dodo Payments',
                                reference_id=topup_ref,
                            )
                            logger.info(f'Dodo webhook: wallet topup ₹{amount} for user {user_id}')
                except Exception as e:
                    logger.error(f'Dodo webhook wallet topup error: {e}')
                    return HttpResponse(status=500)

            return HttpResponse(status=200)

        # Regular order payment
        if payment_id and order_id:
            try:
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(id=int(order_id))

                    # Idempotent — update existing pending payment or create new
                    payment, created = Payment.objects.get_or_create(
                        dodo_payment_id=payment_id,
                        defaults={
                            'order': order,
                            'amount': order.total_amount,
                            'method': 'dodo',
                            'status': 'completed',
                            'transaction_id': payment_id,
                            'gateway_response': {
                                'gateway': 'dodo_webhook',
                                'payment_id': payment_id,
                                'event_type': event_type,
                            }
                        }
                    )

                    if not created and payment.status != 'completed':
                        payment.status = 'completed'
                        payment.transaction_id = payment_id
                        payment.save()

                    if not order.is_paid:
                        order.is_paid = True
                        order.transition_to('confirmed')
                        order.save()
                        logger.info(f'Dodo webhook: order {order_id} confirmed')
            except Order.DoesNotExist:
                logger.warning(f'Dodo webhook: order {order_id} not found')
            except Exception as e:
                logger.error(f'Dodo webhook error for order {order_id}: {e}')
                return HttpResponse(status=500)

    return HttpResponse(status=200)


@login_required
def payment_status_api(request, payment_id):
    """JSON API endpoint for payment status polling"""
    payment = get_object_or_404(Payment, id=payment_id, order__user=request.user)
    return JsonResponse({
        'id': payment.id,
        'status': payment.status,
        'method': payment.method,
        'display_method': payment.display_method,
        'transaction_id': payment.transaction_id,
        'amount': str(payment.amount),
        'is_refunded': payment.is_refunded,
        'created_at': payment.created_at.isoformat(),
    })
