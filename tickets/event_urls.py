from django.urls import path
from . import views

# These patterns are included under /events/<int:event_pk>/
urlpatterns = [
    # Tickets
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/create/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/detail/', views.ticket_detail_by_qr, name='ticket_detail_by_qr'),
    path('tickets/<int:pk>/edit/', views.ticket_edit, name='ticket_edit'),
    path('tickets/<int:pk>/delete/', views.ticket_delete, name='ticket_delete'),
    path('tickets/reset/', views.reset_ticket_status, name='reset_ticket_status'),
    path('tickets/delete-multiple/', views.delete_tickets, name='delete_tickets'),
    path('tickets/export/', views.export_tickets_csv, name='export_tickets_csv'),
    path('tickets/export/xlsx/', views.export_tickets_xlsx, name='export_tickets_xlsx'),

    # Scanner
    path('scanner/', views.scanner_page, name='scanner'),
    path('scanner1/', views.scanner_page1, name='scanner1'),
    path('scanner2/', views.scanner_page2, name='scanner2'),
    path('verify/', views.verify_ticket, name='verify_ticket'),

    # Import
    path('import/', views.import_page, name='import_page'),
    path('import/replace/', views.import_replace_tickets, name='import_replace_tickets'),
    path('import/add/', views.import_add_tickets, name='import_add_tickets'),
    path('import/mapping/', views.import_mapping, name='import_mapping'),
    path('import/execute/', views.import_execute, name='import_execute'),
    path('import/preview/', views.import_preview, name='import_preview'),
    path('prepare-import/', views.merge_import, name='merge_import'),
    path('prepare-import/execute/', views.merge_execute, name='merge_execute'),

    # Management
    path('management/', views.ticket_management_dashboard, name='ticket_management'),

    # Logs
    path('logs/', views.ticket_log_list, name='ticket_log_list'),
    path('delete_logs/', views.delete_logs, name='delete_logs'),

    # Settings
    path('settings/', views.settings, name='settings'),
    path('settings/delete-all/', views.delete_all_data, name='delete_all_data'),
    path('settings/delete-checkins/', views.delete_checkins, name='delete_checkins'),
    path('settings/update-token/', views.update_eventee_token, name='update_eventee_token'),
    path('settings/required-fields', views.update_required_fields, name='update_required_fields'),
    path('settings/printer-settings', views.update_printer_settings, name='update_printer_settings'),

    # Special labels
    path('special-labels/', views.special_labels, name='special_labels'),
    path('special-labels/print/', views.print_special_labels, name='print_special_labels'),

    # Search
    path('search/tickets/', views.search_tickets_by_name, name='search_tickets'),

    # Kiosk
    path('kiosk/', views.kiosk_mode, name='kiosk'),
    path('kiosk/verify/', views.kiosk_verify, name='kiosk_verify'),

    # Bulk print
    path('bulk-print/', views.bulk_print, name='bulk_print'),
    path('bulk-print/execute/', views.bulk_print_execute, name='bulk_print_execute'),
]
