from pydantic import BaseModel

class Resposta(BaseModel):
    """
    Classe que representa uma resposta de sucesso para funções.

    Atributos:
        mensagem (str): A mensagem da resposta.
    """

    mensagem: str
