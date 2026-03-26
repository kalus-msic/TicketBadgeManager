import datetime
from django.db import migrations


def create_default_event(apps, schema_editor):
    """
    After the Event model is introduced (0017), existing tickets have event=None.
    Create one default Event and assign all orphaned tickets to it so the app
    remains functional after the update.
    """
    Ticket = apps.get_model('tickets', 'Ticket')
    Event = apps.get_model('tickets', 'Event')

    if not Ticket.objects.filter(event__isnull=True).exists():
        return

    default_event = Event.objects.create(
        name='Výchozí akce',
        date=datetime.date.today(),
        status='active',
    )

    Ticket.objects.filter(event__isnull=True).update(event=default_event)


def reverse_default_event(apps, schema_editor):
    Ticket = apps.get_model('tickets', 'Ticket')
    Ticket.objects.all().update(event=None)


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0017_event_model'),
    ]

    operations = [
        migrations.RunPython(create_default_event, reverse_default_event),
    ]
