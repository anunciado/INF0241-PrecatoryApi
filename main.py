import os
import time

import joblib
import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Response, HTTPException, Depends
from fastapi import UploadFile, File
from fastapi.responses import FileResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select, WebDriverWait
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor

from models import TipoDeTabelaCorrecao, Resposta, PredicaoInput, CalculoInput, CalculoOutput, PredicaoOutput
from utils import obter_logger_e_configuracao, commom_verificacao_api_token

load_dotenv()

description = """
        ChimichangApp API helps you do awesome stuff. 🚀
        
        ## Tipo De Tabela Correcao
        
        You can **read items**.
        
        ## Modelo
        
        You will be able to:
        
        * **Create users** (_not implemented_).
        * **Read users** (_not implemented_).
"""

app = FastAPI(
    title="PrecatoryAPI",
    description=description,
    summary="API desenvolvida para auxiliar nos cálculos de precatórios",
    version="0.1",
    contact={
        "name": "Luís Eduardo Anunciado Silva",
        "url": "https://github.com/anunciado/",
        "email": "luissilva@tjrn.jus.br",
    },
    license_info={
        "name": "GPL 3.0",
        "url": "https://www.gnu.org/licenses/gpl-3.0.pt-br.html",
    },
    dependencies=[Depends(commom_verificacao_api_token)],
)

logger = obter_logger_e_configuracao()


BCB_API_URL = os.getenv('BCB_API_URL')
CJF_URL = os.getenv('CJF_URL')
DRIVER_PATH = os.getenv('DRIVER_PATH')
DOWNLOAD_PATH = os.getcwd()


# Rota para retornar os tipos de tabela de correção
@app.get("/get_tipos_tabela_de_correcao")
async def get_tipos_tabela_de_correcao():
    logger.info(f"Requisição de buscar os tipos de tabela de correção recebida.")
    return [tipo.value for tipo in TipoDeTabelaCorrecao]


# Rota para automação
@app.get("/get_last_tabela_de_correcao/{tipo_tabela}")
def get_last_tabela_de_correcao(tipo_tabela: TipoDeTabelaCorrecao):
    logger.info(f"Requisição de buscar última tabela de correção recebida com parâmetro tipo_tabela={tipo_tabela}.")

    match tipo_tabela:
        case 'selic':
            try:
                # Consome os dados da API do Banco Central
                response = requests.get(BCB_API_URL)
                response.raise_for_status()
                dados = response.json()

                # Transforma os dados em um DataFrame do pandas
                df = pd.DataFrame(dados)

                # Ajusta as colunas para o formato esperado
                df.columns = ["Data", "Valor"]

                # Converte a coluna "Data" para o formato datetime
                df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y")

                # Converte a coluna "Valor" para float
                df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")

                # Ordena os dados da mais recente para a mais antiga
                df = df.sort_values(by="Data", ascending=False).reset_index(drop=True)

                # Substitui o primeiro valor por 1
                if not df.empty:
                    df.at[0, "Valor"] = 1

                # Itera sobre os demais dados e ajusta os valores para o valor acumulado
                for i in range(1, len(df)):
                    df.at[i, "Valor"] = df.at[i - 1, "Valor"] + df.at[i, "Valor"] * 0.01

                # Extrai o ano e o mês das datas
                df["Ano"] = df["Data"].dt.year
                df["Mês"] = df["Data"].dt.month_name(locale='pt_BR')

                # Cria uma tabela dinâmica com os anos como linhas e os meses como colunas
                df_pivot = df.pivot(index="Ano", columns="Mês", values="Valor")

                # Ordena as colunas pelo mês do ano
                meses_ordenados = [
                    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
                ]
                df_pivot = df_pivot.reindex(columns=meses_ordenados)

                # Define o caminho do arquivo Excel gerado
                nome_arquivo = "selic.xlsx"

                # Gera o arquivo Excel
                df_pivot.to_excel(nome_arquivo)

                # Retorna o arquivo gerado como resposta
                logger.info(f"Requisição processada com sucesso. Será retornado o arquivo: {nome_arquivo}.")
                return FileResponse(nome_arquivo, media_type="application/vnd.ms-excel", filename=nome_arquivo)

            except requests.RequestException as e:
                raise HTTPException(status_code=500, detail="Erro ao acessar a API externa do BCB.")
            except Exception as e:
                raise HTTPException(status_code=500, detail="Erro ao gerar o arquivo Excel.")
        case 'justica_federal':
            # Configuração do WebDriver (use o caminho correto para o driver do Chrome)
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")  # Opcional: executa o navegador em modo headless
            prefs = {"download.default_directory": DOWNLOAD_PATH}
            options.add_experimental_option("prefs", prefs)
            service = Service(DRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=options)

            try:
                logger.info("Navegador aberto em modo headless.")
                # Navega para a página
                driver.get(CJF_URL)

                # Aguarda o carregamento da página
                wait = WebDriverWait(driver, 5)  # Espera explícita de até 5 segundos

                # Verificar se existe um iframe e alternar para ele
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                if iframes:
                    driver.switch_to.frame(iframes[0])

                # Seleciona "Tabela de Correção Monetária" no select "Tipo de Tabela"
                tipo_tabela_select = wait.until(ec.presence_of_element_located((By.NAME, "tipoTabela")))
                Select(tipo_tabela_select).select_by_value("TCM")
                logger.info("Opção 'Tabela de Correção Monetária' foi selecionada no select de 'Tipo de Tabela'")

                # Seleciona "Ações Condenatórias em Geral (devedor não enquadrado como Fazenda Pública)" no select "Tipo de Ação"
                tipo_acao_select = wait.until(ec.presence_of_element_located((By.NAME, "seqEncadeamento")))
                Select(tipo_acao_select).select_by_value("6")
                logger.info("Opção 'Ações Condenatórias em Geral (devedor não enquadrado como Fazenda Pública)' foi selecionada no select de 'Tipo de Ação'")

                time.sleep(1)  # Ajuste o tempo conforme necessário para aguardar o download

                # Seleciona o mês mais recente no select "Data Final"
                mes_final_select = wait.until(ec.presence_of_element_located((By.NAME, "mesIndice")))
                Select(mes_final_select).select_by_index(
                    len(Select(mes_final_select).options) - 1)  # Seleciona o último item
                logger.info("Opção do último mês foi selecionada no select de mês da 'Data Final'")

                # Seleciona o ano mais recente no select "Data Final"
                ano_final_select = wait.until(ec.presence_of_element_located((By.NAME, "anoIndice")))
                Select(ano_final_select).select_by_index(0)  # Seleciona o primeiro item
                logger.info("Opção do último ano foi selecionada no select de ano da 'Data Final'")

                # Seleciona "Não" no select "Com Selic?"
                selic_select = wait.until(ec.presence_of_element_located((By.NAME, "flagSelic")))
                Select(selic_select).select_by_value("0")
                logger.info("Opção 'NÃO' foi selecionada no select de 'Com Selic?'")

                # Clica no botão "Gerar Tabela"
                gerar_tabela_button = wait.until(
                    ec.element_to_be_clickable((By.XPATH, "/html/body/div/form/div[2]/input")))
                gerar_tabela_button.click()
                logger.info("O botão 'Gerar Tabela' foi clicado.")

                # Aguarda a mudança de página e o arquivo ser baixado
                time.sleep(5)  # Ajuste o tempo conforme necessário para o download do arquivo

                # Verifica o arquivo .xls mais recente na pasta de download
                downloaded_file = None
                latest_time = 0

                for file in os.listdir(DOWNLOAD_PATH):
                    file_path = os.path.join(DOWNLOAD_PATH, file)
                    if file.endswith(".xls") and os.path.isfile(file_path):
                        file_mod_time = os.path.getmtime(file_path)
                        if file_mod_time > latest_time:
                            latest_time = file_mod_time
                            downloaded_file = file_path

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

@app.get("/create_modelo/{tipo_tabela}")
def create_modelo(tipo_tabela: TipoDeTabelaCorrecao):
    logger.info(f"Requisição de criar modelo recebida com parâmetro tipo_tabela={tipo_tabela}")

    apk_model = tipo_tabela.value + ".apk"
    match tipo_tabela:
        case 'selic':
            response = requests.get(BCB_API_URL)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Erro ao acessar a API externa do BCB.")

            data = response.json()
            df = pd.DataFrame(data)
            df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
            df.dropna(inplace=True)

            df["mes"] = df["data"].dt.month
            df["ano"] = df["data"].dt.year
            X = df[["ano", "mes"]]
            y = df["valor"]

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            model = DecisionTreeRegressor()
            model.fit(X_train, y_train)
            logger.info("O modelo foi treinado com sucesso.")

            joblib.dump(model, apk_model)
            logger.info(f"Requisição processada com sucesso. Será retornado o arquivo: {apk_model}")
            return FileResponse(apk_model, media_type='application/octet-stream', filename=apk_model)
        case 'justica_federal':
            raise HTTPException(status_code=501,
                                detail="Criação de modelo da justiça federal ainda não foi implementada.")


@app.post("/post_modelo/{tipo_tabela}")
def post_modelo(tipo_tabela: TipoDeTabelaCorrecao, file: UploadFile = File(...)):
    logger.info(f"Requisição de salvar o modelo recebida com parâmetro tipo_tabela={tipo_tabela}")
    apk_model = tipo_tabela.value + ".apk"

    try:
        with open(apk_model, "wb") as f:
            f.write(file.file.read())
        logger.info(f"Requisição processada com sucesso.")
        return Resposta(mensagem="Modelo carregado com sucesso")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro ao carregar o arquivo do modelo.")


@app.delete("/delete_modelo/{tipo_tabela}")
def delete_modelo(tipo_tabela: TipoDeTabelaCorrecao):
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


@app.put("/update_modelo/{tipo_tabela}")
def update_modelo(tipo_tabela: TipoDeTabelaCorrecao, file: UploadFile = File(...)):
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


@app.get("/get_modelo/{tipo_tabela}")
def get_modelo(tipo_tabela: TipoDeTabelaCorrecao):
    logger.info(f"Requisição de buscar o modelo recebida com parâmetro tipo_tabela={tipo_tabela}")
    apk_model = tipo_tabela.value + ".apk"

    if os.path.exists(apk_model):
        try:
            with open(apk_model, "rb") as f:
                file_content = f.read()
            logger.info(f"Requisição processada com sucesso. Será retornado o arquivo: {apk_model}")
            return Response(content=file_content, media_type="application/octet-stream",
                            headers={"Content-Disposition": f"attachment; filename={apk_model}"})
        except Exception as e:
            raise HTTPException(status_code=500, detail="Erro ao buscar o arquivo do modelo.")
    else:
        raise HTTPException(status_code=404, detail="Arquivo do modelo não encontrado.")


@app.get("/get_predicao")
def get_predicao(predicaoInput: PredicaoInput):
    logger.info(f"Requisição de predição recebida com parâmetros ano={predicaoInput.ano}, mes={predicaoInput.mes}, "
                f"tipo_tabela={predicaoInput.tipo_tabela}")

    apk_model = predicaoInput.tipo_tabela.value + ".apk"

    if not os.path.exists(apk_model):
        raise HTTPException(status_code=500, detail="Modelo não encontrado. Treine ou carregue o modelo primeiro.")

    match predicaoInput.tipo_tabela:
        case 'selic':
            model = joblib.load(apk_model)
            input_data = pd.DataFrame([[predicaoInput.ano, predicaoInput.mes]], columns=["ano", "mes"])
            valor_previsto = model.predict(input_data)[0]
            logger.info(f"Requisição processada com sucesso.")
            return PredicaoOutput(ano=predicaoInput.ano, mes=predicaoInput.mes, valor_previsto=valor_previsto)
        case 'justica_federal':
            raise HTTPException(status_code=501, detail="Predição com o modelo ainda não foi implementada.")


@app.get("/get_calculo")
def get_calculo(calculoInput: CalculoInput):
    logger.info(f"Requisição de cálculo recebida com parâmetros referencia_ano={calculoInput.referencia_ano}, "
                f"referencia_mes={calculoInput.referencia_mes}, predicao_ano={calculoInput.predicao_ano}, "
                f"predicao_mes={calculoInput.predicao_mes}, tipo_tabela={calculoInput.tipo_tabela}")
    apk_model = calculoInput.tipo_tabela.value + ".apk"

    if not os.path.exists(apk_model):
        raise HTTPException(status_code=500, detail="Modelo não encontrado. Treine ou carregue o modelo primeiro.")

    response = requests.get(BCB_API_URL)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Erro ao acessar a API externa do BCB.")

    match calculoInput.tipo_tabela:
        case 'selic':
            data = response.json()
            df = pd.DataFrame(data)
            df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
            df.dropna(inplace=True)
            df["mes"] = df["data"].dt.month
            df["ano"] = df["data"].dt.year

            # Carregar o modelo treinado
            model = joblib.load(apk_model)

            # Determinar a última data no conjunto de dados
            last_date = df["data"].max()

            # Criar uma lista de meses e anos para predição até a data de predicao_ano e predicao_mes
            pred_dates = pd.date_range(start=last_date + pd.offsets.MonthBegin(1),
                                       end=pd.Timestamp(year=calculoInput.predicao_ano,
                                                        month=calculoInput.predicao_mes, day=1),
                                       freq="MS")

            # Prever os valores para os meses ausentes
            predictions = []
            for date in pred_dates:
                input_data = pd.DataFrame([[date.year, date.month]], columns=["ano", "mes"])
                predicted_value = model.predict(input_data)[0]
                predictions.append((date, predicted_value))

            # Atualizar o DataFrame com os valores previstos
            for date, value in predictions:
                df = pd.concat(
                    [df, pd.DataFrame({"data": [date], "valor": [value], "ano": [date.year], "mes": [date.month]})])

            # Ordena os dados da mais recente para a mais antiga
            df = df.sort_values(by="data", ascending=False).reset_index(drop=True)

            # Substitui o primeiro valor por 1
            if not df.empty:
                df.at[0, "valor"] = 1

            # Itera sobre os demais dados e ajusta os valores para o valor acumulado
            for i in range(1, len(df)):
                df.at[i, "valor"] = df.at[i - 1, "valor"] + df.at[i, "valor"] * 0.01

            # Calcular os valores cumulativos para previsão até a data de referência
            reference_date = pd.Timestamp(year=calculoInput.referencia_ano, month=calculoInput.referencia_mes, day=1)
            taxa = df.loc[df["data"] == reference_date].iloc[0]['valor']

            # Retornar o valor multiplicado pelo valor de referência
            valor_previsto = calculoInput.valor * taxa

            logger.info(f"Requisição processada com sucesso.")
            return CalculoOutput(ano=calculoInput.referencia_ano, mes=calculoInput.referencia_mes,
                                 taxa=taxa, valor_previsto=valor_previsto)
        case 'justica_federal':
            raise HTTPException(status_code=501, detail="Predição com o modelo ainda não foi implementada.")