from django import forms
from django.forms import inlineformset_factory
from .models import Producto, Venta, DetalleVenta


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'precio']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


DetalleVentaFormSet = inlineformset_factory(
    Venta,
    DetalleVenta,
    fields=['producto', 'cantidad'],
    extra=5,
    can_delete=False,
    widgets={
        'producto': forms.Select(attrs={'class': 'form-select'}),
        'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': '0'}),
    },
) 