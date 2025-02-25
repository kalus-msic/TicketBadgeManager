from django import forms
from .models import Ticket

class CsvImportForm(forms.Form):
    csv_file = forms.FileField()

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['qr_code', 'name', 'company_name','email','status']
        widgets = {
            'qr_code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
