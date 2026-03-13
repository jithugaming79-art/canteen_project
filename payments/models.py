from django.db import models
from django.contrib.auth.models import User
from orders.models import Order


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('wallet', 'Wallet'),
        ('card', 'Credit/Debit Card'),
        ('netbanking', 'Net Banking'),
        ('dodo', 'Dodo Payments'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    dodo_payment_id = models.CharField(max_length=200, blank=True, null=True, unique=True,
                                       help_text="Dodo Payments Payment ID")

    # Audit / traceability fields
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    gateway_response = models.JSONField(blank=True, null=True)

    # Refund tracking
    is_refunded = models.BooleanField(default=False)
    refunded_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.id} – {self.order.token_number} [{self.status}]"

    @property
    def is_successful(self):
        return self.status == 'completed'

    @property
    def display_method(self):
        return dict(self.METHOD_CHOICES).get(self.method, self.method)


class WalletTransaction(models.Model):
    TYPE_CHOICES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallet_transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.CharField(max_length=200)
    reference_id = models.CharField(max_length=100, blank=True,
                                    help_text="Idempotency key / external reference")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.transaction_type == 'credit' else '-'
        return f"{sign}₹{self.amount} ({self.description})"
