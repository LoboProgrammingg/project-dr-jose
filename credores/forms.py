# credores/forms.py

from django import forms
from .models import Credor, Pagamento

class CredorForm(forms.ModelForm):
    """
    Formulário limpo, pois o estilo é gerenciado globalmente
    no base.html com a tag <style type="text/tailwindcss">.
    """
    class Meta:
        model = Credor
        fields = ['nome', 'email', 'telefone', 'valor_inicial', 
                  'taxa_juros_mensal', 'descricao_divida', 'ativo']
        widgets = {
            'descricao_divida': forms.Textarea(attrs={'rows': 3}),
        }

class PagamentoForm(forms.ModelForm):
    """Formulário limpo para pagamentos."""
    class Meta:
        model = Pagamento
        fields = ['valor', 'data_pagamento', 'recibo', 'observacao']
        widgets = {
            'data_pagamento': forms.DateInput(attrs={'type': 'date'}),
            'valor': forms.NumberInput(attrs={'step': '0.01'}),
            'observacao': forms.TextInput(attrs={'placeholder': 'Ex: Pagamento parcial via PIX'}),
        }