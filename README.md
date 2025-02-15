# INF0241-PrecatoryApi
Uma API de precatórios judiciais usando REST para a classe UFG INF INF0241: Construindo APIs para Inteligência Artificial.

## Funcionalidades

- Automação de geração de relatórios para cálculos de correção monetária.        
- Integração com sistema de inteligência artificial para predição de valores após correção monetária.
- Rotas protegidas por token de API.

## Tecnologias

 - Python 3, uma linguagem de programação de alto nível e de propósito geral,
 - FastAPI, um framework Python para construção de APIs;
 - Selenium, um framework para interagir com aplicações web,
 - Pandas, uma ferramenta de análise e manipulação de dados;
 - Sklearn, uma ferramenta para aprendizado de máquina construído sobre a biblioteca SciPy;
 - Swagger, uma especificação aberta para definição de APIs REST.

## Configuração do ambiente de desenvolvimento

1. Instale o python, na versão 3.10, através do (link)[https://www.python.org/downloads/];
2. Instale o navegador do chrome através do (link)[https://www.google.com/chrome/];
3. Clone este repositório https://github.com/anunciado/INF0241-PrecatoryAp.git em sua máquina local;
4. Baixe o driver, respeitando a versão do chrome instalada em sua máquina, através do (link)[https://googlechromelabs.github.io/chrome-for-testing/] e coloque o arquivo na raiz do projeto;
6. Abra o projeto em sua IDE de preferência, como sugestão utilize o Visual Studio Code ou PyCharm;
7. Crie um ambiente virtual com o comando:
```
. python -m venv venv
```
7. Ative o ambiente virtual com o comando:
* No windows:
```
venv\Scripts\activate
```
* No linux:
```
source venv/bin/activate
```
8. Instale as bibliotecas no seu ambiente virtual a partir do arquivo _requirements.txt_ com o comando:
```
pip install -r requirements.txt
```
8. Crie um arquivo _.env_ na raiz do projeto como no exemplo arquivo _.env.sample_ com os seguintes parâmetros, alterando o DRIVER_PATH, colocando o path pro driver e API_TOKEN, uma senha pessoa para acesso as rotas.
```
BCB_API_URL=https://api.bcb.gov.br/dados/serie/bcdata.sgs.4390/dados?formato=json
CJF_URL=https://sicom.cjf.jus.br/tabelaCorMor.php
DRIVER_PATH=./chromedriver.exe
API_TOKEN=suausenha
```
9. Execute o projeto com o comando:
```
fastapi dev main.py
```

## Swagger 

O swagger com todos os exemplos de uso do sistema está disponível em: http://localhost:8080/docs.

Para se autenticar usando o swagger use a _API_TOKEN_ definida no arquivo _.env_ como parâmetro _api_token_ nas rotas. 

## Contribuição:

1. `Mova` a issue a ser resolvida para a coluna _In Progress_ no [board do projeto].  
2. `Clone` este repositório https://github.com/anunciado/INF0241-PrecatoryAp.git.
3. `Crie` um branch a partir da branch _dev_.
4. `Commit` suas alterações.
5. `Realize` o push das alterações.
6. `Crie` a solicitação PR para branch _dev_.
7. `Mova` a _issue_ da coluna _In Progress_ para a coluna _Code Review_ do [board do projeto].

## Desenvolvedores

- [Luís Eduardo](https://github.com/anunciado)
