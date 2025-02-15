from fastapi import FastAPI, Depends

from config.security import commom_verificacao_api_token
from router.api import router

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

app.include_router(router)