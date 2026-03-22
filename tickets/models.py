from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('VALID', _('Valid')),
        ('USED', _('Used')),
        ('CANCELLED', _('Cancelled')),
    ]
    
    GDPR_CHOICES = [
        ('NFO', _('Not Filled Out')),
        ('YES', _('Yes')),
        ('NO', _('No')),
    ]
    
    qr_code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='VALID')
    gdpr = models.CharField(max_length=3, choices=GDPR_CHOICES, default='NFO')
    email = models.CharField(max_length=200, null=True, blank=True)
    event_name = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Invited to Eventee via API
    invited = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name} - {self.company_name}"


class CheckIn(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    check_in_time = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.ticket.name} checked in at {self.check_in_time}"


class Log(models.Model):
    EVENT_CHOICES = [
        ('CHECKIN', _('Check-In')),
        ('UPDATE', _('Update')),
        ('CREATE', _('Create')),
        ('DELETE', _('Delete')),
        ('IMPORT', _('Import')),
        ('PRINT', _('Print')),
        ('BULK_PRINT', _('Bulk Print')),
        ('ERROR', _('Error')),
        ('SYSTEM', _('System')),
        ('OTHER', _('Other')),
    ]
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )
    ticket_qr = models.CharField(max_length=100, null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        ticket_info = self.ticket_qr if self.ticket_qr else (self.ticket.qr_code if self.ticket else "Deleted Ticket")
        return f"{ticket_info} - {self.event_type} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
DEFAULT_REQUIRED_TICKET_FIELDS = [
    "name",
    "company_name",
    "email",
]

class AppSettings(models.Model):
    """General application settings."""
    # Eventee API settings
    eventee_api_token = models.CharField(max_length=255, blank=True, null=True, 
                                        verbose_name="Eventee API Token")
    
    # Ticket form settings
    required_ticket_fields = models.JSONField(default=list, blank=True,
                                            verbose_name="Required Ticket Fields")
    
    # Printer settings
    default_printer = models.CharField(max_length=255, blank=True, null=True,
                                     verbose_name="Default Printer")
    printer_1_name = models.CharField(max_length=255, default="TDP-2251",
                                      verbose_name="Printer 1 Name")
    printer_2_name = models.CharField(max_length=255, default="TDP-2252",
                                      verbose_name="Printer 2 Name")
    auto_print_on_scan = models.BooleanField(default=True,
                                           verbose_name="Automatically print labels when scanning")
    
    class Meta:
        verbose_name = "Application Settings"
        verbose_name_plural = "Application Settings"
    
    def __str__(self):
        return "Application Settings"