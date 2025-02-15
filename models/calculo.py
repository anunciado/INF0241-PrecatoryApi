from pydantic import BaseModel

from models.tipoDeTabelaCorrecao import TipoDeTabelaCorrecao

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