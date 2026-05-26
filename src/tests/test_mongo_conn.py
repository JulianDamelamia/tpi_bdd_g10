from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

def test_connection():
    # La URL de conexión al contenedor que definimos en Docker Compose
    uri = "mongodb://localhost:27017/"
    
    try:
        # Intentamos conectar con un timeout corto para no esperar infinito si falla
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        
        # El comando 'ping' fuerza una conexión real al servidor
        client.admin.command('ping')
        
        print("✅ ¡Conexión exitosa a MongoDB!")
        print(f"Bases de datos disponibles: {client.list_database_names()}")
        
    except ConnectionFailure:
        print("❌ Falló la conexión: El servidor MongoDB no responde.")
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    test_connection()