from django.contrib import admin
from .models import Ticket, CheckIn, Log, AppSettings


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['qr_code', 'name', 'company_name', 'status', 'created_at']
    list_filter = ['status', 'gdpr', 'invited', 'created_at']
    search_fields = ['qr_code', 'name', 'company_name', 'email']
    readonly_fields = ['created_at']


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'check_in_time']
    list_filter = ['check_in_time']
    search_fields = ['ticket__name', 'ticket__qr_code']
    raw_id_fields = ['ticket']


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'event_type', 'ticket', 'message']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['message', 'ticket__name', 'ticket_qr']
    readonly_fields = ['timestamp']


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ['__str__']
    
    def has_add_permission(self, request):
        # Only allow one instance of AppSettings
        return not AppSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of settings
        return False
