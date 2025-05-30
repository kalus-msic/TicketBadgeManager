# Generated migration for new event types

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0011_alter_ticket_company_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='log',
            name='event_type',
            field=models.CharField(choices=[('CHECKIN', 'Check-In'), ('UPDATE', 'Update'), ('CREATE', 'Create'), ('DELETE', 'Delete'), ('IMPORT', 'Import'), ('ERROR', 'Error'), ('SYSTEM', 'System'), ('OTHER', 'Other')], max_length=20),
        ),
    ]