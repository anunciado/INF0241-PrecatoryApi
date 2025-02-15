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


# Rota para retornar os tipos de tabela de correção
@router.get("/get_tipos_tabela_de_correcao")
async def get_tipos_tabela_de_correcao():
    logger.info(f"Requisição de buscar os tipos de tabela de correção recebida.")
    return [tipo.value for tipo in TipoDeTabelaCorrecao]


# Rota para automação
@router.get("/get_last_tabela_de_correcao/{tipo_tabela}")
def get_last_tabela_de_correcao(tipo_tabela: TipoDeTabelaCorrecao):
    logger.info(f"Requisição de buscar última tabela de correção recebida com parâmetro tipo_tabela={tipo_tabela}.")

    match tipo_tabela:
        case 'selic':
            try:
                nome_arquivo = TaxaService.get_tabela_de_correcao_selic()

                # Retorna o arquivo gerado como resposta
                logger.info(f"Requisição processada com sucesso. Será retornado o arquivo: {nome_arquivo}.")
                return FileResponse(nome_arquivo, media_type="application/vnd.ms-excel", filename=nome_arquivo)

            except requests.RequestException as e:
                raise HTTPException(status_code=500, detail="Erro ao acessar a API externa do BCB.")
            except Exception as e:
                raise HTTPException(status_code=500, detail="Erro ao gerar o arquivo Excel.")
        case 'justica_federal':
            driver = TaxaService.get_driver()

            try:
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
                    raise HTTPException(status_code=500, detail="Erro ao baixar o arquivo da página externa do CJF.")

            except Exception as e:
                raise HTTPException(status_code=500, detail="Erro ao acessar a página externa da CJF.")

            finally:
                driver.quit()
                logger.info("Navegador fechado.")
