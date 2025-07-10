# credores/admin.py

from django.contrib import admin
from .models import Credor, Pagamento

class PagamentoInline(admin.TabularInline):
    """Permite adicionar e ver pagamentos diretamente na página do Credor."""
    model = Pagamento
    extra = 1
    fields = ('valor', 'data_pagamento', 'observacao', 'recibo')
    readonly_fields = ('data_pagamento',)
    ordering = ('-data_pagamento',)

@admin.register(Credor)
class CredorAdmin(admin.ModelAdmin):
    """Configuração da interface de administração para Credores."""
    # Adicionamos as novas colunas para uma visão mais completa
    list_display = (
        'nome', 
        'valor_inicial', 
        'get_total_juros',
        'get_total_pagamentos', 
        'get_saldo_devedor', 
        'ativo',
    )
    search_fields = ('nome', 'email')
    list_filter = ('ativo',)
    inlines = [PagamentoInline]
    readonly_fields = ('get_total_pagamentos', 'get_total_juros', 'get_saldo_devedor')
    
    fieldsets = (
        ('Informações do Credor', {
            'fields': ('nome', 'email', 'telefone', 'ativo')
        }),
        ('Detalhes da Dívida', {
            'fields': ('valor_inicial', 'taxa_juros_mensal', 'descricao_divida')
        }),
        ('Resumo Financeiro (Calculado)', {
            'fields': ('get_total_juros', 'get_total_pagamentos', 'get_saldo_devedor')
        }),
    )

    # --- MÉTODOS ATUALIZADOS PARA USAR AS NOVAS PROPRIEDADES DO MODELO ---
    
    def get_total_pagamentos(self, obj):
        # Correção: Usa a nova propriedade 'total_pagamentos'
        return obj.total_pagamentos
    get_total_pagamentos.short_description = 'Total Pago'

    def get_total_juros(self, obj):
        # Novo método para exibir os juros
        return obj.total_juros_aplicados
    get_total_juros.short_description = 'Juros Aplicados'

    def get_saldo_devedor(self, obj):
        # Usa a propriedade 'saldo_devedor' que já está correta
        return obj.saldo_devedor
    get_saldo_devedor.short_description = 'Saldo Devedor'


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    """Configuração da interface de administração para Pagamentos."""
    list_display = ('credor', 'valor', 'data_pagamento')
    search_fields = ('credor__nome',)
    list_filter = ('data_pagamento',)