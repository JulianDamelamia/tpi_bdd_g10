"""Perfilado determinístico del encuestado + pesos de correlación.

La demografía se deriva por hash del respondent_id: la misma persona mantiene
siempre el mismo perfil entre encuestas sin persistir estado aleatorio. Los pesos
introducen correlación region/NSE -> respuesta para que segmentación y predicción
muestren patrones reales.
"""
import datetime as dt
import hashlib
import math

REGIONS = ["AMBA", "Centro", "NOA", "NEA", "Cuyo", "Patagonia"]
NSE_LEVELS = ["alto", "medio", "bajo"]
PARTIES = ["Frente Federal", "Movimiento Popular", "Union Republicana",
           "Alianza Verde", "Partido Vecinal"]
APPROVAL = ["Muy buena", "Buena", "Regular", "Mala", "Muy mala"]


def grupo_etario(edad: int) -> str:
    if edad < 30:
        return "16-29"
    if edad < 45:
        return "30-44"
    if edad < 65:
        return "45-64"
    return "65+"


def profile_for(respondent_id: str) -> dict:
    h = hashlib.sha256(respondent_id.encode("utf-8")).digest()
    region = REGIONS[h[0] % len(REGIONS)]
    nse = NSE_LEVELS[h[1] % len(NSE_LEVELS)]
    g = h[2] % 100
    genero = "X" if g < 4 else ("F" if g % 2 == 0 else "M")
    edad = 16 + (int.from_bytes(h[3:5], "big") % 75)
    return {"respondent_id": respondent_id, "edad": edad,
            "grupo_etario": grupo_etario(edad), "region": region,
            "nse": nse, "genero": genero}


_REGION_BIAS = {
    "AMBA":      [1.6, 1.3, 0.7, 1.0, 0.6],
    "Centro":    [0.8, 0.9, 1.8, 1.1, 0.7],
    "NOA":       [1.7, 1.2, 0.6, 0.8, 1.0],
    "NEA":       [1.6, 1.3, 0.6, 0.7, 1.1],
    "Cuyo":      [0.9, 0.8, 1.6, 1.0, 0.9],
    "Patagonia": [1.0, 0.9, 1.1, 1.6, 0.8],
}
_NSE_BIAS = {
    "alto":  [0.7, 0.8, 1.8, 1.2, 0.6],
    "medio": [1.1, 1.1, 1.0, 1.0, 1.0],
    "bajo":  [1.7, 1.3, 0.6, 0.7, 1.2],
}
# imagen sesgada a negativa (contexto de ajuste/desfinanciamiento), con gradiente
# por NSE: el NSE alto la sufre menos, el bajo es el mas critico.
# orden de opciones: [Muy buena, Buena, Regular, Mala, Muy mala]
_APPROVAL_BY_NSE = {
    "alto":  [0.9, 1.2, 1.4, 1.4, 1.0],
    "medio": [0.5, 0.9, 1.2, 1.7, 1.6],
    "bajo":  [0.3, 0.5, 1.0, 1.9, 2.4],
}


def party_weights(region: str, nse: str) -> list[float]:
    rb, nb = _REGION_BIAS[region], _NSE_BIAS[nse]
    return [rb[i] * nb[i] for i in range(len(PARTIES))]


# polaridad de cada opcion: [Muy buena, Buena, Regular, Mala, Muy mala]
_POLARITY = [1.0, 0.5, 0.0, -0.5, -1.0]
_FECHA_BASE = dt.date(2024, 1, 1)
_HORIZONTE_DIAS = 1000


def clima_imagen(fecha: dt.date) -> float:
    """Humor social hacia el gobierno en una fecha. Arranca apenas tibio y se
    derrumba: tendencia negativa fuerte + olas (sube/baja) + shocks mensuales
    deterministicos para que la serie quede bien movida."""
    dias = (fecha - _FECHA_BASE).days
    t01 = dias / _HORIZONTE_DIAS
    tendencia = 0.2 - 2.6 * t01                        # de +0.2 a -2.4: se desploma
    ola = 0.55 * math.sin(2 * math.pi * dias / 95)     # sube y baja
    h = hashlib.sha256(f"{fecha.year}-{fecha.month}".encode()).digest()
    shock = (h[0] / 255.0 - 0.5) * 1.1                 # golpe mensual ~[-0.55, 0.55]
    return tendencia + ola + shock


def approval_weights(nse: str, fecha: dt.date | None = None) -> list[float]:
    base = _APPROVAL_BY_NSE[nse]
    if fecha is None:
        return list(base)
    c = clima_imagen(fecha)
    beta = 1.4
    return [base[i] * math.exp(beta * c * _POLARITY[i]) for i in range(len(base))]
