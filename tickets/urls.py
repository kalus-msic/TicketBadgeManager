from django.urls import path, include
from . import views

app_name = 'tickets'
urlpatterns = [
    # Global routes (no event context)
    path('', views.index, name='index'),
    path('check-server/', views.check_server_status, name='check_server_status'),
    path('ticket/<int:ticket_id>/qr-code/', views.generate_qr_code, name='generate_qr_code'),
    path('qr-code/', views.generate_qr_code, name='generate_qr_code_url'),

    # Event CRUD
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:event_pk>/edit/', views.event_edit, name='event_edit'),
    path('events/<int:event_pk>/delete/', views.event_delete, name='event_delete'),

    # Event-scoped routes
    path('events/<int:event_pk>/', include('tickets.event_urls')),
]
