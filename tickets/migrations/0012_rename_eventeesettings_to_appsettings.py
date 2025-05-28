# Generated manually to rename EventeeSettings to AppSettings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0011_alter_ticket_company_name'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='EventeeSettings',
            new_name='AppSettings',
        ),
        migrations.AlterModelOptions(
            name='appsettings',
            options={'verbose_name': 'Application Settings', 'verbose_name_plural': 'Application Settings'},
        ),
        migrations.RenameField(
            model_name='appsettings',
            old_name='api_token',
            new_name='eventee_api_token',
        ),
        migrations.AddField(
            model_name='appsettings',
            name='default_printer',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Default Printer'),
        ),
        migrations.AlterField(
            model_name='appsettings',
            name='eventee_api_token',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Eventee API Token'),
        ),
        migrations.AlterField(
            model_name='appsettings',
            name='required_ticket_fields',
            field=models.JSONField(blank=True, default=list, verbose_name='Required Ticket Fields'),
        ),
    ]