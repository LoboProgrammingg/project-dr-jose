# credores/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Credor, Pagamento
from .forms import CredorForm, PagamentoForm
from decimal import Decimal
from django.utils import timezone

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
    context_object_name = 'credores'
    ordering = ['nome']

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
        context['titulo_pagina'] = 'Adicionar Novo Credor'
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
                    valor=-valor_juros,
                    data_pagamento=credor.data_criacao.date(), # Usa a data de criação da dívida
                    observacao=f"Juros iniciais de {credor.taxa_juros_mensal}% aplicados na criação da dívida."
                )
                messages.success(self.request, f'Credor "{credor.nome}" criado e juros iniciais de R$ {valor_juros} aplicados automaticamente.')
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
        context['titulo_pagina'] = f'Editar Credor: {self.object.nome}'
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
        else:
            for error in form.errors.values():
                messages.error(request, error)
    return redirect('credores:detalhe', pk=credor.pk)

@user_passes_test(is_staff_member)
def aplicar_juros(request, pk):
    credor = get_object_or_404(Credor, pk=pk)
    if request.method == 'POST':
        juros_aplicados = credor.aplicar_juros_mensal()
        if juros_aplicados:
            messages.success(request, f"Juros de R$ {abs(juros_aplicados.valor)} aplicados com sucesso.")
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
