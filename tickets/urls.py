from django.urls import path
from . import views

app_name = 'tickets'
urlpatterns = [
    # Existující cesty...
    path('', views.index, name='index'),
    path('prepare-import/', views.merge_import, name='merge_import'),
    path('scanner/', views.scanner_page, name='scanner'),
    path('verify/', views.verify_ticket, name='verify_ticket'),
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('settings/', views.settings, name='settings'),
    path('settings/delete-all/', views.delete_all_data, name='delete_all_data'),
    path('settings/delete-checkins/', views.delete_checkins, name='delete_checkins'),
    path('import/', views.import_page, name='import_page'),
    path('import/replace/', views.import_replace_tickets, name='import_replace_tickets'),
    path('import/add/', views.import_add_tickets, name='import_add_tickets'),
    path('management/', views.ticket_management_dashboard, name='ticket_management'),
    path('tickets/', views.ticket_list, name='ticket_list'),
    
    # Upravené cesty pro detail ticketu
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),  # Pro přístup přes ID
    path('tickets/detail/', views.ticket_detail_by_qr, name='ticket_detail_by_qr'),  # Nová cesta pro QR kód
    
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

]