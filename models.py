from enum import Enum
from pydantic import BaseModel


class TipoDeTabelaCorrecao(str, Enum):
    selic = "selic"
    encoge = "encoge"
    justicaFederal = "justicaFederal"

class Numero(BaseModel):
    """
    Classe Numero que herda de BaseModel.

    Atributos:
        numero1 (int): Primeiro número inteiro.
        numero2 (int): Segundo número inteiro.
    """

    numero1: int
    numero2: int


class Resultado(BaseModel):
    """
    Classe que representa o resultado de uma operação.

    Atributos:
        resultado (int): O valor do resultado.
    """

    resultado: int
