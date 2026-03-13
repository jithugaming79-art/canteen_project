from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg

class Category(models.Model):
    """Food category like Breakfast, Lunch, Snacks"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name

class MenuItem(models.Model):
    """Food item in the menu"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='menu/', blank=True, null=True)
    preparation_time = models.IntegerField(default=10, help_text='Time in minutes')
    is_available = models.BooleanField(default=True)
    is_todays_special = models.BooleanField(default=False)
    is_vegetarian = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['is_available'], name='menu_available_idx'),
            models.Index(fields=['category', 'is_available'], name='menu_cat_avail_idx'),
            models.Index(fields=['is_todays_special'], name='menu_special_idx'),
        ]
    
    def __str__(self):
        return f"{self.name} - ₹{self.price}"
    
    @property
    def average_rating(self):
        """Calculate average rating from reviews"""
        avg = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0
    
    @property
    def review_count(self):
        """Get total number of reviews"""
        return self.reviews.count()


class Review(models.Model):
    """User review for a menu item"""
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True)
    admin_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'menu_item']  # One review per user per item
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.menu_item.name} ({self.rating}★)"


class Favorite(models.Model):
    """User's favorite menu items"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'menu_item']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} ❤️ {self.menu_item.name}"


