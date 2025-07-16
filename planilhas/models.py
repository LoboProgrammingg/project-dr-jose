from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.serializers.json import DjangoJSONEncoder


class AnoPlanilha(models.Model):
    ano = models.PositiveIntegerField(
        unique=True, help_text='Ano de referência (ex: 2025)'
    )
    criado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='anos_criados'
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-ano']

    def __str__(self):
        return str(self.ano)


class Planilha(models.Model):
    ano_referencia = models.ForeignKey(
        AnoPlanilha, on_delete=models.CASCADE, related_name='planilhas_upload'
    )
    nome = models.CharField(
        max_length=200,
        help_text='Nome ou mês da planilha (ex: Balanço de Janeiro)',
    )
    arquivo = models.FileField(
        upload_to='planilhas/%Y/%m/',
        help_text='Arquivo Excel (.xlsx) ou CSV (.csv)',
    )
    adicionado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='planilhas_adicionadas',
    )

    conteudo_json = models.JSONField(
        blank=True,
        null=True,
        encoder=DjangoJSONEncoder,
        help_text='Conteúdo da planilha em formato JSON para visualização',
    )

    adicionado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-adicionado_em']

    def __str__(self):
        return f'{self.nome} - {self.ano_referencia.ano}'

    def get_absolute_url(self):
        return reverse('planilhas:detalhe_planilha', kwargs={'pk': self.pk})


class PlanilhaNativa(models.Model):
    ano_referencia = models.ForeignKey(
        AnoPlanilha, on_delete=models.CASCADE, related_name='planilhas_nativas'
    )
    nome = models.CharField(
        max_length=200,
        help_text='Nome da nova planilha (ex: Controle de Despesas)',
    )
    adicionado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='planilhas_nativas_adicionadas',
    )

    colunas = models.JSONField(
        default=list,
        encoder=DjangoJSONEncoder,
        help_text="Lista com os nomes das colunas. Ex: ['Data', 'Descrição', 'Valor']",
    )
    dados = models.JSONField(
        default=list,
        encoder=DjangoJSONEncoder,
        help_text='Lista de dicionários, onde cada dicionário é uma linha.',
    )

    adicionado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-adicionado_em']

    def __str__(self):
        return f'{self.nome} (Nativa) - {self.ano_referencia.ano}'

    def get_absolute_url(self):
        return reverse(
            'planilhas:editar_planilha_nativa', kwargs={'pk': self.pk}
        )
