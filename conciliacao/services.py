# conciliacao/services.py

import pandas as pd
from ofxparse import OfxParser
import re
import io # Import 'io' para lidar com arquivos em memória

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
    """
    Lê um arquivo OFX em memória e o transforma em um DataFrame do Pandas.
    Implementa uma lógica robusta de decodificação para evitar erros de 'charmap'.
    """
    print("Iniciando processamento do extrato OFX em memória...")
    
    # 1. Lê todo o conteúdo do arquivo em memória como bytes.
    #    Isso é crucial para podermos tentar diferentes decodificações.
    arquivo_ofx_em_memoria.seek(0) # Garante que a leitura comece do início
    conteudo_bytes = arquivo_ofx_em_memoria.read()
    
    conteudo_texto = None
    try:
        # 2. Tenta decodificar os bytes usando a codificação mais moderna (UTF-8).
        conteudo_texto = conteudo_bytes.decode('utf-8')
        print("Arquivo OFX decodificado com sucesso usando UTF-8.")
    except UnicodeDecodeError:
        # 3. Se UTF-8 falhar, tenta latin-1, comum em sistemas legados no Brasil.
        print("Falha ao decodificar como UTF-8. Tentando como 'latin-1'...")
        try:
            conteudo_texto = conteudo_bytes.decode('latin-1')
            print("Arquivo OFX decodificado com sucesso usando latin-1.")
        except Exception as e:
            print(f"ERRO CRÍTICO: Não foi possível decodificar o arquivo OFX com as codificações testadas. Erro: {e}")
            return pd.DataFrame() # Retorna DataFrame vazio em caso de falha total
            
    if not conteudo_texto:
        print("ERRO CRÍTICO: O conteúdo do arquivo OFX está vazio ou não pôde ser lido.")
        return pd.DataFrame()

    try:
        # 4. Usa io.StringIO para que a biblioteca 'ofxparse' leia o texto decodificado como se fosse um arquivo.
        ofx = OfxParser.parse(io.StringIO(conteudo_texto))
        
        transacoes = []
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
        print(f"Processamento do OFX concluído. Encontradas {len(df_banco)} transações.")
        return df_banco.sort_values(by="Data").reset_index(drop=True)

    except Exception as e:
        print(f"ERRO CRÍTICO ao fazer o parse do conteúdo OFX: {e}")
        # Retorna um DataFrame vazio em caso de qualquer erro de parsing
        return pd.DataFrame()


def carregar_egestor_csv(arquivo_csv_em_memoria) -> pd.DataFrame:
    """Lê um arquivo CSV em memória e o transforma em um DataFrame do Pandas."""
    print("Lendo o arquivo CSV em memória...")
    try:
        # Garante que a leitura comece do início do arquivo em memória
        arquivo_csv_em_memoria.seek(0)
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
    
    # Verifica se os dataframes estão vazios antes de prosseguir
    if df_banco.empty or df_egestor.empty:
        print("AVISO: Um dos DataFrames está vazio. Não é possível realizar a conciliação.")
        # Pode retornar um dataframe vazio ou uma estrutura específica indicando o erro
        return pd.DataFrame()

    # 1. Prepara os DataFrames para a conciliação, arredondando os valores
    df_banco['Valor_Match'] = df_banco['Valor_Banco'].round(2)
    df_egestor['Valor_Match'] = df_egestor['Valor_eGestor'].round(2)
    
    # 2. Primeira mesclagem: Encontra todas as correspondências exatas de Data e Valor.
    df_merged = pd.merge(df_banco.reset_index(), df_egestor.reset_index(), on=['Data', 'Valor_Match'], how='outer', suffixes=('_Banco', '_Gestor'), indicator=True)
    
    # 3. Separa os resultados:
    conciliados = df_merged[df_merged['_merge'] == 'both']
    a_analisar = df_merged[df_merged['_merge'] != 'both']
    
    # 4. Isola os itens pendentes de cada fonte.
    pendentes_banco = a_analisar[a_analisar['_merge'] == 'left_only']
    pendentes_gestor = a_analisar[a_analisar['_merge'] == 'right_only']
    
    # 5. Segunda mesclagem: Tenta encontrar divergências de valor.
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
        return pd.DataFrame()
        
    df_relatorio = pd.DataFrame(relatorio_final).sort_values(by='Data').reset_index(drop=True)
    # A conversão para string é feita no final, antes de gerar o Excel
    # df_relatorio['Data'] = pd.to_datetime(df_relatorio['Data']).dt.strftime('%d/%m/%Y')
    
    return df_relatorio

# --- FUNÇÃO DE GERAÇÃO DE ARQUIVO (COM FORMATAÇÃO PROFISSIONAL) ---

def criar_arquivo_excel(df_relatorio: pd.DataFrame) -> io.BytesIO:
    """
    Recebe um DataFrame de conciliação e o converte em um arquivo Excel em memória,
    com formatação profissional para fácil leitura e análise.
    """
    output_em_memoria = io.BytesIO()
    
    # Formata a coluna de data para o padrão brasileiro ANTES de salvar no Excel
    df_relatorio_formatado = df_relatorio.copy()
    df_relatorio_formatado['Data'] = pd.to_datetime(df_relatorio_formatado['Data']).dt.strftime('%d/%m/%Y')

    with pd.ExcelWriter(output_em_memoria, engine='xlsxwriter', datetime_format='dd/mm/yyyy') as writer:
        df_relatorio_formatado.to_excel(writer, sheet_name='Painel de Conciliação', index=False, header=False, startrow=1)
        
        workbook = writer.book
        worksheet = writer.sheets['Painel de Conciliação']

        # --- DEFINIÇÃO DOS ESTILOS DE FORMATAÇÃO ---
        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'top',
            'fg_color': '#333F4F', 'font_color': 'white', 'border': 1
        })
        money_format = workbook.add_format({'num_format': 'R$ #,##0.00', 'border': 1})
        text_format = workbook.add_format({'border': 1})
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy', 'border': 1})
        
        status_conciliado_format = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100', 'border': 1})
        status_divergencia_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'border': 1})
        status_pendente_format = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500', 'border': 1})

        # --- APLICAÇÃO DOS ESTILOS ---
        for col_num, value in enumerate(df_relatorio_formatado.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Ajusta a largura das colunas
        worksheet.set_column('A:A', 12, date_format)  # Data
        worksheet.set_column('B:B', 40, text_format)  # Histórico Banco
        worksheet.set_column('C:C', 15, money_format) # Valor Banco
        worksheet.set_column('D:D', 40, text_format)  # Histórico Gestor
        worksheet.set_column('E:E', 15, money_format) # Valor Gestor
        worksheet.set_column('F:F', 15, money_format) # Diferença
        worksheet.set_column('G:G', 25, text_format)  # Status

        # Aplica formatação condicional na coluna de Status
        status_col_letter = 'G'
        worksheet.conditional_format(f'{status_col_letter}2:{status_col_letter}{len(df_relatorio_formatado)+1}', 
                                     {'type': 'cell', 'criteria': '==', 'value': '"Conciliado"', 'format': status_conciliado_format})
        worksheet.conditional_format(f'{status_col_letter}2:{status_col_letter}{len(df_relatorio_formatado)+1}', 
                                     {'type': 'cell', 'criteria': '==', 'value': '"DIVERGÊNCIA DE VALOR"', 'format': status_divergencia_format})
        worksheet.conditional_format(f'{status_col_letter}2:{status_col_letter}{len(df_relatorio_formatado)+1}', 
                                     {'type': 'text', 'criteria': 'containing', 'value': 'PENDENTE', 'format': status_pendente_format})

        worksheet.freeze_panes(1, 0)

    print("Arquivo Excel formatado gerado em memória com sucesso!")
    # Retorna ao início do stream para que o Django possa lê-lo para a resposta HTTP
    output_em_memoria.seek(0)
    return output_em_memoria
