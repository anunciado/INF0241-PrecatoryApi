import os
import time

import joblib
import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Response
from fastapi import UploadFile, File, Query
from fastapi.responses import FileResponse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select, WebDriverWait
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor

from models import TipoDeTabelaCorrecao

load_dotenv()
app = FastAPI()

BCB_API_URL = os.getenv('BCB_API_URL')
CJF_URL = os.getenv('CJF_URL')
DRIVER_PATH = os.getenv('DRIVER_PATH')
DOWNLOAD_PATH = os.getcwd()


# Rota para retornar os tipos de tabela de correção
@app.get("/get_tipos_tabela_de_correcao")
async def get_tipos_tabela_de_correcao():
    return [tipo.value for tipo in TipoDeTabelaCorrecao]


# Rota para automação
@app.get("/get_ultima_tabela_de_correcao/{tipo_tabela}")
def get_ultima_tabela_de_correcao(tipo_tabela: TipoDeTabelaCorrecao):
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
                caminho_arquivo = "dados_bcb.xlsx"

                # Gera o arquivo Excel
                df_pivot.to_excel(caminho_arquivo)

                # Retorna o arquivo gerado como resposta
                return FileResponse(caminho_arquivo, media_type="application/vnd.ms-excel", filename=caminho_arquivo)

            except requests.RequestException as e:
                return Response(content=f"Erro ao acessar a API: {e}", status_code=500)
            except Exception as e:
                return Response(content=f"Erro ao gerar o arquivo Excel: {e}", status_code=500)
        case 'justica_federal':
            # Configuração do WebDriver (use o caminho correto para o driver do Chrome)
            options = webdriver.ChromeOptions()
            options.add_argument("--headless")  # Opcional: executa o navegador em modo headless
            prefs = {"download.default_directory": DOWNLOAD_PATH}
            options.add_experimental_option("prefs", prefs)
            service = Service(DRIVER_PATH)
            driver = webdriver.Chrome(service=service, options=options)

            try:
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

                # Seleciona "Ações Condenatórias em Geral (devedor não enquadrado como Fazenda Pública)" no select "Tipo de Ação"
                tipo_acao_select = wait.until(ec.presence_of_element_located((By.NAME, "seqEncadeamento")))
                Select(tipo_acao_select).select_by_value("6")

                time.sleep(1)  # Ajuste o tempo conforme necessário para aguardar o download

                # Seleciona o mês mais recente no select "Data Final"
                mes_final_select = wait.until(ec.presence_of_element_located((By.NAME, "mesIndice")))
                Select(mes_final_select).select_by_index(len(Select(mes_final_select).options) - 1)  # Seleciona o último item

                # Seleciona o ano mais recente no select "Data Final"
                ano_final_select = wait.until(ec.presence_of_element_located((By.NAME, "anoIndice")))
                Select(ano_final_select).select_by_index(0)  # Seleciona o primeiro item

                # Seleciona "Não" no select "Com Selic?"
                selic_select = wait.until(ec.presence_of_element_located((By.NAME, "flagSelic")))
                Select(selic_select).select_by_value("0")

                # Clica no botão "Gerar Tabela"
                gerar_tabela_button = wait.until(
                    ec.element_to_be_clickable((By.XPATH, "/html/body/div/form/div[2]/input")))
                gerar_tabela_button.click()

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
                    with open(downloaded_file, "rb") as file:
                        file_data = file.read()

                    # Retorna o arquivo como resposta
                    return Response(
                        content=file_data,
                        media_type="application/vnd.ms-excel",
                        headers={"Content-Disposition": f"attachment; filename={os.path.basename(downloaded_file)}"}
                    )
                else:
                    return {"error": "Arquivo não encontrado."}

            except Exception as e:
                return {"error": str(e)}

            finally:
                driver.quit()

        case _:
            return {"message": "Nada a gerar para o tipo de tabela 'selic'."}


@app.get("/train_model")
def train_model():
    response = requests.get(BCB_API_URL)
    if response.status_code != 200:
        return {"error": "Failed to fetch data from API"}

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

    joblib.dump(model, "teste.apk")
    return FileResponse("teste.apk", media_type='application/octet-stream', filename="teste.apk")


@app.post("/load_model")
def load_model(file: UploadFile = File(...)):
    with open("teste.apk", "wb") as f:
        f.write(file.file.read())

    model = joblib.load("teste.apk")
    return {"message": "Model loaded successfully"}


@app.get("/predict")
def predict_value(ano: int = Query(..., description="Ano para a previsão"),
                  mes: int = Query(..., description="Mês para a previsão")):
    if not os.path.exists("teste.apk"):
        return {"error": "Model not found. Train or load the model first."}

    model = joblib.load("teste.apk")
    input_data = pd.DataFrame([[ano, mes]], columns=["ano", "mes"])
    predicted_value = model.predict(input_data)[0]

    return {
        "ano": ano,
        "mes": mes,
        "predicted_value": predicted_value
    }


@app.get("/calculate")
def calculate_value(valor: float, referencia_ano: int, referencia_mes: int, predicao_ano: int, predicao_mes: int):
    if not os.path.exists("teste.apk"):
        return {"error": "Model not found. Train or load the model first."}

    response = requests.get(BCB_API_URL)
    if response.status_code != 200:
        return {"error": "Failed to fetch data from API"}

    data = response.json()
    df = pd.DataFrame(data)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df.dropna(inplace=True)
    df["mes"] = df["data"].dt.month
    df["ano"] = df["data"].dt.year

    # Carregar o modelo treinado
    model = joblib.load("teste.apk")

    # Determinar a última data no conjunto de dados
    last_date = df["data"].max()

    # Criar uma lista de meses e anos para predição até a data de predicao_ano e predicao_mes
    pred_dates = pd.date_range(start=last_date + pd.offsets.MonthBegin(1),
                               end=pd.Timestamp(year=predicao_ano, month=predicao_mes, day=1),
                               freq="MS")

    # Prever os valores para os meses ausentes
    predictions = []
    for date in pred_dates:
        input_data = pd.DataFrame([[date.year, date.month]], columns=["ano", "mes"])
        predicted_value = model.predict(input_data)[0]
        predictions.append((date, predicted_value))

    # Atualizar o DataFrame com os valores previstos
    for date, value in predictions:
        df = pd.concat([df, pd.DataFrame({"data": [date], "valor": [value], "ano": [date.year], "mes": [date.month]})])

    # Ordenar o DataFrame por data
    df.sort_values(by="data", inplace=True)

    # Calcular os valores cumulativos para previsão até a data de referência
    reference_date = pd.Timestamp(year=referencia_ano, month=referencia_mes, day=1)
    cumulative_value = df.loc[df["data"] >= reference_date, "valor"].cumsum().iloc[-1]

    # Retornar o valor multiplicado pelo valor de referência
    reference_value = df.loc[(df["ano"] == referencia_ano) & (df["mes"] == referencia_mes), "valor"].values[0]
    result = valor * reference_value

    return {
        "reference_date": reference_date.strftime("%Y-%m"),
        "cumulative_value": cumulative_value,
        "result": result
    }
