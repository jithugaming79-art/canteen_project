from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q, Sum, Count, F, Avg, DecimalField, ExpressionWrapper
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from menu.models import MenuItem, Favorite
from orders.models import Order, OrderItem
from django.utils import timezone
from allauth.account.models import EmailAddress
from django.core.cache import cache
import time
from .models import ValidStudent, ValidStaff, Feedback
import re
import json
import logging

# Allowed roles for self-registration (admin and kitchen require manual assignment)
ALLOWED_SIGNUP_ROLES = ['student', 'teacher']

# Phone validation regex (Indian phone numbers)
PHONE_REGEX = re.compile(r'^[6-9]\d{9}$')

def register_view(request):
    if request.method == 'GET':
        return redirect('home')
    if request.method == 'POST':
        # --- BOT PROTECTION: Honeypot & Timing ---
        if request.POST.get('website'):  # Honeypot filled by bot
            messages.error(request, 'Registration failed.')
            return render(request, 'accounts/auth_messages.html')
            
        form_load_time = request.POST.get('form_load_time', 0)
        try:
            if time.time() - float(form_load_time) < 2.0: # Too fast (bot)
                messages.error(request, 'Registration too fast. Please try again.')
                return render(request, 'accounts/auth_messages.html')
        except (ValueError, TypeError):
            pass

        # --- RATE LIMITING ---
        ip_addr = request.META.get('REMOTE_ADDR', '127.0.0.1')
        if request.META.get('HTTP_X_FORWARDED_FOR'):
            ip_addr = request.META.get('HTTP_X_FORWARDED_FOR').split(',')[0]
            
        cache_key = f'reg_attempts_{ip_addr}'
        attempts = cache.get(cache_key, 0)
        
        if attempts >= 5:
            messages.error(request, 'Too many accounts created from this IP. Please try again later.')
            return render(request, 'accounts/auth_messages.html')
            
        # Increment attempt counter (expires in 1 hour)
        cache.set(cache_key, attempts + 1, 3600)

        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        role = request.POST.get('role', 'student')
        college_id = request.POST.get('college_id', '').strip().upper()
        
        # Preserve form data for error display
        context = request.POST.dict()
        
        # --- INPUT VALIDATION & SANITIZATION ---
        if len(username) > 30 or len(email) > 254 or len(full_name) > 100 or len(phone) > 15:
            messages.error(request, 'Input exceeds maximum allowed length')
            return render(request, 'accounts/auth_messages.html')
            
        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
            messages.error(request, 'Username can only contain letters, numbers, and underscores (3-30 chars)')
            return render(request, 'accounts/auth_messages.html')
        if not username or len(username) < 3:
            messages.error(request, 'Username must be at least 3 characters')
            return render(request, 'accounts/auth_messages.html')
        
        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Please enter a valid email address')
            return render(request, 'accounts/auth_messages.html')
        
        # Check for duplicate email
        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists')
            return render(request, 'accounts/auth_messages.html')
        
        # Validate phone (mandatory and must be valid format)
        if not phone:
            messages.error(request, 'Phone number is required')
            return render(request, 'accounts/auth_messages.html')
        if not PHONE_REGEX.match(phone):
            messages.error(request, 'Please enter a valid 10-digit phone number')
            return render(request, 'accounts/auth_messages.html')
        
        # Validate password match
        if password1 != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'accounts/auth_messages.html')
            
        try:
            # Validate password strength
            temp_user = User(username=username, email=email)
            validate_password(password1, user=temp_user)
        except ValidationError as e:
            for error in e:
                messages.error(request, error)
            return render(request, 'accounts/auth_messages.html')
        
        # Check duplicate username
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'accounts/auth_messages.html')
        
        # SECURITY: Restrict role assignment to allowed roles only
        if role not in ALLOWED_SIGNUP_ROLES:
            role = 'student'  # Default to student for any invalid role
        
        # SECURITY: Verify Student / Faculty ID
        if role == 'student':
            if not college_id:
                messages.error(request, 'Student Registration Number is required')
                return render(request, 'accounts/auth_messages.html')
            
            try:
                valid_student = ValidStudent.objects.get(register_no=college_id)
                if valid_student.is_registered:
                    messages.error(request, 'This Registration Number has already been used')
                    return render(request, 'accounts/auth_messages.html')
            except ValidStudent.DoesNotExist:
                messages.error(request, 'Invalid Registration Number. Please contact admin.')
                return render(request, 'accounts/auth_messages.html')
        elif role == 'teacher':
            if not college_id:
                messages.error(request, 'Faculty / Staff ID is required')
                return render(request, 'accounts/auth_messages.html')

            try:
                valid_staff = ValidStaff.objects.get(staff_id=college_id)
                if valid_staff.is_registered:
                    messages.error(request, 'This Staff/Faculty ID has already been used')
                    return render(request, 'accounts/auth_messages.html')
            except ValidStaff.DoesNotExist:
                messages.error(request, 'Invalid Staff/Faculty ID. Please contact admin.')
                return render(request, 'accounts/auth_messages.html')
        
        # Create user
        user = User.objects.create_user(username=username, email=email, password=password1)
        user.profile.full_name = full_name
        user.profile.phone = phone
        user.profile.role = role
        
        if role == 'student':
            user.profile.college_id = college_id
            # Mark ID as used
            valid_student.is_registered = True
            valid_student.save()
        elif role == 'teacher':
            user.profile.college_id = college_id
            # Mark staff ID as used
            valid_staff.is_registered = True
            valid_staff.save()
        
        user.profile.save()
        
        # Create EmailAddress but mark as unverified initially
        EmailAddress.objects.create(user=user, email=email, primary=True, verified=False)
        
        # Generate and send OTP for email verification
        from .email_otp import generate_otp, store_otp, send_otp_email, mark_resend
        otp = generate_otp()
        store_otp(email, otp)
        mark_resend(email)
        
        email_sent = send_otp_email(email, otp)
        if email_sent:
            messages.success(request, 'Account created! Please check your email for the verification code.')
        else:
            messages.warning(request, 'Account created, but we could not send the verification email. Please use the resend option.')
        
        
        # Store email in session for the verify page
        request.session['verify_email'] = email
        return redirect('verify_email_otp')
    
    return redirect('home')

def phone_login_view(request):
    """Render the phone OTP login page with Firebase integration."""
    return render(request, 'accounts/phone_login.html', {
        'firebase_config': settings.FIREBASE_CONFIG
    })

def phone_verify_view(request):
    """Receive Firebase ID token after phone OTP verification, create/find user, log them in."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=405)
    
    try:
        data = json.loads(request.body)
        phone = data.get('phone', '').strip()
        id_token = data.get('id_token', '')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)
    
    if not phone or not id_token:
        return JsonResponse({'success': False, 'error': 'Phone and token are required'}, status=400)
    
    # Validate phone format
    clean_phone = phone.replace('+91', '').replace(' ', '').strip()
    if len(clean_phone) > 10:
        clean_phone = clean_phone[-10:]
    
    if not PHONE_REGEX.match(clean_phone):
        return JsonResponse({'success': False, 'error': 'Invalid phone number'}, status=400)
    
    # Rate limit check
    from .phone_auth import check_phone_rate_limit, get_or_create_user_by_phone
    if not check_phone_rate_limit(clean_phone):
        return JsonResponse({'success': False, 'error': 'Too many attempts. Please try later.'}, status=429)
    
    try:
        user, created = get_or_create_user_by_phone(clean_phone)
        
        # Check if user is deactivated
        if not user.is_active:
            request.session['reactivate_email'] = user.email
            return JsonResponse({
                'success': True,
                'redirect': '/reactivate_account/',
                'new_user': False
            })
            
        # Log the user in
        from django.contrib.auth import login as auth_login
        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        # Determine redirect based on role
        redirect_url = '/home/'
        if hasattr(user, 'profile'):
            if user.profile.is_admin:
                redirect_url = '/staff/dashboard/'
            elif user.profile.role == 'kitchen':
                redirect_url = '/kitchen/'
        
        phone_logger = logging.getLogger(__name__)
        phone_logger.info(f"Phone login {'(new user)' if created else '(existing user)'}: {clean_phone}")
        
        return JsonResponse({
            'success': True,
            'redirect': redirect_url,
            'new_user': created
        })
    except Exception as e:
        phone_logger = logging.getLogger(__name__)
        phone_logger.error(f"Phone login failed for {clean_phone}: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Login failed. Please try again.'}, status=500)


def verify_email_otp_view(request):
    """Handle the email OTP verification page and form submission."""
    email = request.session.get('verify_email', '')
    
    if not email:
        messages.error(request, 'No email to verify. Please register or log in first.')
        return redirect('login')
    
    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()
        post_email = request.POST.get('email', email).strip().lower()
        
        if not entered_otp or len(entered_otp) != 6:
            messages.error(request, 'Please enter the full 6-digit code.')
            return render(request, 'accounts/verify_email.html', {'email': post_email})
        
        from .email_otp import verify_otp
        success, message = verify_otp(post_email, entered_otp)
        
        if success:
            # Mark email as verified in Django
            try:
                email_address = EmailAddress.objects.get(email=post_email)
                email_address.verified = True
                email_address.save()
            except EmailAddress.DoesNotExist:
                pass
            
            # Clean up session
            if 'verify_email' in request.session:
                del request.session['verify_email']
            
            messages.success(request, 'Email verified successfully! You can now log in.')
            return redirect('login')
        else:
            messages.error(request, message)
            return render(request, 'accounts/verify_email.html', {'email': post_email})
    
    return render(request, 'accounts/verify_email.html', {'email': email})


def resend_email_otp_view(request):
    """Resend the email OTP with cooldown protection."""
    if request.method != 'POST':
        return redirect('verify_email_otp')
    
    email = request.POST.get('email', '').strip().lower() or request.session.get('verify_email', '')
    
    if not email:
        messages.error(request, 'No email address found. Please register first.')
        return redirect('register')
    
    from .email_otp import generate_otp, store_otp, send_otp_email, can_resend, mark_resend
    
    if not can_resend(email):
        messages.warning(request, 'Please wait before requesting a new code.')
        return redirect('verify_email_otp')
    
    otp = generate_otp()
    store_otp(email, otp)
    mark_resend(email)
    
    if send_otp_email(email, otp):
        messages.success(request, 'A new verification code has been sent to your email.')
    else:
        messages.error(request, 'Failed to send verification code. Please try again later.')
    
    request.session['verify_email'] = email
    return redirect('verify_email_otp')


def login_view(request):
    if request.method == 'GET':
        return redirect('home')
    from django.core.exceptions import PermissionDenied
    if request.method == 'POST':
        username = request.POST.get('username')
        if len(username) > 30: # Limit length
            messages.error(request, 'Invalid credentials')
            return render(request, 'accounts/auth_messages.html')
            
        password = request.POST.get('password')
        
        try:
            user = authenticate(request, username=username, password=password)
        except PermissionDenied:
            messages.error(request, 'Too many failed attempts. Please try again in an hour.')
            return render(request, 'accounts/auth_messages.html')
        
        if user is not None:
            # Email verification check
            email_address = EmailAddress.objects.filter(user=user, email=user.email).first()
            if email_address and not email_address.verified:
                # Send a new OTP and redirect to verification page
                from .email_otp import generate_otp, store_otp, send_otp_email, mark_resend, can_resend
                if can_resend(user.email):
                    otp = generate_otp()
                    store_otp(user.email, otp)
                    mark_resend(user.email)
                    send_otp_email(user.email, otp)
                
                request.session['verify_email'] = user.email
                messages.error(request, 'Please verify your email first. A new code has been sent.')
                return redirect('verify_email_otp')
            
            login(request, user)
            
            # Remember Me: extend session to 30 days if checked
            if request.POST.get('remember_me'):
                request.session.set_expiry(2592000)  # 30 days
            else:
                request.session.set_expiry(86400)  # 24 hours (default)
            
            # Redirect based on role
            if hasattr(user, 'profile'):
                if user.profile.is_admin:
                    return redirect('admin_dashboard')
                elif user.profile.role == 'kitchen':
                    return redirect('kitchen_dashboard')
            return redirect('home')
        else:
            from django.db.models import Q
            # Check if the username/email exists at all
            user_exists = User.objects.filter(
                Q(username__iexact=username) | Q(email__iexact=username)
            ).exists()
            if not user_exists:
                messages.error(request, 'No account found with that username or email. Please register first.')
            else:
                messages.error(request, 'Invalid credentials. Please check your password.')
    
    return render(request, 'accounts/auth_messages.html')

def reactivate_account_view(request):
    """View to handle reactivation of a deactivated account."""
    reactivate_email = request.session.get('reactivate_email')
    if not reactivate_email:
        return redirect('login')
    
    if request.method == 'POST':
        from django.db.models import Q
        try:
            inactive_user = User.objects.get(email=reactivate_email, is_active=False)
            # Reactivate account and log in
            inactive_user.is_active = True
            inactive_user.save()
            
            # Remove session key
            del request.session['reactivate_email']
            
            login(request, inactive_user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Welcome back! Your account has been reactivated.')
            return redirect('home')
        except User.DoesNotExist:
            messages.error(request, 'Account not found or already active.')
            return redirect('login')
            
    return render(request, 'accounts/reactivate_account.html')

@login_required
def change_password_view(request):
    """Secure password change view requiring old password validation"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in after change
            messages.success(request, 'Your password was successfully updated!')
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out')
    return redirect('home')

def home_view(request):
    # Redirect staff away from customer home page
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        if request.user.profile.is_admin:
            return redirect('admin_dashboard')
        elif request.user.profile.role == 'kitchen':
            return redirect('kitchen_dashboard')

    specials = MenuItem.objects.filter(is_todays_special=True, is_available=True)[:4]
    popular_items = MenuItem.objects.filter(is_available=True)[:6]
    
    context = {
        'specials': specials,
        'popular_items': popular_items,
        'firebase_config': settings.FIREBASE_CONFIG,
    }
    return render(request, 'accounts/home.html', context)

def terms_view(request):
    """Terms and Conditions page"""
    return render(request, 'accounts/terms.html')

@login_required
def admin_dashboard(request):
    """Staff dashboard for order management"""
    if not request.user.profile.is_admin:
        messages.error(request, 'Access denied. Staff only.')
        return redirect('home')
        
    # Handle Status Update
    if request.method == 'POST' and 'order_id' in request.POST:
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('status')
        try:
            order = Order.objects.get(id=order_id)
            order.status = new_status
            if new_status == 'collected':
                order.is_paid = True
            order.save()
            messages.success(request, f'Order {order.token_number} marked as {new_status}')
        except Order.DoesNotExist:
            pass
        return redirect('admin_dashboard')

    # Handle Menu Toggle
    if request.method == 'POST' and 'toggle_item' in request.POST:
        item_id = request.POST.get('item_id')
        from menu.services import toggle_menu_item_availability
        success, item, msg = toggle_menu_item_availability(item_id)
        if success:
            messages.info(request, msg)
        return redirect('admin_dashboard')

    # Handle WhatsApp Actions
    if request.method == 'POST' and 'whatsapp_action' in request.POST:
        action = request.POST.get('whatsapp_action')
        
        if action == 'create_offer':
            from notifications.models import Offer
            title = request.POST.get('offer_title', '').strip()
            description = request.POST.get('offer_description', '').strip()
            code = request.POST.get('offer_code', '').strip().upper()
            valid_until = request.POST.get('offer_valid_until', '')
            discount_type = request.POST.get('discount_type', 'percent')
            discount_value = request.POST.get('discount_value', '').strip()
            single_item_only = request.POST.get('single_item_only') == 'on'
            
            if title and description and valid_until:
                Offer.objects.create(
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
                        pass

                messages.success(request, f'✅ Offer "{title}" created!')
            else:
                messages.error(request, 'Please fill in all required fields.')
            return redirect('admin_dashboard')
        
        elif action == 'send_offer':
            from notifications.models import Offer
            from notifications.whatsapp import send_offer_to_users
            offer_id = request.POST.get('offer_id')
            try:
                offer = Offer.objects.get(id=offer_id)
                results = send_offer_to_users(offer)
                sent = results.get('sent', 0)
                failed = results.get('failed', 0)
                skipped = results.get('skipped', 0)
                messages.success(request, f'📱 WhatsApp: {sent} sent, {failed} failed, {skipped} skipped')
            except Offer.DoesNotExist:
                messages.error(request, 'Offer not found.')
            return redirect('admin_dashboard')

    # Data for Dashboard
    active_orders_qs = Order.objects.exclude(status__in=['payment_pending', 'collected', 'cancelled']).order_by('-created_at')
    

    # Paginate orders (20 per page)
    paginator = Paginator(active_orders_qs, 20)
    page = request.GET.get('page')
    try:
        active_orders = paginator.page(page)
    except PageNotAnInteger:
        active_orders = paginator.page(1)
    except EmptyPage:
        active_orders = paginator.page(paginator.num_pages)
    
    # Simple Stats
    today = timezone.now().date()
    todays_orders = Order.objects.filter(created_at__date=today)
    total_revenue = todays_orders.filter(is_paid=True).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    menu_items = MenuItem.objects.all().order_by('category', 'name')

    # WhatsApp Data
    from notifications.models import Offer, WhatsAppLog
    from accounts.models import UserProfile
    offers = Offer.objects.all().order_by('-created_at')[:20]
    whatsapp_opted_in_count = UserProfile.objects.filter(whatsapp_opt_in=True).count()
    whatsapp_sent_count = WhatsAppLog.objects.filter(status='sent').count()
    active_offers_count = Offer.objects.filter(is_active=True).count()

    context = {
        'active_orders': active_orders,
        'todays_count': todays_orders.count(),
        'total_revenue': total_revenue,
        'menu_items': menu_items,
        'offers': offers,
        'whatsapp_opted_in_count': whatsapp_opted_in_count,
        'whatsapp_sent_count': whatsapp_sent_count,
        'active_offers_count': active_offers_count,
    }
    return render(request, 'accounts/admin_dashboard.html', context)


@login_required
def kitchen_dashboard(request):
    """Kitchen staff dashboard for order preparation"""
    # Check if user is kitchen staff or admin
    if request.user.profile.role not in ['kitchen', 'admin']:
        messages.error(request, 'Access denied. Kitchen staff only.')
        return redirect('home')
    
    # Handle Bulk Actions
    if request.method == 'POST' and 'bulk_action' in request.POST:
        order_ids = request.POST.getlist('order_ids')
        target_status = request.POST.get('target_status')
        
        if order_ids and target_status:
            updated_count = 0
            for order_id in order_ids:
                try:
                    order = Order.objects.get(id=order_id)
                    order.status = target_status
                    if target_status == 'collected':
                        order.is_paid = True
                    order.save()
                    
                    # Send notification if ready
                    if target_status == 'ready':
                        from orders.utils import send_order_ready_email
                        try:
                            send_order_ready_email(order)
                        except Exception:
                            pass # Fail silently for email in bulk to avoid blocking
                    
                    updated_count += 1
                except Order.DoesNotExist:
                    continue
            
            if updated_count > 0:
                messages.success(request, f'Successfully updated {updated_count} orders to {target_status}')
            else:
                messages.warning(request, 'No orders were updated')
        return redirect('kitchen_dashboard')

    # Handle Menu Toggle (Kitchen can also manage availability)
    if request.method == 'POST' and 'toggle_item' in request.POST:
        item_id = request.POST.get('item_id')
        from menu.services import toggle_menu_item_availability
        success, item, msg = toggle_menu_item_availability(item_id)
        
        # Return JSON for AJAX requests
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            if success:
                return JsonResponse({
                    'status': 'success',
                    'is_available': item.is_available,
                    'item_id': item.id,
                    'message': msg
                })
            else:
                return JsonResponse({'status': 'error', 'message': msg}, status=404)
        
        if success:
            messages.info(request, msg)
        return redirect('kitchen_dashboard')

    # Handle single order status update
    if request.method == 'POST' and 'order_id' in request.POST:
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('status')
        try:
            order = Order.objects.get(id=order_id)
            old_status = order.status
            order.status = new_status
            if new_status == 'collected':
                order.is_paid = True
            order.save()
            
            # Send notification email if order is ready
            if new_status == 'ready':
                from orders.utils import send_order_ready_email
                send_order_ready_email(order)
            
            # Optional: success message for standard flow
            messages.success(request, f'Order {order.token_number}: {old_status} → {new_status}')

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': f'Order {order.token_number} updated to {new_status}'
                })

        except Order.DoesNotExist:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Order not found'}, status=404)
            messages.error(request, 'Order not found')
        return redirect('kitchen_dashboard')
    
    # Filter orders
    status_filter = request.GET.get('status', 'active')
    search_query = request.GET.get('search', '').strip()
    
    orders = Order.objects.all()
    
    if search_query:
        orders = orders.filter(
            Q(token_number__icontains=search_query) | 
            Q(user__username__icontains=search_query)
        ).order_by('-created_at')
    elif status_filter == 'all':
        orders = orders.filter(
            status__in=['pending', 'confirmed', 'preparing', 'ready']
        ).order_by('created_at')
    elif status_filter == 'active':
        orders = orders.filter(
            status__in=['pending', 'confirmed', 'preparing', 'ready']
        ).order_by('created_at')  # Oldest first for FIFO
    elif status_filter == 'pending':
        orders = orders.filter(status__in=['pending', 'confirmed']).order_by('created_at')
    else:
        orders = orders.filter(status=status_filter).order_by('-created_at')
    
    # Order counts by status
    # Pending now includes both unconfirmed and confirmed-waiting
    pending_count = Order.objects.filter(status__in=['pending', 'confirmed']).count()
    preparing_count = Order.objects.filter(status='preparing').count()
    ready_count = Order.objects.filter(status='ready').count()
    
    # Calculate completed today
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    completed_today = Order.objects.filter(
        status='collected',
        updated_at__gte=today_start
    ).count()
    
    # Menu Stats for the new right panel
    menu_items_qs = MenuItem.objects.exclude(category__name='Non-Veg')
    menu_count = menu_items_qs.count()
    menu_added_today = menu_items_qs.filter(created_at__gte=today_start).count()
    
    context = {
        'orders': orders,
        'completed_today': completed_today,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'preparing_count': preparing_count,
        'ready_count': ready_count,
        'search_query': search_query,
        'menu_items': menu_items_qs.order_by('category', 'name'),
        'menu_count': menu_count,
        'menu_added_today': menu_added_today,
        'active_page': 'kitchen',
    }

    if request.GET.get('partial') == 'true':
        html = render_to_string('includes/kitchen_order_grid.html', context, request=request)
        return JsonResponse({
            'html': html,
            'counts': {
                'pending': pending_count,
                'preparing': preparing_count,
                'ready': ready_count
            }
        })

    return render(request, 'accounts/kitchen_dashboard.html', context)


@login_required
def kitchen_sales_summary(request):
    """JSON API for kitchen sales analytics with date range filter"""
    if request.user.profile.role not in ['kitchen', 'admin']:
        return JsonResponse({'error': 'Access denied'}, status=403)

    from django.db.models.functions import ExtractHour, TruncDate
    from datetime import timedelta

    today = timezone.now().date()
    date_range = request.GET.get('range', 'all')
    completed_statuses = ['delivered', 'collected']

    # Determine date filter
    if date_range == 'today':
        base_orders = Order.objects.filter(created_at__date=today)
        range_label = "Today"
    elif date_range == 'week':
        start = today - timedelta(days=7)
        base_orders = Order.objects.filter(created_at__date__gte=start)
        range_label = "Last 7 Days"
    elif date_range == 'month':
        start = today - timedelta(days=30)
        base_orders = Order.objects.filter(created_at__date__gte=start)
        range_label = "Last 30 Days"
    else:
        base_orders = Order.objects.all()
        range_label = "All Time"

    completed_orders = base_orders.filter(status__in=completed_statuses)
    non_cancelled = base_orders.exclude(status='cancelled')

    # --- Summary Stats ---
    total_orders = base_orders.count()
    completed_count = completed_orders.count()
    total_revenue = completed_orders.filter(is_paid=True).aggregate(
        total=Sum('total_amount'))['total'] or 0
    total_items_sold = OrderItem.objects.filter(
        order__in=completed_orders
    ).aggregate(total=Sum('quantity'))['total'] or 0
    avg_order_value = completed_orders.filter(is_paid=True).aggregate(
        avg=Avg('total_amount'))['avg'] or 0
    cancelled_count = base_orders.filter(status='cancelled').count()
    pending_revenue = non_cancelled.filter(is_paid=False).aggregate(
        total=Sum('total_amount'))['total'] or 0

    # --- Top 5 Selling Items ---
    top_items = (
        OrderItem.objects.filter(order__in=completed_orders)
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
    top_sellers = [
        {'name': item['item_name'], 'qty': item['qty'],
         'revenue': float(item['revenue'] or 0)}
        for item in top_items
    ]

    # --- Category Breakdown ---
    cat_data = (
        OrderItem.objects.filter(order__in=completed_orders, menu_item__isnull=False)
        .values('menu_item__category__name')
        .annotate(
            qty=Sum('quantity'),
            revenue=Sum(ExpressionWrapper(
                F('price') * F('quantity'),
                output_field=DecimalField()
            ))
        )
        .order_by('-revenue')
    )
    categories = [
        {'name': c['menu_item__category__name'] or 'Other',
         'qty': c['qty'], 'revenue': float(c['revenue'] or 0)}
        for c in cat_data
    ]

    # --- Trend Data ---
    if date_range == 'today':
        # Hourly trend for today
        hourly = (
            base_orders.exclude(status='cancelled')
            .annotate(hour=ExtractHour('created_at'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('hour')
        )
        hourly_trend = {h['hour']: h['count'] for h in hourly}
        trend_data = [
            {'label': f"{h}:00", 'count': hourly_trend.get(h, 0)}
            for h in range(7, 23)
        ]
        trend_type = 'hourly'
    else:
        # Daily trend for other ranges
        daily = (
            base_orders.exclude(status='cancelled')
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )
        trend_data = [
            {'label': d['day'].strftime('%b %d'), 'count': d['count']}
            for d in daily if d['day']
        ]
        trend_type = 'daily'

    # --- Payment Method Split ---
    payment_data = (
        completed_orders.filter(is_paid=True)
        .values('payment_method')
        .annotate(
            count=Count('id'),
            total=Sum('total_amount')
        )
        .order_by('-total')
    )
    payments = [
        {'method': p['payment_method'].upper(),
         'count': p['count'], 'total': float(p['total'] or 0)}
        for p in payment_data
    ]

    return JsonResponse({
        'range_label': range_label,
        'summary': {
            'total_orders': total_orders,
            'completed_orders': completed_count,
            'total_revenue': float(total_revenue),
            'total_items_sold': total_items_sold,
            'avg_order_value': round(float(avg_order_value), 2),
            'cancelled_count': cancelled_count,
            'pending_revenue': float(pending_revenue),
        },
        'top_sellers': top_sellers,
        'categories': categories,
        'trend': trend_data,
        'trend_type': trend_type,
        'payments': payments,
    })

@login_required
def feedback_view(request):
    """View and submit user feedback"""
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        rating_str = request.POST.get('rating', '0')
        
        try:
            rating = int(rating_str)
        except (ValueError, TypeError):
            rating = 0

        if not subject or not message:
            messages.error(request, 'Please provide both subject and message.')
        else:
            Feedback.objects.create(
                user=request.user,
                subject=subject,
                message=message,
                rating=rating,
                status='open'
            )
            messages.success(request, 'Thank you! Your feedback has been submitted.')
            return redirect('user_feedback')

    user_feedbacks = Feedback.objects.filter(user=request.user)
    
    context = {
        'feedbacks': user_feedbacks,
        'active_page': 'feedback'
    }
    return render(request, 'accounts/user_feedback.html', context)


@login_required
def profile_view(request):
    """User profile view — view and edit profile details."""
    user = request.user
    profile = user.profile
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        # Validate
        if len(full_name) > 100:
            messages.error(request, 'Name is too long (max 100 characters)')
            return redirect('profile')
        
        if not phone:
            messages.error(request, 'Phone number is required')
            return redirect('profile')
            
        if not PHONE_REGEX.match(phone):
            messages.error(request, 'Please enter a valid 10-digit phone number')
            return redirect('profile')
        
        # Check phone uniqueness (if changed)
        if phone and phone != profile.phone:
            from .models import UserProfile
            if UserProfile.objects.filter(phone=phone).exclude(user=user).exists():
                messages.error(request, 'This phone number is already linked to another account')
                return redirect('profile')
        
        profile.full_name = full_name
        profile.phone = phone
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    # Order stats
    order_count = Order.objects.filter(user=user).exclude(status='cancelled').count()
    total_spent = Order.objects.filter(user=user, status='completed').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Recent orders for Past Orders display
    recent_orders = Order.objects.filter(user=user).exclude(
        status='payment_pending'
    ).prefetch_related('items').order_by('-created_at')
    
    # Favourite items
    favorite_items = Favorite.objects.filter(user=user).select_related('menu_item').order_by('-created_at')
    
    # Wallet transactions
    from payments.models import WalletTransaction
    wallet_transactions = WalletTransaction.objects.filter(user=user).order_by('-created_at')[:20]
    
    context = {
        'profile': profile,
        'order_count': order_count,
        'total_spent': total_spent,
        'recent_orders': recent_orders,
        'favorite_items': favorite_items,
        'wallet_transactions': wallet_transactions,
        'active_page': 'profile'
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def deactivate_account_view(request):
    """Hard-delete user account from database. Requires password confirmation."""
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm', '')
        
        if confirm != 'DEACTIVATE':
            messages.error(request, 'Please type DEACTIVATE to confirm')
            return redirect('profile')
        
        # Verify password (phone-only users don't have passwords)
        if request.user.has_usable_password():
            if not request.user.check_password(password):
                messages.error(request, 'Incorrect password')
                return redirect('profile')
        
        # Release the college/staff ID so it can be reused for registration
        user = request.user
        try:
            profile = user.profile
            if profile.college_id:
                if profile.role == 'student':
                    from .models import ValidStudent
                    ValidStudent.objects.filter(register_no=profile.college_id).update(is_registered=False)
                elif profile.role == 'teacher':
                    from .models import ValidStaff
                    ValidStaff.objects.filter(staff_id=profile.college_id).update(is_registered=False)
        except Exception:
            pass  # Don't block deletion if something goes wrong

        # Log the user out first, then permanently delete the account
        logout(request)
        user.delete()
        
        messages.success(request, 'Your account has been permanently deleted.')
        return redirect('home')
    
    return redirect('profile')


# ─── OTP-Based Password Reset ───────────────────────────────────────────

def forgot_password_view(request):
    """Step 1: Enter email → send password reset OTP."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Please enter your email address.')
            return render(request, 'accounts/forgot_password.html')

        from .email_otp import (
            generate_otp, store_pw_reset_otp,
            send_pw_reset_otp_email, can_resend_pw_reset, mark_resend_pw_reset,
        )

        # Always show success to prevent email enumeration
        user = User.objects.filter(email=email).first()

        if user and can_resend_pw_reset(email):
            otp = generate_otp()
            store_pw_reset_otp(email, otp)
            mark_resend_pw_reset(email)
            send_pw_reset_otp_email(email, otp)

        # Store email in session regardless (prevents enumeration)
        request.session['pw_reset_email'] = email
        request.session.pop('pw_reset_verified', None)
        messages.success(request, 'If an account with that email exists, a verification code has been sent.')
        return redirect('forgot_password_verify')

    # GET: check if username was passed from login page
    username = request.GET.get('username', '').strip()
    if username:
        user = User.objects.filter(username=username).first()
        if user and user.email:
            email = user.email.lower()
            from .email_otp import (
                generate_otp, store_pw_reset_otp,
                send_pw_reset_otp_email, can_resend_pw_reset, mark_resend_pw_reset,
            )
            if can_resend_pw_reset(email):
                otp = generate_otp()
                store_pw_reset_otp(email, otp)
                mark_resend_pw_reset(email)
                send_pw_reset_otp_email(email, otp)
            request.session['pw_reset_email'] = email
            request.session.pop('pw_reset_verified', None)
            messages.success(request, 'If an account with that email exists, a verification code has been sent.')
            return redirect('forgot_password_verify')

    return render(request, 'accounts/forgot_password.html')


def forgot_password_verify_view(request):
    """Step 2: Enter 6-digit OTP to verify identity."""
    email = request.session.get('pw_reset_email', '')

    if not email:
        messages.error(request, 'Please enter your email first.')
        return redirect('forgot_password')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()

        if not entered_otp or len(entered_otp) != 6:
            messages.error(request, 'Please enter the full 6-digit code.')
            return render(request, 'accounts/forgot_password_verify.html', {'email': email})

        from .email_otp import verify_pw_reset_otp
        success, message = verify_pw_reset_otp(email, entered_otp)

        if success:
            request.session['pw_reset_verified'] = True
            return redirect('forgot_password_reset')
        else:
            messages.error(request, message)
            return render(request, 'accounts/forgot_password_verify.html', {'email': email})

    return render(request, 'accounts/forgot_password_verify.html', {'email': email})


def forgot_password_resend_view(request):
    """Resend password reset OTP with cooldown protection."""
    if request.method != 'POST':
        return redirect('forgot_password_verify')

    email = request.POST.get('email', '').strip().lower() or request.session.get('pw_reset_email', '')

    if not email:
        messages.error(request, 'No email address found. Please start over.')
        return redirect('forgot_password')

    from .email_otp import (
        generate_otp, store_pw_reset_otp,
        send_pw_reset_otp_email, can_resend_pw_reset, mark_resend_pw_reset,
    )

    if not can_resend_pw_reset(email):
        messages.warning(request, 'Please wait before requesting a new code.')
        return redirect('forgot_password_verify')

    user = User.objects.filter(email=email).first()
    if user:
        otp = generate_otp()
        store_pw_reset_otp(email, otp)
        mark_resend_pw_reset(email)
        send_pw_reset_otp_email(email, otp)

    messages.success(request, 'A new code has been sent to your email.')
    request.session['pw_reset_email'] = email
    return redirect('forgot_password_verify')


def forgot_password_reset_view(request):
    """Step 3: Set new password (only accessible after OTP verified)."""
    email = request.session.get('pw_reset_email', '')
    verified = request.session.get('pw_reset_verified', False)

    if not email or not verified:
        messages.error(request, 'Please verify your identity first.')
        return redirect('forgot_password')

    if request.method == 'POST':
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/forgot_password_reset.html', {'email': email})

        # Validate password strength
        from django.contrib.auth.password_validation import validate_password
        try:
            user = User.objects.get(email=email)
            validate_password(password1, user=user)
        except User.DoesNotExist:
            messages.error(request, 'Account not found. Please start over.')
            return redirect('forgot_password')
        except ValidationError as e:
            for error in e:
                messages.error(request, error)
            return render(request, 'accounts/forgot_password_reset.html', {'email': email})

        # Set new password
        user.set_password(password1)
        user.save()

        # Clean up session
        request.session.pop('pw_reset_email', None)
        request.session.pop('pw_reset_verified', None)

        messages.success(request, 'Password changed successfully! Please log in with your new password.')
        return redirect('login')

    return render(request, 'accounts/forgot_password_reset.html', {'email': email})



@login_required
def complete_profile_view(request):
    """View to force users (like Google log-ins) to complete their profile"""
    profile = request.user.profile
    
    if request.method == 'POST':
        college_id = request.POST.get('college_id', '').strip()
        phone = request.POST.get('phone', '').strip()
        role = profile.role
        
        # Phone Validation
        import re
        if not phone or not re.match(r'^[6-9]\d{9}$', phone):
            messages.error(request, 'Please enter a valid 10-digit phone number.')
            return render(request, 'accounts/complete_profile.html', {'college_id': college_id, 'phone': phone})
            
        # College ID Validation
        if role == 'student':
            if not college_id:
                messages.error(request, 'Register Number is required.')
                return render(request, 'accounts/complete_profile.html', {'college_id': college_id, 'phone': phone})
            try:
                from .models import ValidStudent
                valid_student = ValidStudent.objects.get(register_no=college_id)
                if valid_student.is_registered:
                    messages.error(request, 'This Register Number is already associated with an account.')
                    return render(request, 'accounts/complete_profile.html', {'college_id': college_id, 'phone': phone})
                valid_student.is_registered = True
                valid_student.save()
            except ValidStudent.DoesNotExist:
                messages.error(request, 'Invalid Register Number. Please contact admin.')
                return render(request, 'accounts/complete_profile.html', {'college_id': college_id, 'phone': phone})
                
        elif role == 'teacher':
            if not college_id:
                messages.error(request, 'Staff ID is required.')
                return render(request, 'accounts/complete_profile.html', {'college_id': college_id, 'phone': phone})
            try:
                from .models import ValidStaff
                valid_staff = ValidStaff.objects.get(staff_id=college_id)
                if valid_staff.is_registered:
                    messages.error(request, 'This Staff ID is already associated with an account.')
                    return render(request, 'accounts/complete_profile.html', {'college_id': college_id, 'phone': phone})
                valid_staff.is_registered = True
                valid_staff.save()
            except ValidStaff.DoesNotExist:
                messages.error(request, 'Invalid Staff ID. Please contact admin.')
                return render(request, 'accounts/complete_profile.html', {'college_id': college_id, 'phone': phone})

        # Save updates to profile
        profile.college_id = college_id
        profile.phone = phone
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('home')

    return render(request, 'accounts/complete_profile.html', {
        'college_id': profile.college_id,
        'phone': profile.phone,
        'role': profile.role
    })



from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def kitchen_scan_qr_api(request):
    """API endpoint for kitchen staff to mark an order as collected via QR scan"""
    try:
        # Check if user is kitchen staff
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'kitchen':
            return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
            
        qr_data = request.POST.get('qr_data', '')
        if not qr_data:
            return JsonResponse({'success': False, 'message': 'No QR data provided'}, status=400)
            
        # Parse ORDER:{token_number}|USER:{user}|TOTAL:{amount}
        # Example format from Order.qr_code_data
        parts = qr_data.split('|')
        token_number = None
        for part in parts:
            if part.startswith('ORDER:'):
                token_number = part.split(':')[1]
                break
                
        if not token_number:
            return JsonResponse({'success': False, 'message': 'Invalid QR code format'}, status=400)
            
        from orders.models import Order
        
        try:
            order = Order.objects.get(token_number=token_number)
            
            # Check if order can be collected
            if order.status == 'collected':
                return JsonResponse({
                    'success': False, 
                    'message': f'Order {token_number} is already collected.'
                })
                
            if order.status != 'ready':
                return JsonResponse({
                    'success': False, 
                    'message': f'Order {token_number} is currently "{order.get_status_display()}" and is not ready for collection yet.'
                })
            
            # Transition to collected
            order.status = 'collected'
            order.save()
            
            # Trigger channel update
            try:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    "kitchen_orders",
                    {
                        "type": "order_update",
                        "order_id": order.id,
                        "status": order.status
                    }
                )
            except Exception as e:
                print(f"WebSocket update failed: {str(e)}")
                
            return JsonResponse({
                'success': True,
                'message': f'Order {token_number} scanned and marked as Collected!',
                'token': token_number
            })
            
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Order not found'}, status=404)
            
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

