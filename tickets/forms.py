from django import forms
from .models import Ticket

class CsvImportForm(forms.Form):
    csv_file = forms.FileField()

class TicketForm(forms.ModelForm):
    invite_to_eventee = forms.BooleanField(
        required=False, 
        label="Invite to Eventee",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )    
    
    class Meta:
        model = Ticket
        fields = ['qr_code', 'name', 'company_name', 'email', 'status']
        widgets = {
            'qr_code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super(TicketForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['invite_to_eventee'].initial = self.instance.invited