import pandas as pd
from dashboards.procesamiento import AnalistaDeDatos

def test_es_alquiler_detectado():
    df = pd.DataFrame({"Detalle": ["1x Cuota de membresía por Oficina C&C (algo)"]})
    a = AnalistaDeDatos(df, "VENTAS")
    assert a.df.loc[0, "Es_Alquiler"] == True

def test_montos_convertidos():
    df = pd.DataFrame({"Monto total":["S/ 1.234,50", None]})
    a = AnalistaDeDatos(df, "VENTAS")
    assert a.df.loc[0, "Monto total"] == 1234.5
    assert a.df.loc[1, "Monto total"] == 0
