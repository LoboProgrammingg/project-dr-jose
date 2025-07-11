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
    try:
        transacoes = []
        ofx = OfxParser.parse(arquivo_ofx_em_memoria)
        # Itera sobre todas as contas no arquivo OFX
        for conta in ofx.accounts:
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
    except Exception as e:
        print(f"ERRO CRÍTICO ao processar arquivo OFX: {e}")
        # Retorna um DataFrame vazio em caso de qualquer erro de parsing
        return pd.DataFrame()


def carregar_egestor_csv(arquivo_csv_em_memoria) -> pd.DataFrame:
    """Lê um arquivo CSV em memória e o transforma em um DataFrame do Pandas."""
    print("Lendo o arquivo CSV em memória...")
    try:
        df = pd.read_csv(arquivo_csv_em_memoria, sep=',', encoding='utf-8', header=0, dtype={'Cód.': str})
        
        # Garante que a coluna 'Descrição' exista para evitar erros
        if 'Descrição' not in df.columns:
            print("AVISO: Coluna 'Descrição' não encontrada no CSV. Uma coluna de histórico vazia será usada.")
            df['Descrição'] = ''
            
        df = df.rename(columns={
            'Data de pagamento': 'Data', 'Descrição': 'Historico_eGestor',
            'Valor': 'Valor_eGestor', 'Cód.': 'Codigo_eGestor'
        })
        
        colunas_necessarias = ['Data', 'Historico_eGestor', 'Valor_eGestor', 'Codigo_eGestor']
        df = df[colunas_necessarias].copy()
        
        df.dropna(how='all', inplace=True)
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce', format='%d/%m/%Y')
        df['Valor_eGestor'] = df['Valor_eGestor'].astype(str).apply(limpar_valor_csv)
        df['Valor_eGestor'] = pd.to_numeric(df['Valor_eGestor'], errors='coerce')
        
        # Remove linhas onde a data ou o valor não puderam ser processados
        df.dropna(subset=['Data', 'Valor_eGestor'], inplace=True)
        
        print("Dados do eGestor processados com sucesso.")
        return df
    except Exception as e:
        print(f"ERRO CRÍTICO ao processar arquivo CSV: {e}")
        return pd.DataFrame()

# --- FUNÇÃO PRINCIPAL DE LÓGICA DE NEGÓCIO ---

def gerar_dataframe_conciliacao(df_banco: pd.DataFrame, df_egestor: pd.DataFrame) -> pd.DataFrame:
    """
    Executa a conciliação e retorna um DataFrame do Pandas com o resultado detalhado.
    Esta é a função que a view usará para salvar os dados no banco.
    """
    print("Executando motor de conciliação de precisão...")
    
    # 1. Prepara os DataFrames para a conciliação, arredondando os valores
    df_banco['Valor_Match'] = df_banco['Valor_Banco'].round(2)
    df_egestor['Valor_Match'] = df_egestor['Valor_eGestor'].round(2)
    
    # 2. Primeira mesclagem: Encontra todas as correspondências exatas de Data e Valor.
    #    'indicator=True' cria a coluna '_merge' que nos diz a origem de cada linha.
    df_merged = pd.merge(df_banco.reset_index(), df_egestor.reset_index(), on=['Data', 'Valor_Match'], how='outer', suffixes=('_Banco', '_Gestor'), indicator=True)
    
    # 3. Separa os resultados:
    #    - Conciliados: Itens que existem em ambos os arquivos com mesmo valor e data.
    conciliados = df_merged[df_merged['_merge'] == 'both']
    #    - a_analisar: Itens que não tiveram uma correspondência exata.
    a_analisar = df_merged[df_merged['_merge'] != 'both']
    
    # 4. Isola os itens pendentes de cada fonte.
    pendentes_banco = a_analisar[a_analisar['_merge'] == 'left_only']
    pendentes_gestor = a_analisar[a_analisar['_merge'] == 'right_only']
    
    # 5. Segunda mesclagem: Tenta encontrar divergências de valor.
    #    Une os itens pendentes pela DATA para ver se há lançamentos no mesmo dia com valores diferentes.
    divergencias = pd.merge(pendentes_banco, pendentes_gestor, on='Data', how='outer', suffixes=('_Banco', '_Gestor'))
    
    # 6. Inicia a construção do relatório final em formato de lista de dicionários.
    relatorio_final = []
    
    # 7. Adiciona os itens perfeitamente conciliados ao relatório.
    for _, row in conciliados.iterrows():
        relatorio_final.append({
            'Data': row['Data'],
            'Histórico Banco': row['Historico_Banco'], 
            'Valor Banco': row['Valor_Banco'],
            'Histórico Gestor': row['Historico_eGestor'], 
            'Valor Gestor': row['Valor_eGestor'],
            'Diferença': 0.00, 
            'Status da Conciliação': 'Conciliado'
        })
        
    # 8. Adiciona as divergências e pendências ao relatório.
    for _, row in divergencias.iterrows():
        banco_presente = pd.notna(row.get('Valor_Banco_Banco'))
        gestor_presente = pd.notna(row.get('Valor_eGestor_Gestor'))
        
        status = 'DIVERGÊNCIA DE VALOR' if banco_presente and gestor_presente else ('PENDENTE (APENAS NO BANCO)' if banco_presente else 'PENDENTE (APENAS NO GESTOR)')
        
        # Tratamento robusto para evitar erros de 'NaN'
        valor_banco = row['Valor_Banco_Banco'] if banco_presente else 0.0
        valor_gestor = row['Valor_eGestor_Gestor'] if gestor_presente else 0.0
        
        historico_banco = row['Historico_Banco_Banco'] if banco_presente else ''
        historico_gestor = row['Historico_eGestor_Gestor'] if gestor_presente else ''
        
        relatorio_final.append({
            'Data': row['Data'],
            'Histórico Banco': historico_banco,
            'Valor Banco': valor_banco,
            'Histórico Gestor': historico_gestor,
            'Valor Gestor': valor_gestor,
            'Diferença': round(valor_banco - valor_gestor, 2),
            'Status da Conciliação': status
        })
        
    # 9. Converte a lista final em um DataFrame, ordena e formata para exibição.
    if not relatorio_final:
        return pd.DataFrame() # Retorna DataFrame vazio se não houver transações
        
    df_relatorio = pd.DataFrame(relatorio_final).sort_values(by='Data').reset_index(drop=True)
    df_relatorio['Data'] = pd.to_datetime(df_relatorio['Data']).dt.strftime('%d/%m/%Y')
    
    return df_relatorio

# --- FUNÇÃO DE GERAÇÃO DE ARQUIVO (COM FORMATAÇÃO PROFISSIONAL) ---

def criar_arquivo_excel(df_relatorio: pd.DataFrame) -> io.BytesIO:
    """
    Recebe um DataFrame de conciliação e o converte em um arquivo Excel em memória,
    com formatação profissional para fácil leitura e análise.
    """
    output_em_memoria = io.BytesIO()
    
    # Usa o XlsxWriter como motor para ter acesso às funcionalidades de formatação
    with pd.ExcelWriter(output_em_memoria, engine='xlsxwriter') as writer:
        # Escreve o DataFrame na planilha, sem o cabeçalho padrão do pandas
        df_relatorio.to_excel(writer, sheet_name='Painel de Conciliação', index=False, header=False, startrow=1)
        
        # Pega os objetos workbook e worksheet para trabalhar com eles
        workbook = writer.book
        worksheet = writer.sheets['Painel de Conciliação']

        # --- DEFINIÇÃO DOS ESTILOS DE FORMATAÇÃO ---

        # Formato do cabeçalho: negrito, fundo cinza, texto branco
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#333F4F',
            'font_color': 'white',
            'border': 1
        })

        # Formato para valores monetários
        money_format = workbook.add_format({'num_format': 'R$ #,##0.00', 'border': 1})
        
        # Formato padrão para células de texto
        text_format = workbook.add_format({'border': 1})

        # Formatos para status (formatação condicional)
        status_conciliado_format = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100', 'border': 1})
        status_divergencia_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'border': 1})
        status_pendente_format = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500', 'border': 1})

        # --- APLICAÇÃO DOS ESTILOS ---

        # Escreve o cabeçalho da tabela com o formato personalizado
        for col_num, value in enumerate(df_relatorio.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Ajusta a largura das colunas com base no conteúdo
        for idx, col in enumerate(df_relatorio):
            series = df_relatorio[col]
            max_len = max((
                series.astype(str).map(len).max(),
                len(str(series.name))
            )) + 2  # Adiciona um espaço extra
            worksheet.set_column(idx, idx, max_len)

        # Aplica os formatos de moeda e texto às colunas correspondentes
        worksheet.set_column('B:B', None, money_format) # Valor Banco
        worksheet.set_column('D:D', None, money_format) # Valor Gestor
        worksheet.set_column('E:E', None, money_format) # Diferença
        worksheet.set_column('A:A', None, text_format) # Histórico Banco
        worksheet.set_column('C:C', None, text_format) # Histórico Gestor

        # Aplica a formatação condicional na coluna de Status
        status_col = df_relatorio.columns.get_loc('Status da Conciliação')
        worksheet.conditional_format(1, status_col, len(df_relatorio), status_col, 
                                     {'type': 'cell', 'criteria': '==', 'value': '"Conciliado"', 'format': status_conciliado_format})
        worksheet.conditional_format(1, status_col, len(df_relatorio), status_col, 
                                     {'type': 'cell', 'criteria': '==', 'value': '"DIVERGÊNCIA DE VALOR"', 'format': status_divergencia_format})
        worksheet.conditional_format(1, status_col, len(df_relatorio), status_col, 
                                     {'type': 'text', 'criteria': 'containing', 'value': 'PENDENTE', 'format': status_pendente_format})

        # Congela a linha do cabeçalho para que ela fique visível ao rolar
        worksheet.freeze_panes(1, 0)

    print("Arquivo Excel formatado gerado em memória com sucesso!")
    return output_em_memoria
