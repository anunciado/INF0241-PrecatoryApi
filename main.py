from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.responses import FileResponse
import requests
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
from io import BytesIO

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

        # Extrai o ano e o mês das datas
        df["Ano"] = df["Data"].dt.year
        df["Mês"] = df["Data"].dt.month_name()

        # Converte a coluna "Valor" para float
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")

        # Cria uma tabela dinâmica com os anos como linhas e os meses como colunas
        df_pivot = df.pivot(index="Ano", columns="Mês", values="Valor")

        # Ordena as colunas pelo mês do ano
        meses_ordenados = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
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

@app.post("/train")
async def train_model(file: UploadFile = File(...)):
    # Verifica se o arquivo é Excel
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Arquivo deve ser um Excel.")

    try:
        # Lê o arquivo Excel em um DataFrame Pandas
        contents = await file.read()  # Lê o conteúdo do arquivo
        excel_data = BytesIO(contents)  # Converte o conteúdo para BytesIO
        df = pd.read_excel(excel_data)

        # Verifica se o DataFrame tem uma coluna de valores
        if df.shape[1] < 2:
            raise HTTPException(status_code=400, detail="O arquivo precisa ter pelo menos duas colunas (índice e valor).")

        # Supondo que a última coluna contenha os dados de interesse
        y = df.iloc[:, -1]

        # Remove valores NaN
        y = y.dropna().reset_index(drop=True)

        X = np.arange(len(y)).reshape(-1, 1)  # Índice como variável independente

        # Treina o modelo de regressão linear
        model = LinearRegression()
        model.fit(X, y)

        # Faz predições para os próximos 5 pontos
        future_indices = np.arange(len(y), len(y) + 5).reshape(-1, 1)
        predictions = model.predict(future_indices)

        # Retorna as previsões como lista
        return {"predictions": predictions.tolist()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar o arquivo: {str(e)}")
