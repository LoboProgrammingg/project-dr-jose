# credores/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Credor, Pagamento

# Personalização do cabeçalho e título do site de administração
admin.site.site_header = "Painel Administrativo da Plataforma"
admin.site.site_title = "Administração Financeira"
admin.site.index_title = "Bem-vindo à Gestão do Sistema"


class PagamentoInline(admin.TabularInline):
    """
    Permite visualizar e adicionar pagamentos diretamente na página de um Credor.
    Isso cria uma experiência de gestão muito mais integrada.
    """
    model = Pagamento
    extra = 1  # Mostra um formulário extra para adicionar um novo pagamento.
    fields = ('data_pagamento', 'valor', 'observacao', 'recibo')
    readonly_fields = ('data_registro',)
    ordering = ('-data_pagamento',)


@admin.register(Credor)
class CredorAdmin(admin.ModelAdmin):
    """
    Configuração avançada para a interface de administração do modelo Credor.
    """
    # Exibe os pagamentos como um bloco dentro da página do credor
    inlines = [PagamentoInline]

    # Campos a serem exibidos na lista de credores
    list_display = (
        'nome',
        'valor_inicial',
        'display_total_juros', # Campo formatado
        'display_total_pagamentos', # Campo formatado
        'display_saldo_devedor', # Campo formatado
        'status_da_divida' # Campo com ícone visual
    )

    # Adiciona um filtro na barra lateral para dívidas ativas/quitadas
    list_filter = ('ativo',)

    # Permite a busca por nome ou email do credor
    search_fields = ('nome', 'email')

    # Organiza os campos no formulário de edição em seções lógicas
    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('nome', 'email', 'telefone')
        }),
        ('Detalhes da Dívida', {
            'fields': ('descricao_divida', 'valor_inicial', 'taxa_juros_mensal', 'ativo')
        }),
        ('Valores Calculados (Apenas Leitura)', {
            'classes': ('collapse',), # Seção recolhida por padrão
            'fields': ('data_criacao', 'juros_iniciais_aplicados', 'valor_atualizado_divida', 'saldo_devedor')
        }),
    )

    # Campos que são calculados e não devem ser editados manualmente
    readonly_fields = (
        'data_criacao', 'juros_iniciais_aplicados', 'valor_atualizado_divida',
        'saldo_devedor', 'total_pagamentos', 'total_juros_gerados'
    )

    # Ações personalizadas que podem ser executadas na lista de credores
    actions = ['marcar_como_quitado', 'marcar_como_ativo']

    # Funções para formatar a exibição dos valores monetários e status
    def display_total_juros(self, obj):
        return f"R$ {obj.total_juros_gerados:.2f}"
    display_total_juros.short_description = "Total Juros"

    def display_total_pagamentos(self, obj):
        return f"R$ {obj.total_pagamentos:.2f}"
    display_total_pagamentos.short_description = "Total Pago"

    def display_saldo_devedor(self, obj):
        saldo = obj.saldo_devedor
        cor = 'red' if saldo > 0 else 'green'
        return format_html(f'<span style="color: {cor}; font-weight: bold;">R$ {saldo:.2f}</span>')
    display_saldo_devedor.short_description = "Saldo Devedor"

    def status_da_divida(self, obj):
        if obj.ativo:
            return format_html('<img src="/static/admin/img/icon-yes.svg" alt="Ativo"> Ativa')
        else:
            return format_html('<img src="/static/admin/img/icon-no.svg" alt="Quitado"> Quitada')
    status_da_divida.short_description = 'Status'
    status_da_divida.admin_order_field = 'ativo'

    # Lógica para as ações em massa
    def marcar_como_quitado(self, request, queryset):
        rows_updated = queryset.update(ativo=False)
        self.message_user(request, f"{rows_updated} dívida(s) foram marcadas como quitadas.")
    marcar_como_quitado.short_description = "Marcar selecionadas como Quitadas"

    def marcar_como_ativo(self, request, queryset):
        rows_updated = queryset.update(ativo=True)
        self.message_user(request, f"{rows_updated} dívida(s) foram marcadas como Ativas.")
    marcar_como_ativo.short_description = "Marcar selecionadas como Ativas"


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    """
    Configuração para a interface de administração do modelo Pagamento.
    Útil para auditoria e visualização de todos os pagamentos do sistema.
    """
    list_display = ('credor', 'data_pagamento', 'valor', 'observacao', 'data_registro')
    list_filter = ('data_pagamento', 'credor')
    search_fields = ('credor__nome', 'observacao')
    autocomplete_fields = ['credor'] # Facilita a seleção do credor
    ordering = ('-data_pagamento',)

