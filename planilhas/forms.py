# planilhas/forms.py
from django import forms
from .models import AnoPlanilha, Planilha, PlanilhaNativa


class AnoPlanilhaForm(forms.ModelForm):
    class Meta:
        model = AnoPlanilha
        fields = ['ano']
        widgets = {
            'ano': forms.NumberInput(
                attrs={'class': 'form-input', 'placeholder': 'Ex: 2025'}
            ),
        }


class PlanilhaForm(forms.ModelForm):
    class Meta:
        model = Planilha
        fields = ['ano_referencia', 'nome', 'arquivo']
        widgets = {
            'ano_referencia': forms.Select(attrs={'class': 'form-select'}),
            'nome': forms.TextInput(
                attrs={
                    'class': 'form-input',
                    'placeholder': 'Ex: Balanço de Janeiro',
                }
            ),
            'arquivo': forms.FileInput(attrs={'class': 'form-file-input'}),
        }


class PlanilhaNativaForm(forms.ModelForm):
    colunas_str = forms.CharField(
        label='Nomes das Colunas (separados por vírgula)',
        help_text='Ex: Data, Descrição, Valor, Categoria',
        widget=forms.TextInput(
            attrs={
                'class': 'form-input',
                'placeholder': 'Data, Descrição, Valor',
            }
        ),
    )

    class Meta:
        model = PlanilhaNativa
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(
                attrs={
                    'class': 'form-input',
                    'placeholder': 'Ex: Controle de Despesas de Viagem',
                }
            ),
        }
