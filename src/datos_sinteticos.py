import random
from datetime import datetime, UTC
from pymongo import MongoClient
from config import DATABASE_URL
import uuid
client = MongoClient(DATABASE_URL['mongo'])
db = client["survey_platform"]

cuestionario_1 = {
  "_id": "mineria_05_2026",
  "titulo": "Encuesta sobre minería - Mayo 2026",
  "fecha_creacion": "2026-05-10T14:22:00Z",
  "preguntas": [
    {
      "pregunta_id": "p01",
      "tipo": "multiple_choice",
      "texto": "¿Con qué espacio político se siente más identificado?",
      "label": "Representación política",
      "opciones": [
        { "codigo": 1, "texto": "Partido ultragarca" },
        { "codigo": 2, "texto": "Mentira y propaganda" },
        { "codigo": 3, "texto": "Los inoperantes de siempre" },
        { "codigo": 4, "texto": "Frente de injunables" }
      ]
    },
    {
      "pregunta_id": "p02",
      "tipo": "rango",
      "texto": "¿Qué tan de acuerdo está con la siguiente frase: 'regalar el país a capitales extranjeros es algo beneficioso para la nación'?",
      "label": "Opinión sobre la inversión extranjera en el país",
      "opciones": [
        { "codigo": 1, "texto": "Mucho" },
        { "codigo": 2, "texto": "Algo" },
        { "codigo": 3, "texto": "Poco" }
      ]
    },
    {
      "pregunta_id": "p03",
      "tipo": "rango",
      "texto": "¿Usted cree de verdad que esto tiene algún tipo de arreglo?",
      "label": "Opinión sobre el futuro del país",
      "opciones": [
        { "codigo": 1, "texto": "Totalmente" },
        { "codigo": 2, "texto": "Más o menos" },
        { "codigo": 3, "texto": "Para nada" }
      ]
    }
  ]
}
def cargar_cuestionario(cuestionario):
    db.cuestionarios.replace_one({"_id": cuestionario["_id"]}, cuestionario, upsert=True)
    print("✅ Cuestionario cargado.")

def generar_datos_sinteticos(cuestionario, cant_respuestas = 10):
    fuentes = ["telefono", "digital"]
    respuestas_a_insertar = []
    for i in range(cant_respuestas):
        respuestas_parciales = []
        for pregunta in cuestionario["preguntas"]:
            codigos_posibles = [op["codigo"] for op in pregunta["opciones"]]
            valor_elegido = random.choice(codigos_posibles)
            respuestas_parciales.append({
                "pregunta_id": pregunta["pregunta_id"],
                "valor": valor_elegido
            })
        respuesta_completa = {
            "encuesta_id": "mineria_05_2026",
            "encuestado_id": f"555000{i}",
            "fecha": datetime.now(UTC).isoformat() + "Z", 
            "fuente": random.choice(fuentes), # Aquí tomamos uno de la lista
            "procesado_por_etl": False,
            "respuestas": respuestas_parciales
        }
        respuestas_a_insertar.append(respuesta_completa)
    print(respuestas_a_insertar)
    db.respuestas.insert_many(respuestas_a_insertar)
    print(f"✅ Se generaron {cant_respuestas} respuestas siguiendo la estructura del cuestionario.")

if __name__ == "__main__":
    cargar_cuestionario(cuestionario = cuestionario_1)
    generar_datos_sinteticos(cuestionario = cuestionario_1, cant_respuestas= 10 )