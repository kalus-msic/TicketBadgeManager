from .dashboard_views import index
from .ticket_views import (
    ticket_list, ticket_detail, ticket_detail_by_qr,
    ticket_create, ticket_edit, ticket_delete,
    reset_ticket_status, delete_tickets, export_tickets_csv, export_tickets_xlsx
)
from .import_views import (
    import_page, import_replace_tickets, import_add_tickets,
    merge_import, import_mapping, import_execute, import_preview
)
from .scanner_views import (
    scanner_page, scanner_page1, scanner_page2,
    verify_ticket, check_server_status
)
from .settings_views import (
    settings, delete_all_data, delete_checkins,
    update_eventee_token, update_required_fields, update_printer_settings
)
from .log_views import ticket_log_list, delete_logs
from .management_views import ticket_management_dashboard
from .special_label_views import special_labels, print_special_labels
from .qr_views import generate_qr_code
from .search_views import search_tickets_by_name
from .kiosk_views import kiosk_mode, kiosk_verify
from .language_views import set_language_custom
from .bulk_print_views import bulk_print, bulk_print_execute
from .merge_views import merge_execute

__all__ = [
    'index',
    'ticket_list', 'ticket_detail', 'ticket_detail_by_qr',
    'ticket_create', 'ticket_edit', 'ticket_delete',
    'reset_ticket_status', 'delete_tickets', 'export_tickets_csv', 'export_tickets_xlsx',
    'import_page', 'import_replace_tickets', 'import_add_tickets', 'merge_import',
    'import_mapping', 'import_execute', 'import_preview',
    'scanner_page', 'scanner_page1', 'scanner_page2', 'verify_ticket',
    'check_server_status',
    'settings', 'delete_all_data', 'delete_checkins',
    'update_eventee_token', 'update_required_fields', 'update_printer_settings',
    'ticket_log_list', 'delete_logs',
    'ticket_management_dashboard',
    'special_labels', 'print_special_labels',
    'generate_qr_code',
    'search_tickets_by_name',
    'kiosk_mode', 'kiosk_verify',
    'set_language_custom',
    'bulk_print', 'bulk_print_execute',
    'merge_execute'
]