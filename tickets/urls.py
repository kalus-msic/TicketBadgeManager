from django.urls import path
from . import views


app_name = 'tickets'
urlpatterns = [
    # Main routes
    path('', views.index, name='index'),
    path('prepare-import/', views.merge_import, name='merge_import'),
    path('scanner/', views.scanner_page, name='scanner'),
    path('verify/', views.verify_ticket, name='verify_ticket'),
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('settings/', views.settings, name='settings'),
    path('settings/delete-all/', views.delete_all_data, name='delete_all_data'),
    path('settings/delete-checkins/', views.delete_checkins, name='delete_checkins'),
    path('settings/update-token/', views.update_eventee_token, name='update_eventee_token'),

    path('import/', views.import_page, name='import_page'),
    path('import/replace/', views.import_replace_tickets, name='import_replace_tickets'),
    path('import/add/', views.import_add_tickets, name='import_add_tickets'),
    path('import/mapping/', views.import_mapping, name='import_mapping'),
    path('import/execute/', views.import_execute, name='import_execute'),
    path('import/preview/', views.import_preview, name='import_preview'),
    path('management/', views.ticket_management_dashboard, name='ticket_management'),
    path('tickets/', views.ticket_list, name='ticket_list'),
    
    # Ticket detail routes
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),  # Access by ID
    path('tickets/detail/', views.ticket_detail_by_qr, name='ticket_detail_by_qr'),  # Access by QR code
    
    path('tickets/create/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:pk>/edit/', views.ticket_edit, name='ticket_edit'),
    path('tickets/<int:pk>/delete/', views.ticket_delete, name='ticket_delete'),
    path('tickets/reset/', views.reset_ticket_status, name='reset_ticket_status'),
    path('tickets/delete-multiple/', views.delete_tickets, name='delete_tickets'),
    path('tickets/export/', views.export_tickets_csv, name='export_tickets_csv'),
    path('scanner1/', views.scanner_page1, name='scanner1'),
    path('scanner2/', views.scanner_page2, name='scanner2'),
    path('logs/', views.ticket_log_list, name='ticket_log_list'),
    path('delete_logs/', views.delete_logs, name='delete_logs'),
    path('check-server/', views.check_server_status, name='check_server_status'),
    path("settings/required-fields", views.update_required_fields, name="update_required_fields"),
    
    # Special labels
    path('special-labels/', views.special_labels, name='special_labels'),
    path('special-labels/print/', views.print_special_labels, name='print_special_labels'),
    
    # QR code generation
    path('ticket/<int:ticket_id>/qr-code/', views.generate_qr_code, name='generate_qr_code'),
    
    # Search
    path('search/tickets/', views.search_tickets_by_name, name='search_tickets'),
    
    # Kiosk mode
    path('kiosk/', views.kiosk_mode, name='kiosk'),
    path('kiosk/verify/', views.kiosk_verify, name='kiosk_verify'),

]