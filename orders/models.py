from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from menu.models import MenuItem
import random
import string
import qrcode
import io
import base64

# ===== COUPON MODEL =====

class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percentage (%)'),
        ('flat', 'Flat Amount (₹)'),
    ]

    code = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=200, blank=True,
                                   help_text="Short description shown to user (e.g., '50% off Breakfast!')")
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percent')
    discount_value = models.DecimalField(max_digits=6, decimal_places=2,
                                         help_text="Percent (0-100) or flat ₹ amount")
    min_order_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                           help_text="Minimum cart subtotal required")
    max_uses = models.PositiveIntegerField(default=0,
                                           help_text="0 = unlimited uses")
    uses_count = models.PositiveIntegerField(default=0, editable=False)
    one_per_user = models.BooleanField(default=True,
                                       help_text="Each user can use this coupon only once")
    single_item_only = models.BooleanField(default=False,
                                           help_text="Discount applies to one item only (cheapest)")
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True,
                                       help_text="Leave blank for no expiry")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.code

    def calculate_discount(self, subtotal, cheapest_item_price=None):
        """Return the discount amount for a given subtotal (Decimal).
        If single_item_only is True, discount is based on cheapest_item_price."""
        from decimal import Decimal
        base = cheapest_item_price if (self.single_item_only and cheapest_item_price) else subtotal
        if self.discount_type == 'percent':
            return (base * self.discount_value / Decimal('100')).quantize(Decimal('0.01'))
        else:  # flat
            return min(self.discount_value, base)

    def is_valid(self, subtotal, user=None):
        """Returns (bool, error_message). True if coupon can be applied."""
        if not self.is_active:
            return False, 'This coupon is no longer active.'
        now = timezone.now()
        if now < self.valid_from:
            return False, 'This coupon is not valid yet.'
        if self.valid_until and now > self.valid_until:
            return False, 'This coupon has expired.'
        if self.max_uses > 0 and self.uses_count >= self.max_uses:
            return False, 'This coupon has reached its usage limit.'
        if subtotal < self.min_order_amount:
            return False, f'Minimum order of ₹{self.min_order_amount} required for this coupon.'
        # Per-user one-time check
        if self.one_per_user and user:
            from orders.models import Order
            already_used = Order.objects.filter(
                user=user, coupon=self
            ).exclude(status='cancelled').exists()
            if already_used:
                return False, 'You have already used this coupon.'
        return True, ''


# ===== TOKEN GENERATION =====

def generate_token():
    """Generate a random token like TKN-A1B2C3 with retry on collision"""
    for _ in range(10):
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        numbers = ''.join(random.choices(string.digits, k=3))
        token = f"TKN-{letters}{numbers}"
        if not Order.objects.filter(token_number=token).exists():
            return token
    # Fallback: longer token that is virtually collision-proof
    return f"TKN-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('payment_pending', 'Payment Pending'),
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('ready', 'Ready'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('collected', 'Collected'),
        ('cancelled', 'Cancelled'),
    ]

    # Valid status transitions (state machine)
    VALID_TRANSITIONS = {
        'payment_pending': ['pending', 'confirmed', 'cancelled'],
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['preparing', 'cancelled'],
        'preparing': ['ready', 'cancelled'],
        'ready': ['out_for_delivery', 'collected'],
        'out_for_delivery': ['delivered'],
        'delivered': [],
        'collected': [],
        'cancelled': [],
    }
    
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('wallet', 'Wallet'),
    ]
    
    DELIVERY_TYPE_CHOICES = [
        ('pickup', 'Pickup at Counter'),
        ('classroom', 'Deliver to Classroom'),
        ('staffroom', 'Deliver to Staffroom'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    token_number = models.CharField(max_length=20, unique=True, default=generate_token)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='payment_pending')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cash')
    is_paid = models.BooleanField(default=False)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                          help_text="Discount applied via coupon")
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='orders')
    special_instructions = models.TextField(blank=True)
    
    # Delivery options
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_TYPE_CHOICES, default='pickup')
    delivery_location = models.CharField(max_length=50, blank=True, help_text="Classroom number or Staffroom number")
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scheduled_for = models.DateTimeField(null=True, blank=True, help_text="Requested delivery/pickup time for preorders")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status'], name='order_status_idx'),
            models.Index(fields=['created_at'], name='order_created_idx'),
            models.Index(fields=['user', 'status'], name='order_user_status_idx'),
            models.Index(fields=['status', 'created_at'], name='order_status_date_idx'),
        ]
    
    def __str__(self):
        return f"{self.token_number} - {self.user.username}"
    
    def can_transition_to(self, new_status):
        """Check if transition to new_status is valid"""
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])
    
    def transition_to(self, new_status):
        """Transition to new status if valid, returns True/False"""
        if self.can_transition_to(new_status):
            self.status = new_status
            return True
        return False
    
    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def qr_code_data(self):
        """Generate QR code as base64 data URL"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f"ORDER:{self.token_number}|USER:{self.user.username}|TOTAL:{self.total_amount}")
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.SET_NULL, null=True)
    item_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.IntegerField(default=1)
    
    def __str__(self):
        return f"{self.quantity}x {self.item_name}"
    
    def get_subtotal(self):
        return self.price * self.quantity

