from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'resource', 'resource_id', 'user', 'ip_address', 'timestamp')
    list_filter = ('action', 'resource', 'timestamp')
    search_fields = ('resource_id', 'user__email', 'ip_address')
    readonly_fields = ('id', 'user', 'action', 'resource', 'resource_id',
                       'old_value', 'new_value', 'ip_address', 'user_agent', 'timestamp', 'extra')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
