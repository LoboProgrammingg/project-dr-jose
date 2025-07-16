# planilhas/services.py
import pandas as pd
from io import StringIO
import logging

logger = logging.getLogger(__name__)


def extrair_dados_planilha(arquivo):
    try:
        try:
            df = pd.read_excel(arquivo, dtype=str)
        except Exception as e_excel:
            logger.warning(
                f'Falha ao ler como Excel: {e_excel}. Tentando como CSV.'
            )
            arquivo.seek(0)
            df = pd.read_csv(arquivo, dtype=str)

        df.fillna('', inplace=True)

        return df.to_dict(orient='records')

    except Exception as e:
        logger.error(f'Erro final ao processar o arquivo da planilha: {e}')
        raise ValueError(
            f'Não foi possível ler o arquivo da planilha. Verifique o formato. Erro: {e}'
        )


def gerar_csv_nativo(planilha_nativa):
    if not planilha_nativa.dados:
        return None

    df = pd.DataFrame(planilha_nativa.dados)

    if planilha_nativa.colunas:
        colunas_existentes = [
            col for col in planilha_nativa.colunas if col in df.columns
        ]
        df = df[colunas_existentes]

    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8')

    return csv_buffer.getvalue()
