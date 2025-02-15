import os
import time

import joblib
import pandas as pd
import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import Select, WebDriverWait
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor

from config.loggger import obter_logger_e_configuracao

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém o logger para registrar mensagens
logger = obter_logger_e_configuracao()

# URLs e caminhos de configuração obtidos das variáveis de ambiente
BCB_API_URL = os.getenv('BCB_API_URL')
CJF_URL = os.getenv('CJF_URL')
DRIVER_PATH = os.getenv('DRIVER_PATH')
DOWNLOAD_PATH = os.getcwd()  # Diretório atual como pasta de download

class TaxaService:

    # Cria e treina um modelo de regressão com as taxas da SELIC
    @staticmethod
    def create_modelo_selic(response, apk_model):
        data = response.json()
        df = pd.DataFrame(data)

        # Filtra os dados
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        df.dropna(inplace=True)

        # Cria as colunas de mês e ano a partir da data
        df["mes"] = df["data"].dt.month
        df["ano"] = df["data"].dt.year
        X = df[["ano", "mes"]]
        y = df["valor"]

        # Divide os dados entre treino e teste
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Instancia o modelo de árvore de decisão
        model = DecisionTreeRegressor()

        # Treina o modelo
        model.fit(X_train, y_train)
        logger.info("O modelo foi treinado com sucesso.")

        # Salva o modelo treinado em um arquivo
        joblib.dump(model, apk_model)

    # Realiza uma previsão da taxa SELIC para uma determinada entrada de ano e mês
    @staticmethod
    def get_predicao_selic(apk_model, predicaoInput):
        # Carrega o modelo salvo
        model = joblib.load(apk_model)

        # Cria um DataFrame para a entrada de previsão
        input_data = pd.DataFrame([[predicaoInput.ano, predicaoInput.mes]], columns=["ano", "mes"])

        # Faz a previsão
        valor_previsto = model.predict(input_data)[0]
        return valor_previsto

    # Calcula os valores acumulados da SELIC para um intervalo de tempo específico
    @staticmethod
    def get_calculo_selic(apk_model, calculoInput, response):
        data = response.json()
        df = pd.DataFrame(data)

        # Filtra os dados
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        df.dropna(inplace=True)
        df["mes"] = df["data"].dt.month
        df["ano"] = df["data"].dt.year

        # Carrega o modelo salvo
        model = joblib.load(apk_model)

        # Determina a última data presente no dataset
        last_date = df["data"].max()

        # Gera as datas para predição a partir da última data do dataset até a data de cálculo desejada
        pred_dates = pd.date_range(start=last_date + pd.offsets.MonthBegin(1),
                                   end=pd.Timestamp(year=calculoInput.predicao_ano,
                                                    month=calculoInput.predicao_mes, day=1),
                                   freq="MS")
        predictions = []

        # Para cada data gerada, faz a previsão do valor
        for date in pred_dates:
            input_data = pd.DataFrame([[date.year, date.month]], columns=["ano", "mes"])
            predicted_value = model.predict(input_data)[0]
            predictions.append((date, predicted_value))

        # Atualiza o DataFrame com os valores previstos
        for date, value in predictions:
            df = pd.concat(
                [df, pd.DataFrame({"data": [date], "valor": [value], "ano": [date.year], "mes": [date.month]})])

        # Ordena os dados
        df = df.sort_values(by="data", ascending=False).reset_index(drop=True)

        # Substitui o primeiro valor por 1
        if not df.empty:
            df.at[0, "valor"] = 1

        # Calcula os valores cumulativos
        for i in range(1, len(df)):
            df.at[i, "valor"] = df.at[i - 1, "valor"] + df.at[i, "valor"] * 0.01
        reference_date = pd.Timestamp(year=calculoInput.referencia_ano, month=calculoInput.referencia_mes, day=1)

        # Obtém a taxa correspondente à referência
        taxa = df.loc[df["data"] == reference_date].iloc[0]['valor']

        # Calcula o valor corrigido
        valor_previsto = calculoInput.valor * taxa
        return taxa, valor_previsto

    # Gera uma tabela de correção monetária com base nos dados da SELIC
    @staticmethod
    def get_tabela_de_correcao_selic():

        # Faz requisição à API do Banco Central
        response = requests.get(BCB_API_URL)
        response.raise_for_status()
        dados = response.json()

        df = pd.DataFrame(dados)
        df.columns = ["Data", "Valor"]
        df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y")
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")

        # Ordena os dados
        df = df.sort_values(by="Data", ascending=False).reset_index(drop=True)

        # Substitui o primeiro valor por 1
        if not df.empty:
            df.at[0, "Valor"] = 1

        # Calcula os valores acumulativos
        for i in range(1, len(df)):
            df.at[i, "Valor"] = df.at[i - 1, "Valor"] + df.at[i, "Valor"] * 0.01
        df["Ano"] = df["Data"].dt.year
        df["Mês"] = df["Data"].dt.month_name(locale='pt_BR')

        # Cria uma tabela dinâmica
        df_pivot = df.pivot(index="Ano", columns="Mês", values="Valor")
        meses_ordenados = [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ]
        df_pivot = df_pivot.reindex(columns=meses_ordenados)

        nome_arquivo = "selic.xlsx"
        df_pivot.to_excel(nome_arquivo)

        return nome_arquivo

    # Obtém a tabela de correção monetária do site da Justiça Federal
    @staticmethod
    def get_tabela_de_correcao_justica_federal(driver):
        logger.info("Navegador aberto em modo headless.")

        # Abre a URL da Justiça Federal
        driver.get(CJF_URL)

        # Define uma espera explícita de até 5 segundos para carregar a página
        wait = WebDriverWait(driver, 5)

        # Verifica a presença de iframes e alterna para o iframe, se existir
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            driver.switch_to.frame(iframes[0])

        # Seleciona a tabela de correção monetária
        tipo_tabela_select = wait.until(ec.presence_of_element_located((By.NAME, "tipoTabela")))
        Select(tipo_tabela_select).select_by_value("TCM")
        logger.info("Opção 'Tabela de Correção Monetária' foi selecionada no select de 'Tipo de Tabela'")

        # Seleciona o tipo de ação
        tipo_acao_select = wait.until(ec.presence_of_element_located((By.NAME, "seqEncadeamento")))
        Select(tipo_acao_select).select_by_value("6")
        logger.info(
            "Opção 'Ações Condenatórias em Geral (devedor não enquadrado como Fazenda Pública)' foi selecionada no select de 'Tipo de Ação'")

        # Aguarda o tempo para efetivar a seleção
        time.sleep(1)

        # Seleciona o último mês
        mes_final_select = wait.until(ec.presence_of_element_located((By.NAME, "mesIndice")))
        Select(mes_final_select).select_by_index(len(Select(mes_final_select).options) - 1)
        logger.info("Opção do último mês foi selecionada no select de mês da 'Data Final'")

        # Seleciona o primeiro ano
        ano_final_select = wait.until(ec.presence_of_element_located((By.NAME, "anoIndice")))
        Select(ano_final_select).select_by_index(0)
        logger.info("Opção do primeiro ano foi selecionada no select de ano da 'Data Final'")

        # Seleciona 'Não' para o uso da SELIC
        selic_select = wait.until(ec.presence_of_element_located((By.NAME, "flagSelic")))
        Select(selic_select).select_by_value("0")
        logger.info("Opção 'NÃO' foi selecionada no select de 'Com Selic?'")

        # Clica no botão para gerar a tabela
        gerar_tabela_button = wait.until(ec.element_to_be_clickable((By.XPATH, "/html/body/div/form/div[2]/input")))
        gerar_tabela_button.click()
        logger.info("O botão 'Gerar Tabela' foi clicado.")

        # Aguarda o tempo de download do arquivo
        time.sleep(5)
        downloaded_file = None
        latest_time = 0

        # Verifica o arquivo .xls mais recente no diretório de download
        for file in os.listdir(DOWNLOAD_PATH):
            file_path = os.path.join(DOWNLOAD_PATH, file)
            if file.endswith(".xls") and os.path.isfile(file_path):
                file_mod_time = os.path.getmtime(file_path)
                if file_mod_time > latest_time:
                    latest_time = file_mod_time
                    downloaded_file = file_path

        # Retorna o caminho do arquivo baixado
        return downloaded_file

    # Configuração e inicialização do WebDriver
    @staticmethod
    def get_driver():
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        prefs = {"download.default_directory": DOWNLOAD_PATH}
        options.add_experimental_option("prefs", prefs)
        service = Service(DRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=options)
        return driver
