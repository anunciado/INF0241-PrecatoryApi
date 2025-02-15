from fastapi import FastAPI, Depends

from config.security import commom_verificacao_api_token
from router.api import router

description = """
PrecatoryAPI foi desenvolvida para auxiliar no cálculo e automação de processos relacionados a precatórios. 🧮
        
## Funcionalidades
        
* Integração com sistema de inteligência artificial para predição de valores após correção monetária.
* Automação de geração de relatórios para cálculos de correção monetária.
* Rotas protegidas por token de API.
"""

app = FastAPI(
    title="PrecatoryAPI",
    description=description,
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

app.include_router(router)