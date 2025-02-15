import os

import requests
from fastapi import Response, HTTPException, APIRouter
from fastapi.responses import FileResponse

from config.loggger import obter_logger_e_configuracao
from models.tipoDeTabelaCorrecao import TipoDeTabelaCorrecao
from service.taxa_service import TaxaService

logger = obter_logger_e_configuracao()

router = APIRouter(
    prefix="/taxa/automation",
    tags=["taxa"]
)

@router.get(
    "/get_tipos_tabela_de_correcao",
    summary="Obter tipos de tabela de correção",
    description="Retorna os tipos de tabela de correção disponíveis.",
    response_model=list[str],
    status_code=200
)
async def get_tipos_tabela_de_correcao():
    logger.info(f"Requisição de buscar os tipos de tabela de correção recebida.")
    return [tipo.value for tipo in TipoDeTabelaCorrecao]

@router.get(
    "/get_last_tabela_de_correcao/{tipo_tabela}",
    summary="Obter última tabela de correção",
    description="Retorna a última tabela de correção com base no tipo especificado (SELIC ou Justiça Federal).",
    status_code=200
)
def get_last_tabela_de_correcao(tipo_tabela: TipoDeTabelaCorrecao):
    logger.info(f"Requisição de buscar última tabela de correção recebida com parâmetro tipo_tabela={tipo_tabela}.")

    match tipo_tabela:
        # Caso o tipo seja 'selic'
        case 'selic':
            try:
                # Chama o serviço para obter a tabela de correção SELIC
                nome_arquivo = TaxaService.get_tabela_de_correcao_selic()

                # Retorna o arquivo gerado como resposta
                logger.info(f"Requisição processada com sucesso. Será retornado o arquivo: {nome_arquivo}.")
                return FileResponse(nome_arquivo, media_type="application/vnd.ms-excel", filename=nome_arquivo)

            except requests.RequestException as e:
                logger.error(f"Erro ao acessar a API externa do BCB: {e}")
                raise HTTPException(status_code=500, detail="Erro ao acessar a API externa do BCB.")
            except Exception as e:
                logger.error(f"Erro ao gerar o arquivo Excel: {e}")
                raise HTTPException(status_code=500, detail="Erro ao gerar o arquivo Excel.")

        # Caso o tipo seja 'justica_federal'
        case 'justica_federal':
            # Inicializa o navegador para automação
            driver = TaxaService.get_driver()

            try:
                # Chama o serviço que faz o download da tabela do site da Justiça Federal
                downloaded_file = TaxaService.get_tabela_de_correcao_justica_federal(driver)

                if downloaded_file:
                    logger.info("O arquivo foi baixado com sucesso.")
                    with open(downloaded_file, "rb") as file:
                        file_data = file.read()

                    # Retorna o arquivo como resposta
                    nome_arquivo = os.path.basename(downloaded_file)
                    logger.info(f"Requisição processada com sucesso. Será retornado o arquivo: {nome_arquivo}")
                    return Response(
                        content=file_data,
                        media_type="application/vnd.ms-excel",
                        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"}
                    )
                else:
                    logger.error("Erro ao baixar o arquivo da página externa do CJF.")
                    raise HTTPException(status_code=500,
                                        detail="Erro ao baixar o arquivo da página externa do CJF.")

            except Exception as e:
                logger.error(f"Erro ao acessar a página externa da CJF: {e}")
                raise HTTPException(status_code=500, detail="Erro ao acessar a página externa da CJF.")

            finally:
                # Fecha o navegador após o processo
                driver.quit()
                logger.info("Navegador fechado.")
