from django.contrib import admin
from .models import UserProfile, ValidStudent, ValidStaff

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'wallet_balance')
    list_filter = ('role',)
    search_fields = ('user__username', 'full_name', 'phone')
    list_editable = ('role', 'wallet_balance')

@admin.register(ValidStudent)
class ValidStudentAdmin(admin.ModelAdmin):
    list_display = ('register_no', 'is_registered')
    list_filter = ('is_registered',)
    search_fields = ('register_no',)

@admin.register(ValidStaff)
class ValidStaffAdmin(admin.ModelAdmin):
    list_display = ('staff_id', 'is_registered')
    list_filter = ('is_registered',)
    search_fields = ('staff_id',)

from .models import SystemSettings

@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'delivery_fee', 'maintenance_mode')
    list_editable = ('delivery_fee', 'maintenance_mode')
    
    # Prevent creating multiple instances
    def has_add_permission(self, request):
        return not SystemSettings.objects.exists()
