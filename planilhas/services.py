# planilhas/services.py
import pandas as pd
from io import StringIO
import logging

logger = logging.getLogger(__name__)

def extrair_dados_planilha(arquivo):
    """
    Lê um arquivo de planilha (Excel ou CSV), converte todas as colunas
    para texto para garantir a compatibilidade com JSON, e retorna uma
    lista de dicionários.
    """
    try:
        # Tenta ler como Excel primeiro
        try:
            # dtype=str força o pandas a ler todas as colunas como texto
            df = pd.read_excel(arquivo, dtype=str)
        except Exception as e_excel:
            logger.warning(f"Falha ao ler como Excel: {e_excel}. Tentando como CSV.")
            # Volta para o início do arquivo para tentar ler como CSV
            arquivo.seek(0)
            # dtype=str também para CSV
            df = pd.read_csv(arquivo, dtype=str)

        # Substitui valores vazios ou de erro do pandas (NaN, NaT) por uma string vazia
        # Isso evita problemas de serialização com valores nulos do pandas
        df.fillna('', inplace=True)
        
        # Converte o DataFrame para uma lista de dicionários.
        # Agora, todos os valores são strings, que são JSON-serializáveis.
        return df.to_dict(orient='records')
    
    except Exception as e:
        logger.error(f"Erro final ao processar o arquivo da planilha: {e}")
        raise ValueError(f"Não foi possível ler o arquivo da planilha. Verifique o formato. Erro: {e}")


def gerar_csv_nativo(planilha_nativa):
    """
    Converte os dados JSON de uma PlanilhaNativa para um arquivo CSV em memória.
    """
    if not planilha_nativa.dados:
        return None
    
    df = pd.DataFrame(planilha_nativa.dados)
    
    # Garante que as colunas no CSV sigam a ordem definida
    if planilha_nativa.colunas:
        # Filtra para usar apenas as colunas que realmente existem no DataFrame
        colunas_existentes = [col for col in planilha_nativa.colunas if col in df.columns]
        df = df[colunas_existentes]

    # Cria um buffer de texto para armazenar o CSV
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8')
    
    # Retorna o conteúdo do buffer
    return csv_buffer.getvalue()
