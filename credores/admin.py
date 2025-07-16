from django.contrib import admin
from django.utils.html import format_html
from .models import Credor, Pagamento

admin.site.site_header = 'Painel Administrativo da Plataforma'
admin.site.site_title = 'Administração Financeira'
admin.site.index_title = 'Bem-vindo à Gestão do Sistema'


class PagamentoInline(admin.TabularInline):
    model = Pagamento
    extra = 1
    fields = ('data_pagamento', 'valor', 'observacao', 'recibo')
    readonly_fields = ('data_registro',)
    ordering = ('-data_pagamento',)


@admin.register(Credor)
class CredorAdmin(admin.ModelAdmin):
    inlines = [PagamentoInline]

    list_display = (
        'nome',
        'valor_inicial',
        'display_total_juros',
        'display_total_pagamentos',
        'display_saldo_devedor',
        'status_da_divida',
    )

    list_filter = ('ativo',)

    search_fields = ('nome', 'email')

    fieldsets = (
        ('Informações Pessoais', {'fields': ('nome', 'email', 'telefone')}),
        (
            'Detalhes da Dívida',
            {
                'fields': (
                    'descricao_divida',
                    'valor_inicial',
                    'taxa_juros_mensal',
                    'ativo',
                )
            },
        ),
        (
            'Valores Calculados (Apenas Leitura)',
            {
                'classes': ('collapse',),
                'fields': (
                    'data_criacao',
                    'juros_iniciais_aplicados',
                    'valor_atualizado_divida',
                    'saldo_devedor',
                ),
            },
        ),
    )

    readonly_fields = (
        'data_criacao',
        'juros_iniciais_aplicados',
        'valor_atualizado_divida',
        'saldo_devedor',
        'total_pagamentos',
        'total_juros_gerados',
    )

    actions = ['marcar_como_quitado', 'marcar_como_ativo']

    def display_total_juros(self, obj):
        return f'R$ {obj.total_juros_gerados:.2f}'

    display_total_juros.short_description = 'Total Juros'

    def display_total_pagamentos(self, obj):
        return f'R$ {obj.total_pagamentos:.2f}'

    display_total_pagamentos.short_description = 'Total Pago'

    def display_saldo_devedor(self, obj):
        saldo = obj.saldo_devedor
        cor = 'red' if saldo > 0 else 'green'
        return format_html(
            f'<span style="color: {cor}; font-weight: bold;">R$ {saldo:.2f}</span>'
        )

    display_saldo_devedor.short_description = 'Saldo Devedor'

    def status_da_divida(self, obj):
        if obj.ativo:
            return format_html(
                '<img src="/static/admin/img/icon-yes.svg" alt="Ativo"> Ativa'
            )
        else:
            return format_html(
                '<img src="/static/admin/img/icon-no.svg" alt="Quitado"> Quitada'
            )

    status_da_divida.short_description = 'Status'
    status_da_divida.admin_order_field = 'ativo'

    def marcar_como_quitado(self, request, queryset):
        rows_updated = queryset.update(ativo=False)
        self.message_user(
            request, f'{rows_updated} dívida(s) foram marcadas como quitadas.'
        )

    marcar_como_quitado.short_description = 'Marcar selecionadas como Quitadas'

    def marcar_como_ativo(self, request, queryset):
        rows_updated = queryset.update(ativo=True)
        self.message_user(
            request, f'{rows_updated} dívida(s) foram marcadas como Ativas.'
        )

    marcar_como_ativo.short_description = 'Marcar selecionadas como Ativas'


@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = (
        'credor',
        'data_pagamento',
        'valor',
        'observacao',
        'data_registro',
    )
    list_filter = ('data_pagamento', 'credor')
    search_fields = ('credor__nome', 'observacao')
    autocomplete_fields = ['credor']
    ordering = ('-data_pagamento',)
