from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import user_passes_test
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.db.models import Sum
from decimal import Decimal

from django.db.models import Q

from .models import Credor, Pagamento
from .forms import CredorForm, PagamentoForm


def is_staff_member(user):
    return user.is_staff


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class CredorListView(StaffRequiredMixin, ListView):
    model = Credor
    template_name = 'credores/credor_list.html'

    def get_queryset(self):
        queryset = super().get_queryset()

        nome_filtro = self.request.GET.get('nome', '').strip()

        credores_ativos = queryset.filter(ativo=True).order_by('nome')

        if nome_filtro:
            credores_ativos = credores_ativos.filter(
                nome__icontains=nome_filtro
            )

        self._credores_ativos_filtrados = credores_ativos
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        credores_ativos = self._credores_ativos_filtrados

        valor_total_emprestado = credores_ativos.aggregate(
            total=Sum('valor_inicial')
        )['total'] or Decimal('0.00')

        total_juros_ativos = sum(
            c.total_juros_gerados for c in credores_ativos
        )

        saldo_devedor_total = sum(c.saldo_devedor for c in credores_ativos)

        context['valor_total_emprestado'] = valor_total_emprestado
        context['lucro_potencial'] = total_juros_ativos
        context['saldo_devedor_total'] = saldo_devedor_total
        context['total_credores_ativos'] = credores_ativos.count()
        context['credores_ativos'] = credores_ativos

        context['credores_quitados'] = Credor.objects.filter(
            ativo=False
        ).order_by('-data_criacao')

        context['request'] = self.request

        return context


class CredorDetailView(StaffRequiredMixin, DetailView):
    model = Credor
    template_name = 'credores/credor_detail.html'
    context_object_name = 'credor'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pagamento_form'] = PagamentoForm()
        context['pagamentos'] = self.object.pagamentos.all().order_by(
            '-data_pagamento'
        )
        return context


class CredorCreateView(StaffRequiredMixin, CreateView):
    model = Credor
    form_class = CredorForm
    template_name = 'credores/credor_form.html'
    success_url = reverse_lazy('credores:lista')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view'] = {
            'title': 'Adicionar Novo Credor',
            'description': 'Preencha os dados para adicionar um novo credor.',
        }
        return context

    def form_valid(self, form):
        response = super().form_valid(form)

        credor = self.object

        if credor.taxa_juros_mensal > 0:
            valor_juros = (
                credor.valor_inicial * (credor.taxa_juros_mensal / 100)
            ).quantize(Decimal('0.01'))

            if valor_juros > 0:
                Pagamento.objects.create(
                    credor=credor,
                    valor=-valor_juros,
                    data_pagamento=credor.data_criacao.date(),
                    observacao=f'Juros iniciais de {credor.taxa_juros_mensal}% aplicados na criação da dívida.',
                )
                messages.success(
                    self.request,
                    f'Credor "{credor.nome}" criado e juros iniciais de R$ {valor_juros:.2f} aplicados automaticamente.',
                )
        else:
            messages.success(
                self.request,
                f'Credor "{credor.nome}" criado com sucesso (sem juros iniciais).',
            )

        return response


class CredorUpdateView(StaffRequiredMixin, UpdateView):
    model = Credor
    form_class = CredorForm
    template_name = 'credores/credor_form.html'
    success_url = reverse_lazy('credores:lista')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['view'] = {
            'title': f'Editar Credor: {self.object.nome}',
            'description': 'Atualize os dados deste credor.',
        }
        return context


class CredorDeleteView(StaffRequiredMixin, DeleteView):
    model = Credor
    template_name = 'credores/credor_confirm_delete.html'
    success_url = reverse_lazy('credores:lista')


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

            credor.refresh_from_db()

            if credor.saldo_devedor <= 0:
                credor.ativo = False
                credor.save()
                messages.info(
                    request,
                    f'Dívida quitada! O credor "{credor.nome}" foi movido para o histórico de quitados.',
                )

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(
                        request,
                        f"Erro no campo '{form.fields[field].label}': {error}",
                    )
            if form.non_field_errors:
                for error in form.non_field_errors:
                    messages.error(request, f'Erro: {error}')

    return redirect('credores:detalhe', pk=credor.pk)


@user_passes_test(is_staff_member)
def aplicar_juros(request, pk):
    credor = get_object_or_404(Credor, pk=pk)
    if request.method == 'POST':
        juros_aplicados = credor.aplicar_juros_mensal()
        if juros_aplicados:
            messages.success(
                request,
                f'Juros de R$ {abs(juros_aplicados.valor):.2f} aplicados com sucesso.',
            )
        else:
            messages.warning(
                request,
                'Nenhum juro foi aplicado (dívida quitada ou sem taxa definida).',
            )
    return redirect('credores:detalhe', pk=credor.pk)


@user_passes_test(is_staff_member)
def toggle_credor_status(request, pk):
    credor = get_object_or_404(Credor, pk=pk)
    credor.ativo = not credor.ativo
    credor.save()
    status = 'reativado' if credor.ativo else 'marcado como quitado'
    messages.info(
        request,
        f'O status do credor "{credor.nome}" foi alterado para {status}.',
    )
    return redirect('credores:lista')
