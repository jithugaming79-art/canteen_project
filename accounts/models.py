from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    """Extended user profile with role and wallet"""
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
        ('kitchen', 'Kitchen Staff'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    full_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    college_id = models.CharField(max_length=30, blank=True)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    whatsapp_opt_in = models.BooleanField(default=True, help_text="Receive offer notifications via WhatsApp")
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_kitchen(self):
        return self.role == 'kitchen'

# Auto-create profile when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class ValidStudent(models.Model):
    """Whitelist of valid student registration numbers"""
    register_no = models.CharField(max_length=20, unique=True, help_text="e.g. 03SU23FC071")
    is_registered = models.BooleanField(default=False, help_text="True if a user has already registered with this ID")
    
    def __str__(self):
        return f"{self.register_no} ({'Registered' if self.is_registered else 'Available'})"


class ValidStaff(models.Model):
    """Whitelist of valid faculty/staff IDs"""
    staff_id = models.CharField(max_length=20, unique=True, help_text="e.g. 03SU26SI001 or 03SU26FI001")
    is_registered = models.BooleanField(default=False, help_text="True if a user has already registered with this ID")
    
    def __str__(self):
        return f"{self.staff_id} ({'Registered' if self.is_registered else 'Available'})"


class SystemSettings(models.Model):
    """Global system settings (Singleton pattern)"""
    delivery_fee = models.DecimalField(max_digits=6, decimal_places=2, default=10.00, help_text="Fee for classroom/staffroom delivery")
    upi_id = models.CharField(max_length=100, default='campusbites@ybl', help_text="Canteen UPI VPA")
    maintenance_mode = models.BooleanField(default=False, help_text="Disable new orders")
    
    class Meta:
        verbose_name_plural = "System Settings"
        
    def __str__(self):
        return "System Configuration"

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj


class Feedback(models.Model):
    """User feedback / complaints / suggestions"""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedbacks')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    rating = models.IntegerField(default=0, help_text="Overall rating 1-5, 0 means not rated")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    admin_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    VALID_TRANSITIONS = {
        'open': ['in_progress'],
        'in_progress': ['resolved'],
        'resolved': [],
    }
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} — {self.subject}"

    def can_transition_to(self, new_status):
        """Check if transitioning to the new status is allowed"""
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])
