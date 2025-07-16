from django.db import models
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone


class Credor(models.Model):
    nome = models.CharField(
        max_length=200, help_text='Nome completo do credor'
    )
    email = models.EmailField(
        max_length=254,
        blank=True,
        null=True,
        help_text='Email do credor (opcional)',
    )
    telefone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Telefone do credor (opcional)',
    )

    valor_inicial = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Valor original do principal da dívida',
    )
    taxa_juros_mensal = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text='Taxa de juros mensal em porcentagem (ex: 1.00 para 1%)',
    )
    juros_iniciais_aplicados = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text='Juros calculados automaticamente no momento da criação da dívida',
    )

    descricao_divida = models.TextField(
        help_text='Detalhes sobre a origem da dívida'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(
        default=True, help_text='Marque se a dívida ainda está ativa/em aberto'
    )

    def __str__(self):
        return self.nome

    @property
    def total_pagamentos(self) -> Decimal:
        soma = (
            self.pagamentos.filter(valor__gt=0)
            .aggregate(total=Sum('valor'))
            .get('total')
        )
        return soma or Decimal('0.00')

    @property
    def total_juros_adicionais(self) -> Decimal:
        soma = (
            self.pagamentos.filter(valor__lt=0)
            .aggregate(total=Sum('valor'))
            .get('total')
        )
        return abs(soma or Decimal('0.00'))

    @property
    def total_juros_gerados(self) -> Decimal:
        return self.juros_iniciais_aplicados + self.total_juros_adicionais

    @property
    def valor_atualizado_divida(self) -> Decimal:
        return self.valor_inicial + self.total_juros_gerados

    @property
    def saldo_devedor(self) -> Decimal:
        return self.valor_atualizado_divida - self.total_pagamentos

    def aplicar_juros_mensal(self):
        if (
            not self.ativo
            or self.saldo_devedor <= 0
            or self.taxa_juros_mensal <= 0
        ):
            return None

        valor_juros = (
            self.saldo_devedor * (self.taxa_juros_mensal / 100)
        ).quantize(Decimal('0.01'))

        if valor_juros <= 0:
            return None

        juros_aplicados = Pagamento.objects.create(
            credor=self,
            valor=-valor_juros,
            data_pagamento=timezone.now().date(),
            observacao=f'Juros de {self.taxa_juros_mensal}% sobre saldo de R$ {self.saldo_devedor}',
        )
        return juros_aplicados


class Pagamento(models.Model):
    credor = models.ForeignKey(
        Credor, on_delete=models.CASCADE, related_name='pagamentos'
    )
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Valor do pagamento. Use um valor negativo para juros ou taxas.',
    )
    data_pagamento = models.DateField(
        help_text='Data em que o pagamento foi realizado'
    )
    recibo = models.ImageField(
        upload_to='recibos/',
        blank=True,
        null=True,
        help_text='Faça o upload do comprovante/recibo do pagamento',
    )
    observacao = models.CharField(
        max_length=200,
        blank=True,
        help_text="Observação sobre o pagamento (ex: 'Pagamento parcial via PIX')",
    )
    data_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pagamento de R$ {self.valor} para {self.credor.nome} em {self.data_pagamento.strftime('%d/%m/%Y')}"
