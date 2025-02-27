from django.db import models
from django.utils import timezone


class Ticket(models.Model):
    STATUS_CHOICES = [
        ('VALID', 'Valid'),
        ('USED', 'Used'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    GDPR_CHOICES = [
        ('NFO', 'Not Filled Out'),
        ('YES', 'Yes'),
        ('NO', 'No'),
    ]
    
    qr_code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='VALID')
    gdpr = models.CharField(max_length=3, choices=GDPR_CHOICES, default='NFO')
    email = models.CharField(max_length=200)
    event_name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.company_name}"


class CheckIn(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    check_in_time = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.ticket.name} checked in at {self.check_in_time}"


class Log(models.Model):
    EVENT_CHOICES = [
        ('CHECKIN', 'Check-In'),
        ('UPDATE', 'Update'),
        ('OTHER', 'Other'),
        ('ERROR', 'Error'),
        ('SYSTEM', 'System'),
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
