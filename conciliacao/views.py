# conciliacao/views.py

import json
from datetime import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
import pandas as pd
import io

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.db.models import Sum
from django.core.paginator import Paginator

# Importa o services.py que contém toda a lógica de negócio
from . import services
from .models import RelatorioConciliacao, Transacao
from credores.models import Credor, Pagamento


# ==============================================================================
# --- VIEWS DE PÁGINA E LÓGICA DE NEGÓCIO ---
# ==============================================================================

@login_required
def dashboard(request):
    """(SEM ALTERAÇÕES) Exibe o painel principal com as métricas de negócio."""
    credores_ativos = Credor.objects.filter(ativo=True)
    total_credores_ativos = credores_ativos.count()
    saldo_devedor_total = sum(c.saldo_devedor for c in credores_ativos)
    valor_total_emprestado = credores_ativos.aggregate(total=Sum('valor_inicial'))['total'] or Decimal('0.00')
    valor_total_juros = sum(c.total_juros_adicionais for c in credores_ativos)
    
    top_credores_data = sorted([(c.nome, c.saldo_devedor) for c in credores_ativos if c.saldo_devedor > 0], key=lambda item: item[1], reverse=True)[:5]
    
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
        'retorno_total_esperado': valor_total_emprestado + valor_total_juros,
        'lucro_potencial': valor_total_juros,
        'top_credores_labels_json': json.dumps([item[0] for item in top_credores_data]),
        'top_credores_valores_json': json.dumps([float(item[1]) for item in top_credores_data]),
        'labels_meses_json': json.dumps(labels_meses),
        'dados_pagamentos_json': json.dumps(dados_pagamentos),
        'dados_juros_json': json.dumps(dados_juros),
        'composicao_divida_valores_json': json.dumps([float(valor_total_emprestado), float(valor_total_juros)])
    }
    return render(request, 'dashboard.html', context)

@login_required
def pagina_upload(request):
    """
    (ATUALIZADO)
    Processa o upload MENSAL, usando o services.py para conciliar
    e salvar o resultado no banco de dados, utilizando os nomes de coluna corretos.
    """
    if request.method == 'POST':
        arquivo_ofx = request.FILES.get('arquivo_ofx')
        arquivo_csv = request.FILES.get('arquivo_csv')
        mes_ano_referencia = request.POST.get('mes_ano_referencia')

        if not all([arquivo_ofx, arquivo_csv, mes_ano_referencia]):
            return render(request, 'conciliacao/upload.html', {'error': "Todos os campos são obrigatórios."})
        
        try:
            data_referencia = datetime.strptime(mes_ano_referencia, '%Y-%m')
            mes_ano_formatado = data_referencia.strftime('%m/%Y')
        except ValueError:
            return render(request, 'conciliacao/upload.html', {'error': "O formato da data é inválido. Use AAAA-MM."})

        try:
            # 1. Usa as funções do nosso services.py robusto
            df_banco = services.processar_banco_ofx(arquivo_ofx)
            df_egestor = services.carregar_egestor_csv(arquivo_csv)
            df_relatorio = services.gerar_dataframe_conciliacao(df_banco, df_egestor)

            if df_relatorio.empty:
                return render(request, 'conciliacao/upload.html', {'error': "Não foi possível gerar o relatório. Verifique se os arquivos contêm dados para o período."})

            # 2. Salva o resultado no banco de dados
            novo_relatorio = RelatorioConciliacao.objects.create(mes_ano_referencia=mes_ano_formatado, executado_por=request.user)
            
            # ATENÇÃO: Os nomes das colunas (ex: 'Data', 'Histórico Banco') devem ser EXATAMENTE os mesmos
            # retornados pelo DataFrame da função 'gerar_dataframe_conciliacao' em services.py.
            transacoes_para_criar = [
                Transacao(
                    relatorio=novo_relatorio,
                    data=row['Data'], # O DataFrame já retorna um objeto datetime
                    historico=row['Histórico Banco'] or row['Histórico Gestor'],
                    valor_banco=row['Valor Banco'],
                    valor_gestor=row['Valor Gestor'],
                    diferenca=row['Diferença'],
                    status=row['Status da Conciliação']
                ) for _, row in df_relatorio.iterrows()
            ]
            Transacao.objects.bulk_create(transacoes_para_criar)
            return redirect('conciliacao:detalhe_relatorio', pk=novo_relatorio.pk)
        except Exception as e:
            return render(request, 'conciliacao/upload.html', {'error': f'Ocorreu um erro inesperado: {e}'})
            
    return render(request, 'conciliacao/upload.html')

@login_required
def upload_relatorio_anual(request):
    """
    (SEM ALTERAÇÕES SIGNIFICATIVAS)
    Processa o upload ANUAL e gera um relatório Excel para download direto.
    Esta view já estava correta, pois passa o DataFrame diretamente para a função de criação do Excel.
    """
    if request.method == 'POST':
        arquivo_ofx = request.FILES.get('arquivo_ofx')
        arquivo_csv = request.FILES.get('arquivo_csv')

        if not arquivo_ofx or not arquivo_csv:
            return render(request, 'conciliacao/upload_anual.html', {'error': "Ambos os arquivos (OFX e CSV) são obrigatórios."})

        try:
            df_banco = services.processar_banco_ofx(arquivo_ofx)
            df_egestor = services.carregar_egestor_csv(arquivo_csv)
            df_relatorio = services.gerar_dataframe_conciliacao(df_banco, df_egestor)
            
            if df_relatorio.empty:
                return render(request, 'conciliacao/upload_anual.html', {'error': "Não foi possível gerar o relatório. Verifique se os arquivos contêm dados válidos."})

            # Usa a função de criação de Excel do nosso services.py
            buffer_excel = services.criar_arquivo_excel(df_relatorio)
            
            response = HttpResponse(buffer_excel, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            nome_arquivo = f'Relatorio_Conciliacao_Anual_{datetime.now().strftime("%Y%m%d")}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
            return response
        except Exception as e:
            return render(request, 'conciliacao/upload_anual.html', {'error': f'Ocorreu um erro inesperado: {e}'})

    return render(request, 'conciliacao/upload_anual.html')

@login_required
def lista_relatorios(request):
    """(SEM ALTERAÇÕES) Exibe o histórico de conciliações mensais salvas."""
    mes_ano_filtro = request.GET.get('mes_ano')
    queryset = RelatorioConciliacao.objects.all().order_by('-data_execucao')
    if mes_ano_filtro:
        queryset = queryset.filter(mes_ano_referencia=mes_ano_filtro)
    paginator = Paginator(queryset, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    meses_disponiveis = RelatorioConciliacao.objects.order_by('-mes_ano_referencia').values_list('mes_ano_referencia', flat=True).distinct()
    context = {'relatorios': page_obj, 'meses_disponiveis': meses_disponiveis, 'mes_ano_selecionado': mes_ano_filtro}
    return render(request, 'conciliacao/lista_relatorios.html', context)

@login_required
def detalhe_relatorio(request, pk):
    """
    (ATUALIZADO)
    Mostra o resultado de uma conciliação mensal específica.
    Os filtros de status foram corrigidos para usar os nomes exatos gerados pelo services.py.
    """
    relatorio = get_object_or_404(RelatorioConciliacao, pk=pk)
    transacoes_qs = relatorio.transacoes.all().order_by('data', 'id')

    # --- CORREÇÃO PRINCIPAL ---
    # Os status aqui devem ser EXATAMENTE os mesmos gerados em 'gerar_dataframe_conciliacao'
    total_divergencias = transacoes_qs.filter(status='DIVERGÊNCIA DE VALOR').count()
    total_pendente_banco = transacoes_qs.filter(status='PENDENTE (APENAS NO BANCO)').count()
    total_pendente_gestor = transacoes_qs.filter(status='PENDENTE (APENAS NO GESTOR)').count()
    # -------------------------------------------------------------------------

    contexto = {
        'relatorio': relatorio,
        'transacoes': transacoes_qs,
        'total_divergencias': total_divergencias,
        'total_pendente_banco': total_pendente_banco,
        'total_pendente_gestor': total_pendente_gestor,
    }
    return render(request, 'conciliacao/detalhe_relatorio.html', contexto)

@login_required
def download_relatorio_excel(request, pk):
    """
    (ATUALIZADO)
    Gera o download de um relatório MENSAL já salvo no banco, convertendo
    os dados do modelo para o formato de DataFrame que a função de criação de Excel espera.
    """
    relatorio = get_object_or_404(RelatorioConciliacao, pk=pk)
    transacoes_qs = relatorio.transacoes.all().order_by('data').values(
        'data', 'historico', 'valor_banco', 'valor_gestor', 'diferenca', 'status'
    )
    
    if not transacoes_qs:
        # Lidar com o caso de não haver transações, talvez redirecionar com uma mensagem
        return redirect('conciliacao:detalhe_relatorio', pk=pk)

    df_from_db = pd.DataFrame(list(transacoes_qs))
    
    # Prepara o DataFrame para a função criar_arquivo_excel
    # Renomeia as colunas do banco de dados para os nomes de coluna esperados pelo service
    df_relatorio = pd.DataFrame()
    df_relatorio['Data'] = df_from_db['data']
    # Assume que o histórico salvo é o do banco e cria uma coluna vazia para o gestor
    df_relatorio['Histórico Banco'] = df_from_db['historico']
    df_relatorio['Valor Banco'] = df_from_db['valor_banco']
    df_relatorio['Histórico Gestor'] = '' # Coluna necessária para a função de excel
    df_relatorio['Valor Gestor'] = df_from_db['valor_gestor']
    df_relatorio['Diferença'] = df_from_db['diferenca']
    df_relatorio['Status da Conciliação'] = df_from_db['status']

    buffer_excel = services.criar_arquivo_excel(df_relatorio)
    
    response = HttpResponse(buffer_excel, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    nome_arquivo = f'relatorio_conciliacao_{relatorio.mes_ano_referencia.replace("/", "-")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
    return response

# --- VIEWS DE AUTENTICAÇÃO E PÁGINAS ESTÁTICAS (Sem alterações) ---

class PaginaLoginView(auth_views.LoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True

class PaginaLogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('login')

@login_required
def instrucoes_ofx(request):
    """Exibe a página com instruções detalhadas."""
    return render(request, 'conciliacao/instrucoes_ofx.html')
