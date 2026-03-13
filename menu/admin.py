from django.contrib import admin
from django.utils.html import format_html
from .models import Category, MenuItem, Review

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'item_count')
    list_filter = ('is_active',)
    search_fields = ('name',)
    
    @admin.display(description='Items')
    def item_count(self, obj):
        return obj.items.count()

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'name', 'category', 'price', 'is_available', 'is_todays_special', 'is_vegetarian')
    list_filter = ('category', 'is_available', 'is_todays_special', 'is_vegetarian')
    search_fields = ('name', 'description')
    list_editable = ('price', 'is_available', 'is_todays_special')
    readonly_fields = ('created_at',)
    
    @admin.display(description='Image')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "-"

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'menu_item', 'rating_stars', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'menu_item__name', 'comment')
    readonly_fields = ('created_at',)
    
    @admin.display(description='Rating', ordering='rating')
    def rating_stars(self, obj):
        return "⭐" * obj.rating
