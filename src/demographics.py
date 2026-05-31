"""Perfilado determinístico del encuestado + pesos de correlación.

La demografía se deriva por hash del respondent_id: la misma persona mantiene
siempre el mismo perfil entre encuestas sin persistir estado aleatorio. Los pesos
introducen correlación region/NSE -> respuesta para que segmentación y predicción
muestren patrones reales.
"""
import hashlib

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


def approval_weights(nse: str) -> list[float]:
    return list(_APPROVAL_BY_NSE[nse])
