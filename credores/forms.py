# credores/forms.py

from django import forms
from .models import Credor, Pagamento

class CredorForm(forms.ModelForm):
    """Formulário para Criar e Editar Credores."""
    class Meta:
        model = Credor
        fields = ['nome', 'email', 'telefone', 'valor_inicial', 'taxa_juros_mensal', 'descricao_divida', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'valor_inicial': forms.NumberInput(attrs={'class': 'form-control'}),
            'taxa_juros_mensal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descricao_divida': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class PagamentoForm(forms.ModelForm):
    """Formulário para adicionar um novo pagamento a um Credor."""
    class Meta:
        model = Pagamento
        fields = ['valor', 'data_pagamento', 'recibo', 'observacao']
        widgets = {
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'data_pagamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'recibo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'observacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Pagamento parcial via PIX'}),
        }