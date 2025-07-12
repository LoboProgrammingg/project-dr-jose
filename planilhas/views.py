# planilhas/views.py
import json
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.core.serializers.json import DjangoJSONEncoder

from .models import AnoPlanilha, Planilha, PlanilhaNativa
from .forms import AnoPlanilhaForm, PlanilhaForm, PlanilhaNativaForm
from . import services

# --- Views para Anos ---

class ListaAnosView(LoginRequiredMixin, ListView):
    """
    Exibe a lista de todos os anos de referência cadastrados.
    """
    model = AnoPlanilha
    template_name = 'planilhas/lista_anos.html'
    context_object_name = 'anos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AnoPlanilhaForm()
        return context

@login_required
def criar_ano(request):
    """
    Processa o formulário para criar um novo ano de referência.
    """
    if request.method == 'POST':
        form = AnoPlanilhaForm(request.POST)
        if form.is_valid():
            ano = form.save(commit=False)
            ano.criado_por = request.user
            ano.save()
    return redirect('planilhas:lista_anos')

class DetalheAnoView(LoginRequiredMixin, ListView):
    """
    Exibe todas as planilhas (nativas e de upload) para um ano específico.
    Também lida com a funcionalidade de pesquisa.
    """
    template_name = 'planilhas/detalhe_ano.html'
    context_object_name = 'planilhas_upload' # Contexto para planilhas de upload
    paginate_by = 5

    def get_queryset(self):
        self.ano_obj = get_object_or_404(AnoPlanilha, ano=self.kwargs['ano'])
        search_query = self.request.GET.get('q', '')
        queryset = Planilha.objects.filter(ano_referencia=self.ano_obj)
        if search_query:
            queryset = queryset.filter(nome__icontains=search_query)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ano'] = self.ano_obj
        search_query = self.request.GET.get('q', '')
        
        planilhas_nativas = PlanilhaNativa.objects.filter(ano_referencia=self.ano_obj)
        if search_query:
            planilhas_nativas = planilhas_nativas.filter(nome__icontains=search_query)
        context['planilhas_nativas'] = planilhas_nativas
        
        context['search_query'] = search_query
        return context

# --- Views para Planilhas de Upload (CRUD) ---

@login_required
def upload_planilha(request, ano):
    """
    Lida com o upload de um novo arquivo de planilha (Excel/CSV).
    """
    ano_obj = get_object_or_404(AnoPlanilha, ano=ano)
    if request.method == 'POST':
        form = PlanilhaForm(request.POST, request.FILES)
        if form.is_valid():
            planilha = form.save(commit=False)
            planilha.adicionado_por = request.user
            
            try:
                dados_json = services.extrair_dados_planilha(planilha.arquivo)
                planilha.conteudo_json = dados_json
            except Exception as e:
                form.add_error('arquivo', f"Erro ao ler a planilha: {e}")
                return render(request, 'planilhas/planilha_form.html', {'form': form, 'ano': ano_obj})

            planilha.save()
            return redirect('planilhas:detalhe_ano', ano=ano)
    else:
        form = PlanilhaForm(initial={'ano_referencia': ano_obj})
        
    return render(request, 'planilhas/planilha_form.html', {'form': form, 'ano': ano_obj})

class DetalhePlanilhaView(LoginRequiredMixin, DetailView):
    """Exibe o conteúdo de uma planilha que foi enviada por upload."""
    model = Planilha
    template_name = 'planilhas/detalhe_planilha.html'
    context_object_name = 'planilha'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dados = self.object.conteudo_json
        if dados:
            context['headers'] = dados[0].keys() if dados else []
            context['rows'] = dados
        return context

class EditarPlanilhaView(LoginRequiredMixin, UpdateView):
    """Edita os metadados (como o nome) de uma planilha de upload."""
    model = Planilha
    form_class = PlanilhaForm
    template_name = 'planilhas/planilha_form.html'
    
    def get_success_url(self):
        return reverse_lazy('planilhas:detalhe_ano', kwargs={'ano': self.object.ano_referencia.ano})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ano'] = self.object.ano_referencia
        return context

class DeletarPlanilhaView(LoginRequiredMixin, DeleteView):
    """Deleta uma planilha de upload."""
    model = Planilha
    template_name = 'planilhas/planilha_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('planilhas:detalhe_ano', kwargs={'ano': self.object.ano_referencia.ano})

@login_required
def download_planilha(request, pk):
    """Força o download do arquivo original da planilha."""
    planilha = get_object_or_404(Planilha, pk=pk)
    arquivo = planilha.arquivo
    response = HttpResponse(arquivo.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{arquivo.name.split("/")[-1]}"'
    return response

# --- Views para Planilhas Nativas (Criadas no Sistema) ---

@login_required
def criar_planilha_nativa(request, ano):
    """
    Exibe e processa o formulário para criar uma nova planilha nativa.
    """
    ano_obj = get_object_or_404(AnoPlanilha, ano=ano)
    if request.method == 'POST':
        form = PlanilhaNativaForm(request.POST)
        if form.is_valid():
            planilha = form.save(commit=False)
            planilha.adicionado_por = request.user
            planilha.ano_referencia = ano_obj
            
            colunas_str = form.cleaned_data.get('colunas_str', '')
            planilha.colunas = [col.strip() for col in colunas_str.split(',') if col.strip()]
            
            planilha.save()
            return redirect('planilhas:editar_planilha_nativa', pk=planilha.pk)
    else:
        form = PlanilhaNativaForm()
        
    return render(request, 'planilhas/planilha_nativa_form.html', {'form': form, 'ano': ano_obj})

@login_required
def editar_planilha_nativa(request, pk):
    """
    View principal para a interface de edição de planilhas nativas.
    Lida com GET para renderizar o editor e POST (via Fetch/JSON) para salvar os dados.
    """
    planilha = get_object_or_404(PlanilhaNativa, pk=pk)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            planilha.nome = data.get('nome', planilha.nome)
            planilha.colunas = data.get('colunas', planilha.colunas)
            planilha.dados = data.get('dados', planilha.dados)
            planilha.save()
            return JsonResponse({'status': 'success', 'message': 'Planilha salva com sucesso!'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Dados inválidos.'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    context = {
        'planilha': planilha,
        'planilha_json': json.dumps({
            'nome': planilha.nome,
            'colunas': planilha.colunas,
            'dados': planilha.dados
        }, cls=DjangoJSONEncoder)
    }
    return render(request, 'planilhas/editor_planilha_nativa.html', context)

class DeletarPlanilhaNativaView(LoginRequiredMixin, DeleteView):
    """Deleta uma planilha nativa."""
    model = PlanilhaNativa
    template_name = 'planilhas/planilha_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('planilhas:detalhe_ano', kwargs={'ano': self.object.ano_referencia.ano})

@login_required
def download_planilha_nativa(request, pk):
    """Gera e força o download de uma planilha nativa como um arquivo CSV."""
    planilha = get_object_or_404(PlanilhaNativa, pk=pk)
    csv_data = services.gerar_csv_nativo(planilha)
    if csv_data:
        response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{planilha.nome}.csv"'
        return response
    return redirect(planilha.get_absolute_url())
