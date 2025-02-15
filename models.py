from enum import Enum
from pydantic import BaseModel

class TipoDeTabelaCorrecao(str, Enum):
    selic = "selic"
    justica_federal = "justica_federal"

class PredicaoInput(BaseModel):
    """
    Classe que representa os parâmetros de entrada para predição do valor de um tipo de tabela.

    Atributos:
        ano (int): Ano previsto.
        mes (int): Mês previsto.
        tipo_tabela (TipoDeTabelaCorrecao): Tipo de tabela.
    """
    ano: int
    mes: int
    tipo_tabela: TipoDeTabelaCorrecao


class PredicaoOutput(BaseModel):
    """
    Classe que representa uma predição do valor de um tipo de tabela.

    Atributos:
        ano (int): Ano previsto.
        mes (int): Mês previsto.
        valor_previsto (float): Valor previsto.
    """
    ano: int
    mes: int
    valor_previsto: float

class CalculoInput(BaseModel):
    """
    Classe que representa os parâmetros de entrada para o cálculo do valor de um tipo de tabela.

    Atributos:
        valor (float): Valor inicial.
        referencia_ano (int) : Ano de referência.
        referencia_mes (int) : Mês de referência.
        predicao_ano (int) : Ano de predição.
        predicao_mes (int) : Mês de predição.
        tipo_tabela (TipoDeTabelaCorrecao): Tipo de tabela.
    """
    valor: float
    referencia_ano: int
    referencia_mes: int
    predicao_ano: int
    predicao_mes: int
    tipo_tabela: TipoDeTabelaCorrecao

class CalculoOutput(BaseModel):
    """
    Classe que representa o cálculo da atualização de um valor no futuro através da predição de um tipo de tabela.

    Atributos:
        predicao_ano (int) : Ano de predição.
        predicao_mes (int) : Mês de predição.
        taxa (float): Taxa calculada.
        valor_previsto (float): Valor previsto.
    """
    ano: int
    mes: int
    taxa: float
    valor_previsto: float


class Resposta(BaseModel):
    """
    Classe que representa uma resposta de sucesso para funções.

    Atributos:
        mensagem (str): A mensagem da resposta.
    """

    mensagem: str