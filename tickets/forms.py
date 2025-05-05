from django import forms
from .models import Ticket, EventeeSettings, DEFAULT_REQUIRED_TICKET_FIELDS

class CsvImportForm(forms.Form):
    csv_file = forms.FileField()

class TicketForm(forms.ModelForm):
    # Checkbox „Invite to Eventee“ zůstává vždy nepovinný
    invite_to_eventee = forms.BooleanField(
        required=False,
        label="Invite to Eventee",
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

        # 1) Pokusíme se načíst uložená povinná pole
        settings_obj = EventeeSettings.objects.first()
        if settings_obj and settings_obj.required_ticket_fields:
            required = settings_obj.required_ticket_fields
        else:
            # pokud ještě není nic uloženo, použijeme výchozí
            required = DEFAULT_REQUIRED_TICKET_FIELDS

        # 2) Dynamicky označíme pole jako required / nepovinné
        for name, field in self.fields.items():
            if name == "invite_to_eventee":
                continue  # necháváme checkbox vždy nepovinný

            field.required = name in required
            if field.required:
                field.widget.attrs['required'] = 'required'
            else:
                field.widget.attrs.pop('required', None)

        # 3) Předvyplnění checkboxu pro editaci existujícího ticketu
        if self.instance and self.instance.pk:
            self.fields['invite_to_eventee'].initial = self.instance.invited