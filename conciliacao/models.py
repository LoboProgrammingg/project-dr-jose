# conciliacao/models.py
from django.db import models
from django.contrib.auth.models import User

class RelatorioConciliacao(models.Model):
    """
    Guarda as informações de um relatório de conciliação executado.
    O campo 'mes_ano_referencia' é a chave para o filtro solicitado.
    """
    # Este campo armazena a data de referência que o usuário irá inserir.
    mes_ano_referencia = models.CharField(max_length=7, help_text="Mês e ano da conciliação (ex: 07/2025)")
    data_execucao = models.DateTimeField(auto_now_add=True)
    executado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        # A ordenação já está correta, mostrando os mais recentes primeiro.
        ordering = ['-data_execucao']
        verbose_name = "Relatório de Conciliação"
        verbose_name_plural = "Relatórios de Conciliação"

    def __str__(self):
        return f"Relatório de {self.mes_ano_referencia} (executado em {self.data_execucao.strftime('%d/%m/%Y')})"

class Transacao(models.Model):
    """Guarda cada linha individual de um resultado de conciliação."""
    STATUS_CHOICES = [
        ('Conciliado', 'Conciliado'),
        ('DIVERGÊNCIA DE VALOR', 'Divergência de Valor'),
        ('PENDENTE (APENAS NO BANCO)', 'Pendente no Banco'),
        ('PENDENTE (APENAS NO GESTOR)', 'Pendente no Gestor'),
    ]

    relatorio = models.ForeignKey(RelatorioConciliacao, on_delete=models.CASCADE, related_name='transacoes')
    data = models.DateField()
    historico = models.CharField(max_length=255, blank=True, null=True)
    valor_banco = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    valor_gestor = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    diferenca = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)

    class Meta:
        ordering = ['data']
        verbose_name = "Transação Conciliada"
        verbose_name_plural = "Transações Conciliadas"

    def __str__(self):
        return f"{self.data.strftime('%d/%m/%Y')} - {self.status}"
