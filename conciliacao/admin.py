# conciliacao/admin.py

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import RelatorioConciliacao, Transacao


class TransacaoInline(admin.TabularInline):
    """
    Permite visualizar as transações de um relatório diretamente na página
    de detalhes do RelatorioConciliacao.
    """

    model = Transacao
    # Define os campos que serão exibidos para cada transação
    fields = (
        'data',
        'historico',
        'status',
        'valor_banco',
        'valor_gestor',
        'diferenca',
    )
    # Torna todos os campos somente leitura
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(RelatorioConciliacao)
class RelatorioConciliacaoAdmin(admin.ModelAdmin):
    """
    Configuração avançada para a interface de administração do modelo RelatorioConciliacao.
    """

    inlines = [TransacaoInline]
    list_display = (
        'mes_ano_referencia',
        'data_execucao',
        'executado_por',
        'total_transacoes',
        'total_divergencias',
    )
    list_filter = ('mes_ano_referencia', 'executado_por')
    search_fields = ('mes_ano_referencia',)
    readonly_fields = ('data_execucao', 'executado_por')

    def total_transacoes(self, obj):
        return obj.transacoes.count()

    total_transacoes.short_description = 'Nº de Transações'

    def total_divergencias(self, obj):
        count = obj.transacoes.exclude(status='Conciliado').count()
        if count > 0:
            return format_html(f'<b style="color: red;">{count}</b>')
        return 0

    total_divergencias.short_description = 'Nº de Divergências'


# A classe TransacaoAdmin foi removida conforme solicitado.
