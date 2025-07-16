import pandas as pd
from ofxparse import OfxParser
import re
import os
import numpy as np

# ... (sua função limpar_valor_csv permanece a mesma) ...

def processar_banco_ofx(caminho_ofx: str) -> pd.DataFrame:
    """
    Processa um arquivo OFX com tratamento explícito de codificação para evitar erros.
    Tenta decodificar o arquivo como UTF-8 e, em caso de falha, como latin-1.
    """
    if not os.path.exists(caminho_ofx):
        raise FileNotFoundError(f"Arquivo OFX não encontrado em: {caminho_ofx}")
    print(f"Iniciando processamento do extrato OFX: '{caminho_ofx}'...")

    try:
        # Tenta ler o arquivo com a codificação mais comum (UTF-8)
        with open(caminho_ofx, 'r', encoding='utf-8') as f:
            ofx = OfxParser.parse(f)
        print("Arquivo lido com sucesso usando codificação UTF-8.")
    except UnicodeDecodeError:
        # Se falhar, tenta com latin-1, comum em sistemas legados no Brasil
        print("Falha ao ler como UTF-8. Tentando como 'latin-1'...")
        try:
            with open(caminho_ofx, 'r', encoding='latin-1') as f:
                ofx = OfxParser.parse(f)
            print("Arquivo lido com sucesso usando codificação latin-1.")
        except Exception as e:
            raise IOError(f"Não foi possível ler o arquivo OFX com as codificações testadas (UTF-8, latin-1). Erro: {e}")
    except Exception as e:
        raise e

    transacoes = []
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
    df_banco = df_banco.sort_values(by="Data").reset_index(drop=True)
    print(f"Processamento do OFX concluído. Encontradas {len(df_banco)} transações.")
    return df_banco

# ... (o resto do seu código, carregar_egestor_csv, gerar_relatorio_definitivo, etc., continua IGUAL) ...

# --- MÓDULO 3: GERAÇÃO DE RELATÓRIO (LÓGICA CORRIGIDA E ROBUSTA) ---
def gerar_relatorio_definitivo(df_banco: pd.DataFrame, df_egestor: pd.DataFrame, arquivo_saida: str):
    print("Iniciando motor de conciliação de precisão (Padrão VBA)...")

    # Adiciona colunas de "match" para encontrar correspondências exatas
    df_banco['Valor_Match'] = df_banco['Valor_Banco'].round(2)
    df_egestor['Valor_Match'] = df_egestor['Valor_eGestor'].round(2)

    # 1. Realiza um merge completo para cruzar todos os dados
    df_merged = pd.merge(
        df_banco.reset_index(), 
        df_egestor.reset_index(), 
        on=['Data', 'Valor_Match'], 
        how='outer', 
        suffixes=('_Banco', '_Gestor'), 
        indicator=True
    )

    # 2. Separa os conciliados dos itens que precisam de análise
    conciliados = df_merged[df_merged['_merge'] == 'both']
    a_analisar = df_merged[df_merged['_merge'] != 'both']

    # 3. Prepara as listas de pendências
    pendentes_banco = a_analisar[a_analisar['_merge'] == 'left_only']
    pendentes_gestor = a_analisar[a_analisar['_merge'] == 'right_only']

    # 4. Alinha as pendências por data para encontrar divergências de valor
    divergencias = pd.merge(
        pendentes_banco,
        pendentes_gestor,
        on='Data',
        how='outer',
        suffixes=('_Banco', '_Gestor')
    )
    
    # 5. Monta o Painel de Análise final
    relatorio_final = []

    # Adiciona os itens perfeitamente conciliados
    for _, row in conciliados.iterrows():
        relatorio_final.append({
            'Data': row['Data'],
            'Histórico Banco': row['Historico_Banco'], 'Valor Banco': row['Valor_Banco'],
            'Histórico Gestor': row['Historico_eGestor'], 'Valor Gestor': row['Valor_eGestor'],
            'Diferença': 0.00, 'Status da Conciliação': 'Conciliado'
        })
        
    # Adiciona os itens com divergência ou pendência
    for _, row in divergencias.iterrows():
        status = ''
        banco_presente = pd.notna(row['Valor_Banco_Banco'])
        gestor_presente = pd.notna(row['Valor_eGestor_Gestor'])

        if banco_presente and gestor_presente:
            status = 'DIVERGÊNCIA DE VALOR'
        elif banco_presente:
            status = 'PENDENTE (APENAS NO BANCO)'
        elif gestor_presente:
            status = 'PENDENTE (APENAS NO GESTOR)'
            
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

    if not relatorio_final:
        print("Nenhuma transação para processar no relatório final.")
        return

    # 6. Gera o DataFrame final e o formata para o Excel
    df_relatorio = pd.DataFrame(relatorio_final).sort_values(by='Data').reset_index(drop=True)
    df_relatorio['Data'] = df_relatorio['Data'].dt.strftime('%d/%m/%Y')

    print(f"Gerando relatório final em '{arquivo_saida}'...")
    with pd.ExcelWriter(arquivo_saida) as writer:
        df_relatorio.to_excel(writer, sheet_name='Painel de Conciliação', index=False)
        
    print(f"\nRelatório de precisão '{arquivo_saida}' gerado com sucesso!")

# --- BLOCO PRINCIPAL DE EXECUÇÃO ---
if __name__ == "__main__":
    ofx_banco_path = "JANEIRO-2024-converted.ofx"
    # Adicionei a função que faltava no seu código original
    def limpar_valor_csv(valor_str: str) -> float | None:
        if not isinstance(valor_str, str): return None
        sinal = -1 if '(-)' in valor_str or valor_str.strip().startswith('-') else 1
        valor_limpo = re.sub(r'[^\d,]', '', str(valor_str).replace('.', ''))
        valor_limpo = valor_limpo.replace(',', '.')
        try: return float(valor_limpo) * sinal
        except (ValueError, TypeError): return None
    
    def carregar_egestor_csv(caminho_arquivo: str) -> pd.DataFrame:
        if not os.path.exists(caminho_arquivo): raise FileNotFoundError(f"Arquivo CSV do eGestor não encontrado em: {caminho_arquivo}")
        print(f"Lendo o arquivo CSV '{caminho_arquivo}'...")
        df = pd.read_csv(caminho_arquivo, sep=',', encoding='utf-8', header=0, dtype={'Cód.': str})
        print("Arquivo CSV lido. Padronizando colunas...")
        if 'Descrição' not in df.columns:
            print("AVISO: Coluna 'Descrição' não encontrada no CSV. Será criada uma coluna de histórico vazia.")
            df['Descrição'] = ''
        df = df.rename(columns={
            'Data de pagamento': 'Data', 'Descrição': 'Historico_eGestor',
            'Valor': 'Valor_eGestor', 'Cód.': 'Codigo_eGestor'
        })
        colunas = ['Data', 'Historico_eGestor', 'Valor_eGestor', 'Codigo_eGestor']
        if not all(c in df.columns for c in colunas): raise ValueError(f"Colunas esperadas não encontradas. Disponíveis: {df.columns.tolist()}")
        df = df[colunas].copy()
        df.dropna(how='all', inplace=True)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce', format='%d/%m/%Y')
        df['Valor_eGestor'] = df['Valor_eGestor'].astype(str).apply(limpar_valor_csv)
        df['Valor_eGestor'] = pd.to_numeric(df['Valor_eGestor'], errors='coerce')
        df.dropna(subset=['Data', 'Valor_eGestor'], inplace=True)
        print("Dados do eGestor processados com sucesso.")
        return df

    csv_egestor_path = "extrato Financeiro JANEIRO 2024.xlsx - extrato Financeiro JANEIRO 2024.xls (2).csv"
    relatorio_path = 'relatorio_janeiro_2024.xlsx'

    try:
        df_banco_final = processar_banco_ofx(ofx_banco_path)
        df_egestor_final = carregar_egestor_csv(csv_egestor_path)
        gerar_relatorio_definitivo(df_banco_final, df_egestor_final, relatorio_path)
    except FileNotFoundError as e:
        print(f"\nERRO CRÍTICO: ARQUIVO NÃO ENCONTRADO. {e}")
    except Exception as e:
        print(f"\nERRO CRÍTICO: Ocorreu um erro inesperado. {e}")