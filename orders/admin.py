from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('item_name', 'price', 'quantity', 'get_subtotal')
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('token_number', 'user_link', 'status_badge', 'total_amount', 'payment_info', 'created_at')
    list_filter = ('status', 'is_paid', 'payment_method', 'created_at')
    search_fields = ('token_number', 'user__username', 'user__email')
    inlines = [OrderItemInline]
    readonly_fields = ('token_number', 'created_at', 'total_amount', 'user')
    # date_hierarchy = 'created_at'  # Requires MySQL timezone tables on Windows
    ordering = ('-created_at',)
    actions = ['mark_confirmed', 'mark_preparing', 'mark_ready', 'mark_collected', 'mark_cancelled']
    
    fieldsets = (
        ('Order Details', {
            'fields': (('token_number', 'status'), 'created_at', 'user')
        }),
        ('Payment', {
            'fields': (('total_amount', 'payment_method'), 'is_paid')
        }),
        ('Delivery', {
            'fields': ('delivery_type', 'delivery_location', 'delivery_fee'),
            'classes': ('collapse',)
        }),
        ('Instructions', {
            'fields': ('special_instructions',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='User', ordering='user__username')
    def user_link(self, obj):
        return obj.user.username

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'confirmed': 'info',
            'preparing': 'primary',
            'ready': 'success',
            'collected': 'secondary',
            'cancelled': 'danger',
            'payment_pending': 'dark'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge badge-pill badge-{}">{}</span>',
            color,
            obj.get_status_display()
        )

    @admin.display(description='Payment')
    def payment_info(self, obj):
        icon = '✅' if obj.is_paid else '❌'
        return format_html('{} {}', icon, obj.payment_method.upper())

    # --- Actions ---
    @admin.action(description='Confirm selected orders')
    def mark_confirmed(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f"{updated} orders marked as Confirmed.")

    @admin.action(description='Start Preparing')
    def mark_preparing(self, request, queryset):
        updated = queryset.update(status='preparing')
        self.message_user(request, f"{updated} orders marked as Preparing.")

    @admin.action(description='Mark as Ready')
    def mark_ready(self, request, queryset):
        # Trigger emails/notifications logic here if needed, but update() is raw SQL
        # For signals to fire, we should loop. But for bulk admin actions, speed is key.
        # If we want signals:
        count = 0
        for order in queryset:
            order.status = 'ready'
            order.save() # triggers signals
            count += 1
        self.message_user(request, f"{count} orders marked as Ready.")

    @admin.action(description='Mark as Collected (Paid)')
    def mark_collected(self, request, queryset):
        queryset.update(status='collected', is_paid=True)
        self.message_user(request, f"{queryset.count()} orders marked as Collected.")

    @admin.action(description='Cancel Orders')
    def mark_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, f"{queryset.count()} orders Cancelled.")
