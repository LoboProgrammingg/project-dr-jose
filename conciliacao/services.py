# conciliacao/services.py

import pandas as pd
from ofxparse import OfxParser
import re
import io

# --- FUNÇÕES DE LEITURA E LIMPEZA (Helpers) ---

def limpar_valor_csv(valor_str: str) -> float | None:
    """Converte o formato de valor do CSV para um float padrão, removendo 'R$'."""
    if not isinstance(valor_str, str):
        return None
    sinal = -1 if '(-)' in valor_str or valor_str.strip().startswith('-') else 1
    # Remove R$, pontos de milhar e outros caracteres não numéricos
    valor_limpo = re.sub(r'[^\d,]', '', str(valor_str).replace('.', '').replace('R$', ''))
    valor_limpo = valor_limpo.replace(',', '.')
    try:
        return float(valor_limpo) * sinal
    except (ValueError, TypeError):
        return None

def processar_banco_ofx(arquivo_ofx_em_memoria) -> pd.DataFrame:
    """Lê um arquivo OFX em memória e o transforma em um DataFrame do Pandas."""
    print("Iniciando processamento do extrato OFX em memória...")
    transacoes = []
    ofx = OfxParser.parse(arquivo_ofx_em_memoria)
    conta = ofx.accounts[0]
    extrato = conta.statement
    for transacao in extrato.transactions:
        transacoes.append({
            "Data": transacao.date.date(),
            "Historico_Banco": transacao.memo,
            "Valor_Banco": float(transacao.amount),
            "Codigo_Banco": transacao.id
        })
    if not transacoes:
        return pd.DataFrame(columns=["Data", "Historico_Banco", "Valor_Banco", "Codigo_Banco"])
    df_banco = pd.DataFrame(transacoes)
    df_banco['Data'] = pd.to_datetime(df_banco['Data'])
    return df_banco.sort_values(by="Data").reset_index(drop=True)

def carregar_egestor_csv(arquivo_csv_em_memoria) -> pd.DataFrame:
    """Lê um arquivo CSV em memória e o transforma em um DataFrame do Pandas."""
    print("Lendo o arquivo CSV em memória...")
    df = pd.read_csv(arquivo_csv_em_memoria, sep=',', encoding='utf-8', header=0, dtype={'Cód.': str})
    if 'Descrição' not in df.columns:
        print("AVISO: Coluna 'Descrição' não encontrada no CSV. Uma coluna de histórico vazia será usada.")
        df['Descrição'] = ''
    df = df.rename(columns={
        'Data de pagamento': 'Data', 'Descrição': 'Historico_eGestor',
        'Valor': 'Valor_eGestor', 'Cód.': 'Codigo_eGestor'
    })
    colunas = ['Data', 'Historico_eGestor', 'Valor_eGestor', 'Codigo_eGestor']
    df = df[colunas].copy()
    df.dropna(how='all', inplace=True)
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce', format='%d/%m/%Y')
    df['Valor_eGestor'] = df['Valor_eGestor'].astype(str).apply(limpar_valor_csv)
    df['Valor_eGestor'] = pd.to_numeric(df['Valor_eGestor'], errors='coerce')
    df.dropna(subset=['Data', 'Valor_eGestor'], inplace=True)
    print("Dados do eGestor processados com sucesso.")
    return df

# --- FUNÇÃO PRINCIPAL DE LÓGICA DE NEGÓCIO ---

def gerar_dataframe_conciliacao(df_banco: pd.DataFrame, df_egestor: pd.DataFrame) -> pd.DataFrame:
    """
    Executa a conciliação e retorna um DataFrame do Pandas com o resultado detalhado.
    Esta é a função que a view usará para salvar os dados no banco.
    """
    print("Executando motor de conciliação de precisão...")
    df_banco['Valor_Match'] = df_banco['Valor_Banco'].round(2)
    df_egestor['Valor_Match'] = df_egestor['Valor_eGestor'].round(2)
    
    df_merged = pd.merge(df_banco.reset_index(), df_egestor.reset_index(), on=['Data', 'Valor_Match'], how='outer', suffixes=('_Banco', '_Gestor'), indicator=True)
    
    conciliados = df_merged[df_merged['_merge'] == 'both']
    a_analisar = df_merged[df_merged['_merge'] != 'both']
    pendentes_banco = a_analisar[a_analisar['_merge'] == 'left_only']
    pendentes_gestor = a_analisar[a_analisar['_merge'] == 'right_only']
    divergencias = pd.merge(pendentes_banco, pendentes_gestor, on='Data', how='outer', suffixes=('_Banco', '_Gestor'))
    
    relatorio_final = []
    for _, row in conciliados.iterrows():
        relatorio_final.append({
            'Data': row['Data'],
            'Histórico Banco': row['Historico_Banco'], 'Valor Banco': row['Valor_Banco'],
            'Histórico Gestor': row['Historico_eGestor'], 'Valor Gestor': row['Valor_eGestor'],
            'Diferença': 0.00, 'Status da Conciliação': 'Conciliado'
        })
    for _, row in divergencias.iterrows():
        banco_presente = pd.notna(row['Valor_Banco_Banco'])
        gestor_presente = pd.notna(row['Valor_eGestor_Gestor'])
        status = 'DIVERGÊNCIA DE VALOR' if banco_presente and gestor_presente else ('PENDENTE (APENAS NO BANCO)' if banco_presente else 'PENDENTE (APENAS NO GESTOR)')
        valor_banco = row['Valor_Banco_Banco'] if banco_presente else 0
        valor_gestor = row['Valor_eGestor_Gestor'] if gestor_presente else 0
        relatorio_final.append({
            'Data': row['Data'],
            'Histórico Banco': row['Historico_Banco_Banco'] if banco_presente else '',
            'Valor Banco': valor_banco,
            'Histórico Gestor': row['Historico_eGestor_Gestor'] if gestor_presente else '',
            'Valor Gestor': valor_gestor,
            'Diferença': round(valor_banco - valor_gestor, 2),
            'Status da Conciliação': status
        })
        
    df_relatorio = pd.DataFrame(relatorio_final).sort_values(by='Data').reset_index(drop=True)
    df_relatorio['Data'] = df_relatorio['Data'].dt.strftime('%d/%m/%Y')
    return df_relatorio

# --- FUNÇÃO DE GERAÇÃO DE ARQUIVO ---

def criar_arquivo_excel(df_relatorio: pd.DataFrame) -> io.BytesIO:
    """
    Recebe um DataFrame de conciliação e o converte em um arquivo Excel em memória,
    pronto para ser baixado.
    """
    output_em_memoria = io.BytesIO()
    with pd.ExcelWriter(output_em_memoria, engine='xlsxwriter') as writer:
        df_relatorio.to_excel(writer, sheet_name='Painel de Conciliação', index=False)
    
    print("Arquivo Excel gerado em memória com sucesso!")
    return output_em_memoria
