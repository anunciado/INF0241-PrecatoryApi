import os

import requests
from dotenv import load_dotenv
from fastapi import HTTPException, APIRouter
from fastapi import UploadFile, File
from fastapi.responses import FileResponse

from config.loggger import obter_logger_e_configuracao
from models.calculo import CalculoInput, CalculoOutput
from models.predicao import PredicaoInput, PredicaoOutput
from models.resposta import Resposta
from models.tipoDeTabelaCorrecao import TipoDeTabelaCorrecao
from service.taxa_service import TaxaService

load_dotenv()

logger = obter_logger_e_configuracao()

BCB_API_URL = os.getenv('BCB_API_URL')

router = APIRouter(
    prefix="/taxa/ai",
    tags=["taxa"]
)

@router.get(
    "/create_modelo/{tipo_tabela}",
    summary="Criar Modelo",
    description="Cria e retorna um arquivo de modelo com base no tipo de tabela fornecido.",
    status_code=200
)
def create_modelo(tipo_tabela: TipoDeTabelaCorrecao):
    logger.info(f"Requisição de criar modelo recebida com parâmetro tipo_tabela={tipo_tabela}")

    apk_model = tipo_tabela.value + ".apk"
    match tipo_tabela:
        case 'selic':
            response = requests.get(BCB_API_URL)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Erro ao acessar a API externa do BCB.")

            TaxaService.create_modelo_selic(response, apk_model)

            logger.info(f"Requisição processada com sucesso. Será retornado o arquivo: {apk_model}")
            return FileResponse(apk_model, media_type='application/octet-stream', filename=apk_model)
        case 'justica_federal':
            raise HTTPException(status_code=501,
                                detail="Criação de modelo da justiça federal ainda não foi implementada.")


@router.post(
    "/post_modelo/{tipo_tabela}",
    summary="Carregar Modelo",
    description="Carrega um arquivo de modelo para o tipo de tabela fornecido.",
    response_model=Resposta,
    status_code=200
)
def post_modelo(tipo_tabela: TipoDeTabelaCorrecao, file: UploadFile = File(...)) -> Resposta:
    logger.info(f"Requisição de salvar o modelo recebida com parâmetro tipo_tabela={tipo_tabela}")
    apk_model = tipo_tabela.value + ".apk"

    try:
        with open(apk_model, "wb") as f:
            f.write(file.file.read())
        logger.info(f"Requisição processada com sucesso.")
        return Resposta(mensagem="Modelo carregado com sucesso")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao carregar o arquivo do modelo.")


@router.delete(
    "/delete_modelo/{tipo_tabela}",
    summary="Excluir Modelo",
    description="Exclui o modelo correspondente ao tipo de tabela fornecido.",
    response_model=Resposta,
    status_code=200
)
def delete_modelo(tipo_tabela: TipoDeTabelaCorrecao) -> Resposta:
    logger.info(f"Requisição de remover o modelo recebida com parâmetro tipo_tabela={tipo_tabela}")
    apk_model = tipo_tabela.value + ".apk"

    if os.path.exists(apk_model):
        try:
            os.remove(apk_model)
            logger.info(f"Requisição processada com sucesso.")
            return Resposta(mensagem="Modelo excluído com sucesso")
        except Exception as e:
            raise HTTPException(status_code=500, detail="Erro ao remover o arquivo do modelo.")
    else:
        raise HTTPException(status_code=404, detail="Arquivo do modelo não encontrado.")


@router.put(
    "/update_modelo/{tipo_tabela}",
    summary="Atualizar Modelo",
    description="Atualiza um modelo existente com um novo arquivo para o tipo de tabela especificado.",
    response_model=Resposta,
    status_code=200
)
def update_modelo(tipo_tabela: TipoDeTabelaCorrecao, file: UploadFile = File(...)) -> Resposta:
    logger.info(f"Requisição de atualizar o modelo recebida com parâmetro tipo_tabela={tipo_tabela}")
    apk_model = tipo_tabela.value + ".apk"

    if os.path.exists(apk_model):
        try:
            with open(apk_model, "wb") as f:
                f.write(file.file.read())
            logger.info(f"Requisição processada com sucesso.")
            return Resposta(mensagem="Modelo atualizado com sucesso")
        except Exception as e:
            raise HTTPException(status_code=500, detail="Erro ao atualizar o arquivo do modelo.")
    else:
        raise HTTPException(status_code=404, detail="Arquivo do modelo não encontrado.")


@router.get(
    "/get_modelo/{tipo_tabela}",
    summary="Obter Modelo",
    description="Obtém o arquivo de modelo correspondente ao tipo de tabela especificado.",
    status_code=200
)
def get_modelo(tipo_tabela: TipoDeTabelaCorrecao):
    logger.info(f"Requisição de buscar o modelo recebida com parâmetro tipo_tabela={tipo_tabela}")
    apk_model = tipo_tabela.value + ".apk"

    if os.path.exists(apk_model):
        try:
            with open(apk_model, "rb") as f:
                file_content = f.read()
            logger.info(f"Requisição processada com sucesso. Será retornado o arquivo: {apk_model}")
            return FileResponse(apk_model, media_type='application/octet-stream', filename=apk_model)
        except Exception as e:
            raise HTTPException(status_code=500, detail="Erro ao buscar o arquivo do modelo.")
    else:
        raise HTTPException(status_code=404, detail="Arquivo do modelo não encontrado.")


@router.post(
    "/post_predicao",
    summary="Obter Predição",
    description="Gera uma predição com base nos parâmetros de ano, mês e tipo de tabela fornecidos.",
    response_model=PredicaoOutput,
    status_code=200
)
def post_predicao(predicaoInput: PredicaoInput) -> PredicaoOutput:
    logger.info(f"Requisição de predição recebida com parâmetros ano={predicaoInput.ano}, mes={predicaoInput.mes}, "
                f"tipo_tabela={predicaoInput.tipo_tabela}")

    apk_model = predicaoInput.tipo_tabela.value + ".apk"

    if not os.path.exists(apk_model):
        raise HTTPException(status_code=500, detail="Modelo não encontrado. Treine ou carregue o modelo primeiro.")

    match predicaoInput.tipo_tabela:
        case 'selic':
            valor_previsto = TaxaService.get_predicao_selic(apk_model, predicaoInput)
            logger.info(f"Requisição processada com sucesso.")
            return PredicaoOutput(ano=predicaoInput.ano, mes=predicaoInput.mes, valor_previsto=valor_previsto)
        case 'justica_federal':
            raise HTTPException(status_code=501, detail="Predição com o modelo ainda não foi implementada.")


@router.post(
    "/post_calculo",
    summary="Obter Cálculo",
    description="Realiza um cálculo com base nos parâmetros de referência e predição fornecidos.",
    response_model=CalculoOutput,
    status_code=200
)
def post_calculo(calculoInput: CalculoInput) -> CalculoOutput:
    logger.info(f"Requisição de cálculo recebida com parâmetros referencia_ano={calculoInput.referencia_ano}, "
                f"referencia_mes={calculoInput.referencia_mes}, predicao_ano={calculoInput.predicao_ano}, "
                f"predicao_mes={calculoInput.predicao_mes}, tipo_tabela={calculoInput.tipo_tabela}")
    apk_model = calculoInput.tipo_tabela.value + ".apk"

    if not os.path.exists(apk_model):
        raise HTTPException(status_code=500, detail="Modelo não encontrado. Treine ou carregue o modelo primeiro.")

    match calculoInput.tipo_tabela:
        case 'selic':
            response = requests.get(BCB_API_URL)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Erro ao acessar a API externa do BCB.")
            taxa, valor_previsto = TaxaService.get_calculo_selic(apk_model, calculoInput, response)

            logger.info(f"Requisição processada com sucesso.")
            return CalculoOutput(ano=calculoInput.referencia_ano, mes=calculoInput.referencia_mes,
                                 taxa=taxa, valor_previsto=valor_previsto)
        case 'justica_federal':
            raise HTTPException(status_code=501, detail="Predição com o modelo ainda não foi implementada.")
