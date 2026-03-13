from django.contrib import admin, messages
from .models import Offer, WhatsAppLog
from .whatsapp import send_offer_to_users


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ['title', 'discount_code', 'valid_from', 'valid_until', 'is_active', 'messages_sent', 'created_at']
    list_filter = ['is_active', 'valid_from', 'valid_until']
    search_fields = ['title', 'description', 'discount_code']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['send_via_whatsapp']
    fields = ['title', 'description', 'discount_code', 'image', 'valid_from', 'valid_until', 'is_active']

    def messages_sent(self, obj):
        """Show count of successfully sent messages."""
        sent = obj.whatsapp_logs.filter(status__in=['sent', 'dry_run']).count()
        failed = obj.whatsapp_logs.filter(status='failed').count()
        if sent or failed:
            return f"✅ {sent}  ❌ {failed}"
        return "—"
    messages_sent.short_description = 'WhatsApp'

    @admin.action(description="📱 Send selected offers via WhatsApp")
    def send_via_whatsapp(self, request, queryset):
        total_sent = 0
        total_failed = 0
        total_skipped = 0

        for offer in queryset:
            if not offer.is_active:
                messages.warning(request, f"Skipped inactive offer: {offer.title}")
                continue

            results = send_offer_to_users(offer)
            total_sent += results['sent']
            total_failed += results['failed']
            total_skipped += results['skipped']

        msg_parts = []
        if total_sent:
            msg_parts.append(f"✅ {total_sent} sent")
        if total_failed:
            msg_parts.append(f"❌ {total_failed} failed")
        if total_skipped:
            msg_parts.append(f"⏭️ {total_skipped} skipped (already sent)")

        if msg_parts:
            messages.success(request, f"WhatsApp: {', '.join(msg_parts)}")
        else:
            messages.info(request, "No eligible users found (no phone numbers or all opted out).")


@admin.register(WhatsAppLog)
class WhatsAppLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'offer', 'phone', 'status', 'sent_at']
    list_filter = ['status', 'sent_at']
    search_fields = ['user__username', 'phone', 'offer__title']
    readonly_fields = ['offer', 'user', 'phone', 'status', 'whatsapp_message_id', 'error_message', 'sent_at']
    ordering = ['-sent_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
