# test_conciliation.py
# Este script serve como um executor para testar a lógica de conciliação
# com arquivos de um ano inteiro, utilizando as funções do `services.py`.

import pandas as pd
import io
import os

# Importa as funções do seu arquivo de serviço.
# É crucial que o arquivo 'services.py' esteja na mesma pasta que este script.
try:
    import services
except ImportError:
    print("ERRO: O arquivo 'services.py' não foi encontrado.")
    print(
        "Por favor, certifique-se de que 'services.py' e 'test_conciliation.py' estão na mesma pasta."
    )
    exit()

# --- CONFIGURAÇÃO DOS ARQUIVOS ---
# Altere os nomes dos arquivos aqui se necessário.
# O arquivo OFX que você converteu do PDF.
OFX_FILE_PATH = 'extrato_anual.ofx'
# O arquivo CSV com os dados do seu sistema.
CSV_FILE_PATH = 'teste2.csv'
# Nome do arquivo Excel que será gerado com o resultado.
OUTPUT_EXCEL_FILE = 'relatorio_conciliacao_anual.xlsx'


def run_annual_reconciliation():
    """
    Função principal que orquestra a leitura dos arquivos, a execução da
    conciliação e a gravação do relatório final em Excel.
    """
    print('--- INICIANDO TESTE DE CONCILIAÇÃO ANUAL ---')

    # 1. Validar se os arquivos de entrada existem
    if not os.path.exists(OFX_FILE_PATH):
        print(f"ERRO: Arquivo OFX não encontrado em '{OFX_FILE_PATH}'")
        print(
            "Por favor, renomeie o seu arquivo OFX para 'extrato_anual.ofx' ou ajuste o nome no script."
        )
        return

    if not os.path.exists(CSV_FILE_PATH):
        print(f"ERRO: Arquivo CSV não encontrado em '{CSV_FILE_PATH}'")
        print(
            "Por favor, certifique-se de que 'teste2.csv' está na pasta correta."
        )
        return

    # 2. Processar o arquivo OFX do banco
    print(f'\n[1/4] Lendo e processando o extrato bancário: {OFX_FILE_PATH}')
    try:
        # A biblioteca ofxparse espera que o arquivo seja aberto em modo binário ('rb')
        with open(OFX_FILE_PATH, 'rb') as ofx_file:
            df_banco = services.processar_banco_ofx(ofx_file)

        if df_banco.empty:
            print(
                'AVISO: Nenhum dado de transação foi extraído do arquivo OFX. Verifique o arquivo.'
            )
            # Continuamos mesmo assim para ver se há dados no CSV.
        else:
            print(
                f'-> Sucesso! {len(df_banco)} transações lidas do extrato bancário.'
            )

    except Exception as e:
        print(f'ERRO CRÍTICO ao tentar ler o arquivo OFX: {e}')
        return

    # 3. Processar o arquivo CSV do sistema eGestor
    print(f'\n[2/4] Lendo e processando a planilha interna: {CSV_FILE_PATH}')
    try:
        # A função `carregar_egestor_csv` espera um stream de arquivo
        with open(CSV_FILE_PATH, 'r', encoding='utf-8') as csv_file:
            df_egestor = services.carregar_egestor_csv(csv_file)

        if df_egestor.empty:
            print(
                'AVISO: Nenhum dado foi extraído do arquivo CSV. Verifique o arquivo.'
            )
        else:
            print(
                f'-> Sucesso! {len(df_egestor)} lançamentos lidos da planilha.'
            )

    except Exception as e:
        print(f'ERRO CRÍTICO ao tentar ler o arquivo CSV: {e}')
        return

    # 4. Gerar o DataFrame da conciliação
    if df_banco.empty and df_egestor.empty:
        print(
            '\nAmbos os arquivos não continham dados. Encerrando o processo.'
        )
        return

    print('\n[3/4] Executando a lógica de conciliação...')
    df_relatorio = services.gerar_dataframe_conciliacao(df_banco, df_egestor)

    if df_relatorio.empty:
        print('AVISO: O relatório de conciliação final está vazio.')
    else:
        print('-> Lógica de conciliação executada com sucesso.')
        print(f'Total de itens no relatório final: {len(df_relatorio)}')
        print('\nResumo do Status:')
        print(df_relatorio['Status da Conciliação'].value_counts().to_string())

    # 5. Criar e salvar o arquivo Excel
    print(f'\n[4/4] Gerando o arquivo Excel: {OUTPUT_EXCEL_FILE}')
    try:
        # A função `criar_arquivo_excel` retorna o arquivo em memória (BytesIO)
        output_em_memoria = services.criar_arquivo_excel(df_relatorio)

        # Para salvar em um arquivo físico, lemos os bytes da memória e escrevemos no disco
        output_em_memoria.seek(0)   # Importante: volta para o início do stream

        with open(OUTPUT_EXCEL_FILE, 'wb') as f:
            f.write(output_em_memoria.read())

        print(f'\n--- SUCESSO! ---')
        print(
            f"O relatório de conciliação foi salvo em: '{os.path.abspath(OUTPUT_EXCEL_FILE)}'"
        )

    except Exception as e:
        print(f'ERRO CRÍTICO ao tentar criar o arquivo Excel: {e}')


if __name__ == '__main__':
    # Garante que o script só será executado quando chamado diretamente
    run_annual_reconciliation()
