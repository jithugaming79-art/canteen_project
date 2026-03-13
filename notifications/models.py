from django.db import models
from django.contrib.auth.models import User


class Offer(models.Model):
    """Promotional offer that can be sent to users via WhatsApp."""
    title = models.CharField(max_length=200, help_text="Offer headline, e.g. '50% OFF on Breakfast!'")
    description = models.TextField(help_text="Offer details shown in the message body")
    discount_code = models.CharField(max_length=50, blank=True, help_text="Optional coupon code")
    image = models.ImageField(upload_to='offers/', blank=True, null=True, help_text="Optional offer banner image")
    valid_from = models.DateTimeField(help_text="When the offer starts")
    valid_until = models.DateTimeField(help_text="When the offer expires")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} (until {self.valid_until.strftime('%d %b %Y')})"


class WhatsAppLog(models.Model):
    """Tracks every WhatsApp message sent."""
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('dry_run', 'Dry Run'),
    ]

    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='whatsapp_logs')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='whatsapp_logs')
    phone = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    whatsapp_message_id = models.CharField(max_length=100, blank=True, help_text="Message ID from WhatsApp API")
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'WhatsApp Message Log'
        verbose_name_plural = 'WhatsApp Message Logs'

    def __str__(self):
        return f"{self.user.username} — {self.offer.title} ({self.status})"
