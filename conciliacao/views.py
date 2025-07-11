# conciliacao/views.py
import json
from datetime import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import pandas as pd

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.db.models import Sum
from django.core.paginator import Paginator # <-- Importação adicionada

from . import services
from .models import RelatorioConciliacao, Transacao
from credores.models import Credor, Pagamento

# --- VIEWS DE PÁGINA E LÓGICA DE NEGÓCIO ---

@login_required
def dashboard(request):
    """
    A view do dashboard, que funciona como um motor de BI, preparando
    todos os dados para os KPIs e gráficos analíticos.
    """
    # (Lógica do dashboard permanece inalterada)
    credores_ativos = Credor.objects.filter(ativo=True)
    total_credores_ativos = credores_ativos.count()
    saldo_devedor_total = sum(c.saldo_devedor for c in credores_ativos)
    valor_total_emprestado = credores_ativos.aggregate(total=Sum('valor_inicial'))['total'] or Decimal('0.00')
    valor_total_juros = sum(c.total_juros_adicionais for c in credores_ativos)
    retorno_total_esperado = valor_total_emprestado + valor_total_juros
    lucro_potencial = valor_total_juros

    top_credores_data = sorted([(c.nome, c.saldo_devedor) for c in credores_ativos if c.saldo_devedor > 0], key=lambda item: item[1], reverse=True)[:5]
    top_credores_labels = [item[0] for item in top_credores_data]
    top_credores_valores = [float(item[1]) for item in top_credores_data]
    
    hoje = datetime.now()
    labels_meses, dados_pagamentos, dados_juros = [], [], []
    for i in range(6, 0, -1):
        data_mes = hoje - relativedelta(months=i-1)
        labels_meses.append(data_mes.strftime("%b/%y"))
        pagamentos_mes = Pagamento.objects.filter(data_pagamento__year=data_mes.year, data_pagamento__month=data_mes.month, valor__gt=0).aggregate(total=Sum('valor'))['total'] or 0
        juros_mes = Pagamento.objects.filter(data_pagamento__year=data_mes.year, data_pagamento__month=data_mes.month, valor__lt=0).aggregate(total=Sum('valor'))['total'] or 0
        dados_pagamentos.append(float(pagamentos_mes))
        dados_juros.append(float(abs(juros_mes)))

    context = {
        'total_credores_ativos': total_credores_ativos,
        'saldo_devedor_total': saldo_devedor_total,
        'valor_total_emprestado': valor_total_emprestado,
        'retorno_total_esperado': retorno_total_esperado,
        'lucro_potencial': lucro_potencial,
        'top_credores_labels_json': json.dumps(top_credores_labels),
        'top_credores_valores_json': json.dumps(top_credores_valores),
        'labels_meses_json': json.dumps(labels_meses),
        'dados_pagamentos_json': json.dumps(dados_pagamentos),
        'dados_juros_json': json.dumps(dados_juros),
        'composicao_divida_valores_json': json.dumps([float(valor_total_emprestado), float(valor_total_juros)]),
    }
    return render(request, 'dashboard.html', context)

@login_required
def pagina_upload(request):
    """
    Processa o upload, captura o mês/ano de referência, chama o serviço de conciliação,
    salva o resultado no banco de dados e redireciona para a página de detalhes.
    """
    if request.method == 'POST':
        arquivo_ofx = request.FILES.get('arquivo_ofx')
        arquivo_csv = request.FILES.get('arquivo_csv')
        mes_ano_referencia = request.POST.get('mes_ano_referencia')

        if not all([arquivo_ofx, arquivo_csv, mes_ano_referencia]):
            error_msg = "Todos os campos são obrigatórios: Mês/Ano de Referência, Arquivo OFX e Arquivo CSV."
            return render(request, 'conciliacao/upload.html', {'error': error_msg})
        
        try:
            mes_ano_formatado = datetime.strptime(mes_ano_referencia, '%Y-%m').strftime('%m/%Y')
        except ValueError:
            error_msg = "O formato da data de referência é inválido. Use o seletor."
            return render(request, 'conciliacao/upload.html', {'error': error_msg})

        try:
            df_banco = services.processar_banco_ofx(arquivo_ofx)
            df_egestor = services.carregar_egestor_csv(arquivo_csv)
            df_relatorio = services.gerar_dataframe_conciliacao(df_banco, df_egestor)

            novo_relatorio = RelatorioConciliacao.objects.create(
                mes_ano_referencia=mes_ano_formatado,
                executado_por=request.user
            )

            transacoes_para_criar = []
            for _, row in df_relatorio.iterrows():
                transacoes_para_criar.append(
                    Transacao(
                        relatorio=novo_relatorio,
                        data=datetime.strptime(row['Data'], '%d/%m/%Y').date(),
                        historico=row['Histórico Banco'] or row['Histórico Gestor'],
                        valor_banco=row['Valor Banco'],
                        valor_gestor=row['Valor Gestor'],
                        diferenca=row['Diferença'],
                        status=row['Status da Conciliação']
                    )
                )
            
            Transacao.objects.bulk_create(transacoes_para_criar)
            
            return redirect('conciliacao:detalhe_relatorio', pk=novo_relatorio.pk)

        except Exception as e:
            return render(request, 'conciliacao/upload.html', {'error': f'Ocorreu um erro ao processar os arquivos: {e}'})
            
    return render(request, 'conciliacao/upload.html')

@login_required
def lista_relatorios(request):
    """
    Exibe o histórico de conciliações, agora com um filtro por Mês/Ano e paginação.
    """
    mes_ano_filtro = request.GET.get('mes_ano')
    queryset = RelatorioConciliacao.objects.all() # O modelo já ordena por -data_execucao

    if mes_ano_filtro:
        queryset = queryset.filter(mes_ano_referencia=mes_ano_filtro)

    # --- LÓGICA DE PAGINAÇÃO ---
    paginator = Paginator(queryset, 10)  # Mostra 10 relatórios por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # --- FIM DA LÓGICA DE PAGINAÇÃO ---

    meses_disponiveis = RelatorioConciliacao.objects.order_by('-mes_ano_referencia').values_list('mes_ano_referencia', flat=True).distinct()
    
    context = {
        'relatorios': page_obj, # Passa o objeto da página, não o queryset inteiro
        'meses_disponiveis': meses_disponiveis,
        'mes_ano_selecionado': mes_ano_filtro,
    }
    return render(request, 'conciliacao/lista_relatorios.html', context)


@login_required
def detalhe_relatorio(request, pk):
    """Mostra o resultado de uma conciliação específica online."""
    relatorio = get_object_or_404(RelatorioConciliacao, pk=pk)
    transacoes = relatorio.transacoes.all()
    
    contexto = {
        'relatorio': relatorio,
        'transacoes': transacoes,
        'total_divergencias': transacoes.filter(status='DIVERGÊNCIA DE VALOR').count(),
        'total_pendente_banco': transacoes.filter(status='PENDENTE (APENAS NO BANCO)').count(),
        'total_pendente_gestor': transacoes.filter(status='PENDENTE (APENAS NO GESTOR)').count(),
    }
    return render(request, 'conciliacao/detalhe_relatorio.html', contexto)

@login_required
def download_relatorio_excel(request, pk):
    """
    Busca um relatório salvo, reconstrói o DataFrame e serve como um
    arquivo Excel para download.
    """
    relatorio = get_object_or_404(RelatorioConciliacao, pk=pk)
    
    transacoes_qs = relatorio.transacoes.all().values(
        'data', 'historico', 'valor_banco', 'valor_gestor', 'diferenca', 'status'
    )
    
    df_relatorio = pd.DataFrame(list(transacoes_qs))
    
    df_relatorio.rename(columns={
        'data': 'Data',
        'historico': 'Histórico',
        'valor_banco': 'Valor Banco',
        'valor_gestor': 'Valor Gestor',
        'diferenca': 'Diferença',
        'status': 'Status da Conciliação'
    }, inplace=True)
    
    df_relatorio['Data'] = pd.to_datetime(df_relatorio['Data']).dt.strftime('%d/%m/%Y')

    buffer_excel = services.criar_arquivo_excel(df_relatorio)
    buffer_excel.seek(0)
    
    response = HttpResponse(
        buffer_excel,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    nome_arquivo = f'relatorio_conciliacao_{relatorio.mes_ano_referencia.replace("/", "-")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename={nome_arquivo}'
    
    return response

class PaginaLoginView(auth_views.LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

class PaginaLogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('login')
