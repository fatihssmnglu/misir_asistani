from django import forms
from .models import Field
from django import forms
from .models import Alert
from django import forms


class FieldForm(forms.ModelForm):
    class Meta:
        model = Field
        fields = [
            'village',
            'name',
            'crop_type',
            'area_size',
            'soil_type',
            'irrigation_type',
            'lat',
            'lon'
        ]
        labels = {
            'village': 'Köy',
            'name': 'Tarla Adı',
            'crop_type': 'Ürün Türü',
            'area_size': 'Alan (dönüm)',
            'soil_type': 'Toprak Türü',
            'irrigation_type': 'Sulama Türü',
            'lat': 'Enlem (lat)',
            'lon': 'Boylam (lon)',
        }
class AlertForm(forms.ModelForm):
    class Meta:
        model = Alert
        fields = ['title', 'message', 'severity', 'village', 'related_field']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3}),
        }
