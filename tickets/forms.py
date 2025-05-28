from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Ticket, AppSettings, DEFAULT_REQUIRED_TICKET_FIELDS

class CsvImportForm(forms.Form):
    csv_file = forms.FileField(label=_("CSV File"))

class TicketForm(forms.ModelForm):
    # Checkbox „Invite to Eventee“ zůstává vždy nepovinný
    invite_to_eventee = forms.BooleanField(
        required=False,
        label=_("Invite to Eventee"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Ticket
        fields = ['qr_code', 'name', 'company_name', 'email', 'status']
        widgets = {
            'qr_code':       forms.TextInput(attrs={'class': 'form-control'}),
            'name':          forms.TextInput(attrs={'class': 'form-control'}),
            'company_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':         forms.TextInput(attrs={'class': 'form-control'}),
            'status':        forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1) Try to load saved required fields
        settings_obj = AppSettings.objects.first()
        if settings_obj and settings_obj.required_ticket_fields:
            required = settings_obj.required_ticket_fields
        else:
            # If nothing is saved yet, use defaults
            required = DEFAULT_REQUIRED_TICKET_FIELDS

        # 2) Dynamically mark fields as required / optional
        for name, field in self.fields.items():
            if name in ("invite_to_eventee", "qr_code"):
                    continue # Keep checkbox always optional

            field.required = name in required
            if field.required:
                field.widget.attrs['required'] = 'required'
            else:
                field.widget.attrs.pop('required', None)

        # 3) Pre-fill checkbox for editing existing ticket
        if self.instance and self.instance.pk:
            self.fields['invite_to_eventee'].initial = self.instance.invited
        else:
            # 4) Generate QR code for new tickets
            self.fields['qr_code'].initial = self._generate_qr_code()
    
    def _generate_qr_code(self):
        """Generate QR code in format YYYYMMDDxxxx"""
        from django.utils import timezone
        from django.db.models import Count
        
        today = timezone.now()
        date_prefix = today.strftime('%Y%m%d')
        
        # Count tickets created today
        today_count = Ticket.objects.filter(
            qr_code__startswith=date_prefix
        ).count()
        
        # Generate new number with zero padding
        new_number = str(today_count).zfill(4)
        
        return f"{date_prefix}{new_number}"


class SpecialLabelForm(forms.Form):
    """Form for printing special labels (Press, Host, etc.)"""
    name = forms.CharField(
        max_length=200,
        label=_("Name"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('e.g. PRESS, HOST, John Doe')})
    )
    company_name = forms.CharField(
        max_length=200,
        required=False,
        label=_("Company"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Optional')})
    )
    quantity = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=1,
        label=_("Quantity"),
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    printer = forms.ChoiceField(
        choices=[
            ('TDP-2251', _('Printer 1')),
            ('TDP-2252', _('Printer 2')),
        ],
        label=_("Printer"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )