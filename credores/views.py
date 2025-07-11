# credores/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Sum
from decimal import Decimal

# Importe aqui a classe Q para consultas complexas
from django.db.models import Q 

from .models import Credor, Pagamento
from .forms import CredorForm, PagamentoForm

# --- Função de teste de permissão, para maior clareza ---
def is_staff_member(user):
    return user.is_staff

# --- Mixin de Segurança para nossas Views baseadas em Classe ---
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Garante que apenas usuários com status de 'staff' acessem a view."""
    def test_func(self):
        return self.request.user.is_staff

# --- CRUD Views ---

class CredorListView(StaffRequiredMixin, ListView):
    model = Credor
    template_name = 'credores/credor_list.html'
    
    def get_queryset(self):
        """
        Retorna a queryset de credores, aplicando o filtro por nome se presente.
        """
        queryset = super().get_queryset()
        
        # Captura o termo de pesquisa do parâmetro 'nome' na URL
        nome_filtro = self.request.GET.get('nome', '').strip() # .strip() para remover espaços em branco
        
        # Filtra credores ativos
        credores_ativos = queryset.filter(ativo=True).order_by('nome')

        # Aplica o filtro por nome se houver um termo de pesquisa
        if nome_filtro:
            # Use Q object para um OR lógico, se quiser pesquisar em mais de um campo
            # Ex: nome__icontains OR email__icontains
            credores_ativos = credores_ativos.filter(nome__icontains=nome_filtro)
            # Se você quiser filtrar credores quitados também pelo nome:
            # credores_quitados = queryset.filter(ativo=False, nome__icontains=nome_filtro).order_by('-data_criacao')
        
        # Armazena a queryset filtrada para ser usada no get_context_data
        self._credores_ativos_filtrados = credores_ativos
        return queryset # Retorna a queryset completa ou uma parte dela, dependendo da necessidade base.
                        # Para este caso, o importante é que credores_ativos_filtrados esteja disponível.

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Usa a queryset filtrada que foi armazenada em get_queryset
        credores_ativos = self._credores_ativos_filtrados
        
        valor_total_emprestado = credores_ativos.aggregate(total=Sum('valor_inicial'))['total'] or Decimal('0.00')
        
        # total_juros_gerados deve ser um campo ou propriedade calculada no seu modelo Credor.
        # Se for um campo calculado (annotation), use .aggregate(Sum('total_juros_gerados'))
        # Se for uma propriedade Python, some como feito aqui.
        total_juros_ativos = sum(c.total_juros_gerados for c in credores_ativos)
        
        saldo_devedor_total = sum(c.saldo_devedor for c in credores_ativos)

        context['valor_total_emprestado'] = valor_total_emprestado
        context['lucro_potencial'] = total_juros_ativos
        context['saldo_devedor_total'] = saldo_devedor_total
        context['total_credores_ativos'] = credores_ativos.count()
        context['credores_ativos'] = credores_ativos
        
        # Credores quitados não são afetados pelo filtro de nome nesta implementação
        # (a menos que você os filtre também, como comentado acima em get_queryset)
        context['credores_quitados'] = Credor.objects.filter(ativo=False).order_by('-data_criacao')
        
        # Adiciona o objeto request ao contexto para que o template possa acessar request.GET.nome
        context['request'] = self.request 

        return context

class CredorDetailView(StaffRequiredMixin, DetailView):
    model = Credor
    template_name = 'credores/credor_detail.html'
    context_object_name = 'credor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pagamento_form'] = PagamentoForm()
        context['pagamentos'] = self.object.pagamentos.all().order_by('-data_pagamento')
        return context

class CredorCreateView(StaffRequiredMixin, CreateView):
    model = Credor
    form_class = CredorForm
    template_name = 'credores/credor_form.html'
    success_url = reverse_lazy('credores:lista')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Passa um dicionário para 'view' para ser consistente com o nome usado no template
        context['view'] = {'title': 'Adicionar Novo Credor', 'description': 'Preencha os dados para adicionar um novo credor.'}
        return context

    # --- LÓGICA DE JUROS AUTOMÁTICA ADICIONADA AQUI ---
    def form_valid(self, form):
        """
        Esta função é chamada após o formulário ser validado.
        Nós a interceptamos para aplicar os juros iniciais automaticamente.
        """
        # O comportamento padrão salva o objeto e nos dá acesso a ele
        response = super().form_valid(form)
        
        # self.object é o credor que acabou de ser criado
        credor = self.object
        
        # Verifica se uma taxa de juros foi definida no formulário
        if credor.taxa_juros_mensal > 0:
            # Calcula o valor dos juros sobre o valor inicial
            valor_juros = (credor.valor_inicial * (credor.taxa_juros_mensal / 100)).quantize(Decimal('0.01'))
            
            if valor_juros > 0:
                # Cria um registro de "pagamento negativo" para os juros, vinculando-o ao credor
                Pagamento.objects.create(
                    credor=credor,
                    valor=-valor_juros, # Valor negativo para indicar juros
                    data_pagamento=credor.data_criacao.date(), # Usa a data de criação da dívida
                    observacao=f"Juros iniciais de {credor.taxa_juros_mensal}% aplicados na criação da dívida."
                )
                messages.success(self.request, f'Credor "{credor.nome}" criado e juros iniciais de R$ {valor_juros:.2f} aplicados automaticamente.')
        else:
            messages.success(self.request, f'Credor "{credor.nome}" criado com sucesso (sem juros iniciais).')

        return response


class CredorUpdateView(StaffRequiredMixin, UpdateView):
    model = Credor
    form_class = CredorForm
    template_name = 'credores/credor_form.html'
    success_url = reverse_lazy('credores:lista')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Passa um dicionário para 'view' para ser consistente com o nome usado no template
        context['view'] = {'title': f'Editar Credor: {self.object.nome}', 'description': 'Atualize os dados deste credor.'}
        return context

class CredorDeleteView(StaffRequiredMixin, DeleteView):
    model = Credor
    template_name = 'credores/credor_confirm_delete.html'
    success_url = reverse_lazy('credores:lista')

# --- Views de Ação (Baseadas em Funções) ---

@user_passes_test(is_staff_member)
def adicionar_pagamento(request, pk):
    credor = get_object_or_404(Credor, pk=pk)
    if request.method == 'POST':
        form = PagamentoForm(request.POST, request.FILES)
        if form.is_valid():
            pagamento = form.save(commit=False)
            pagamento.credor = credor
            pagamento.save()
            messages.success(request, 'Lançamento adicionado com sucesso!')

            # Força o recálculo dos valores do credor após o pagamento
            credor.refresh_from_db() 

            if credor.saldo_devedor <= 0:
                credor.ativo = False
                credor.save()
                messages.info(request, f'Dívida quitada! O credor "{credor.nome}" foi movido para o histórico de quitados.')

        else:
            # Melhorar a exibição de erros do formulário
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erro no campo '{form.fields[field].label}': {error}")
            # Se houver non_field_errors (erros globais do formulário)
            if form.non_field_errors:
                 for error in form.non_field_errors:
                    messages.error(request, f"Erro: {error}")

    # Sempre redireciona para a página de detalhes, mesmo em caso de erro, para exibir as mensagens
    return redirect('credores:detalhe', pk=credor.pk)


@user_passes_test(is_staff_member)
def aplicar_juros(request, pk):
    credor = get_object_or_404(Credor, pk=pk)
    if request.method == 'POST':
        juros_aplicados = credor.aplicar_juros_mensal() # Supondo que este método retorna o objeto Pagamento ou None
        if juros_aplicados:
            messages.success(request, f"Juros de R$ {abs(juros_aplicados.valor):.2f} aplicados com sucesso.")
        else:
            messages.warning(request, "Nenhum juro foi aplicado (dívida quitada ou sem taxa definida).")
    return redirect('credores:detalhe', pk=credor.pk)

@user_passes_test(is_staff_member)
def toggle_credor_status(request, pk):
    """Inverte o status 'ativo' de um credor (Quitado/Ativo)."""
    credor = get_object_or_404(Credor, pk=pk)
    credor.ativo = not credor.ativo
    credor.save()
    status = "reativado" if credor.ativo else "marcado como quitado"
    messages.info(request, f'O status do credor "{credor.nome}" foi alterado para {status}.')
    return redirect('credores:lista')