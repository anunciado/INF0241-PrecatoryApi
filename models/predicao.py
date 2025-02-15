from pydantic import BaseModel

from models.tipoDeTabelaCorrecao import TipoDeTabelaCorrecao

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