import joblib
import pandas as pd
import requests
from fastapi import FastAPI
from fastapi import Response
from fastapi.responses import FileResponse
from statsmodels.tsa.arima.model import ARIMA

app = FastAPI()

API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?formato=json"

@app.get("/gerar-xls")
async def gerar_xls():
    try:
        # Consome os dados da API do Banco Central
        response = requests.get(API_URL)
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

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.responses import FileResponse
import requests
import pandas as pd
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import train_test_split
import joblib
import os

# URL da API do Banco Central
BCB_API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?formato=json"
MODEL_PATH = "decision_tree_model.pkl"

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

    joblib.dump(model, MODEL_PATH)
    return FileResponse(MODEL_PATH, media_type='application/octet-stream', filename=MODEL_PATH)

@app.post("/load_model")
def load_model(file: UploadFile = File(...)):
    with open(MODEL_PATH, "wb") as f:
        f.write(file.file.read())

    model = joblib.load(MODEL_PATH)
    return {"message": "Model loaded successfully"}

@app.get("/predict")
def predict_value(ano: int = Query(..., description="Ano para a previsão"), mes: int = Query(..., description="Mês para a previsão")):
    if not os.path.exists(MODEL_PATH):
        return {"error": "Model not found. Train or load the model first."}

    model = joblib.load(MODEL_PATH)
    input_data = pd.DataFrame([[ano, mes]], columns=["ano", "mes"])
    predicted_value = model.predict(input_data)[0]

    return {
        "ano": ano,
        "mes": mes,
        "predicted_value": predicted_value
    }

@app.get("/calculate")
def calculate_value(valor: float, referencia_ano: int, referencia_mes: int, predicao_ano: int, predicao_mes: int):
    if not os.path.exists(MODEL_PATH):
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
    model = joblib.load(MODEL_PATH)

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