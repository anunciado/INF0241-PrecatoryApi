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

@app.get("/predict_next_month")
def predict_next_month():
    # 1. Consumo dos dados da API
    response = requests.get(API_URL)
    if response.status_code != 200:
        return {"error": "Failed to fetch data from API"}

    data = response.json()

    # 2. Conversão dos dados para DataFrame
    df = pd.DataFrame(data)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df.dropna(inplace=True)

    # 3. Ordenação por data
    df.sort_values(by="data", inplace=True)
    df.set_index("data", inplace=True)

    # 4. Treinamento do modelo ARIMA
    model = ARIMA(df["valor"], order=(5, 1, 0))  # Ordem (p, d, q) ajustada como exemplo
    model_fit = model.fit()

    # 5. Salvamento do modelo em um arquivo
    joblib.dump(model_fit, "arima_model.pkl")

    # 6. Determinar a data do próximo mês
    last_date = df.index[-1]
    next_month_date = last_date + pd.offsets.MonthBegin(1)

    # 7. Fazer a previsão para o próximo mês
    forecast = model_fit.get_forecast(steps=1)
    predicted_value = forecast.predicted_mean[0]

    return {
        "next_month": next_month_date.strftime("%Y-%m"),
        "predicted_value": predicted_value
    }
