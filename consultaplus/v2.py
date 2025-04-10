import azure.functions as func
import requests
import os
import pyodbc
import pandas as pd
import traceback
from tabulate import tabulate
import json
import matplotlib.pyplot as plt
import time
import logging
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from io import BytesIO
from datetime import datetime, timedelta  # Added datetime imports for the presigned URL function


# Configuración de conexión SQL Server
server = 'chatbotinventariosqlserver.database.windows.net'
database = 'Chabot_Inventario_Talento_SQLDB'
username = 'ghadmin@chatbotinventariosqlserver'
password = 'wm5VrRK=jX/hE?-'
tabla = 'HR_tabular_dev'

# Configuración de Azure OpenAI
AZURE_OPENAI_ENDPOINT = "https://chabot-inventario-talento-aistudio.openai.azure.com/"
AZURE_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEPLOYMENT_NAME = "gpt-4o-mini"
API_VERSION = "2024-02-15-preview"

# Configuración de Blob Storage
CONTAINER_NAME = "consultaplus-container"
# En producción, obtener de variables de entorno
AZURE_STORAGE_CONNECTION_STRING = os.getenv("STORAGE_CONNECTION_STRING")

# Cargar variables de entorno
#load_dotenv()
#openai.api_key = os.getenv("OPENAI_API_KEY")

# Función para llamar a Azure OpenAI
def call_azure_openai(messages):
    try:
        api_url = f"{AZURE_OPENAI_ENDPOINT}openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={API_VERSION}"

        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_API_KEY
        }

        data = {
            "messages": messages,
            "max_tokens": 500  # Ajusta según sea necesario
        }

        response = requests.post(api_url, headers=headers, json=data)

        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
        else:
            print("Error en la solicitud:", response.status_code, response.text)
            return None

    except Exception as e:
        print(traceback.format_exc())
        return None

def subir_a_blob_storage(nombre_archivo, contenido):
    """
    Sube un archivo al Azure Blob Storage.
    
    Args:
        nombre_archivo: Nombre con el que se guardará el archivo en el blob
        contenido: Objeto tipo BytesIO con el contenido del archivo
        
    Returns:
        str: URL del archivo subido o None si hay error
    """
    try:
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        
        # Verificar si el contenedor existe, y crearlo si no existe
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        try:
            container_properties = container_client.get_container_properties()
        except Exception as e:
            if "ContainerNotFound" in str(e):
                logging.info(f"Creando contenedor {CONTAINER_NAME} porque no existe")
                container_client.create_container()
            else:
                raise
                
        blob_client = container_client.get_blob_client(nombre_archivo)
        
        contenido.seek(0)
        blob_client.upload_blob(contenido, overwrite=True)
        
        # Esperar un poco para asegurarse de que el blob esté disponible
        # antes de intentar generar la URL presignada
        time.sleep(1)
        
        # Usar la función para generar una URL presignada en lugar de una URL directa
        url_presignada = generar_url_presignada(nombre_archivo)
        
        if not url_presignada:
            # Si falla la generación de URL presignada, crear una URL directa como respaldo
            connection_parts = AZURE_STORAGE_CONNECTION_STRING.split(';')
            account_name = None
            for part in connection_parts:
                if part.startswith('AccountName='):
                    account_name = part.split('=', 1)[1]
                    break
                    
            if account_name:
                return f"https://{account_name}.blob.core.windows.net/{CONTAINER_NAME}/{nombre_archivo}"
            else:
                return None
                
        return url_presignada
    except Exception as e:
        logging.error(f"Error al subir archivo a Blob Storage: {str(e)}")
        traceback.print_exc()
        return None

def generar_url_presignada(nombre_archivo, expiracion_minutos=60):
    """
    Genera una URL presignada para un blob que expira después de un tiempo determinado.
    
    Args:
        nombre_archivo: Nombre del archivo en el blob storage
        expiracion_minutos: Tiempo en minutos antes de que expire la URL (default: 60)
        
    Returns:
        str: URL presignada o None si hay error
    """
    try:
        # Primero verificamos si el blob existe
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        
        # Verifica si el contenedor existe
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        if not container_client.exists():
            logging.error(f"El contenedor {CONTAINER_NAME} no existe")
            return None
            
        # Verifica si el blob existe
        blob_client = container_client.get_blob_client(nombre_archivo)
        try:
            blob_client.get_blob_properties()
        except Exception as e:
            if "ResourceNotFound" in str(e):
                logging.error(f"El archivo {nombre_archivo} no existe en el contenedor {CONTAINER_NAME}")
                return None
            else:
                raise
        
        # Extraer la clave de la cuenta del connection string
        connection_parts = AZURE_STORAGE_CONNECTION_STRING.split(';')
        account_name = None
        account_key = None
        
        for part in connection_parts:
            if part.startswith('AccountName='):
                account_name = part.split('=', 1)[1]
            elif part.startswith('AccountKey='):
                account_key = part.split('=', 1)[1]
        
        if not account_name or not account_key:
            raise ValueError("No se pudo extraer el nombre de cuenta o la clave de cuenta del connection string")
            
        # Generar el token SAS
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=CONTAINER_NAME,
            blob_name=nombre_archivo,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(minutes=expiracion_minutos)
        )

        return f"https://{account_name}.blob.core.windows.net/{CONTAINER_NAME}/{nombre_archivo}?{sas_token}"
    except Exception as e:
        logging.error(f"Error generando URL pre-firmada: {e}")
        logging.error(traceback.format_exc())
        return None

# Obtener conexión a la base de datos
def get_db_connection():
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"Encrypt=yes;"
            f"TrustServerCertificate=no;"
            f"Connection Timeout=30;"
        )
        return conn
    except Exception as e:
        print(traceback.format_exc())
        return None

def execute_query(query, params=()):
    try:
        conn = get_db_connection()
        if not conn:
            return None, None
        cur = conn.cursor()
        cur.execute(query, params)

        columns = [column[0] for column in cur.description]
        rows = cur.fetchall()

        # Convertimos cada fila a tupla normal
        results = [tuple(row) for row in rows]

        cur.close()
        conn.close()

        return columns, results if results else (columns, [])

    except Exception as e:
        print("ERROR EN execute_query:")
        print(traceback.format_exc())
        return None, None

    
# Obtener columnas de la tabla HR_tabular
def get_table_columns():
    try:
        query = """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'HR_tabular_dev'
        """
        columns = execute_query(query)
        return columns if columns else None
    except Exception as e:
        print(traceback.format_exc())
        return None

# Generar consulta SQL
def generate_sql_query(question):
    try:
        columns = get_table_columns()
        if not columns:
            return None, None
        prompt = (
        f"Eres un experto en SQL que usa SQL Server. Convierte la pregunta en SQL usando la tabla 'Chabot_Inventario_Talento.{tabla}' y sus columnas {columns}. "
        f"Si la pregunta comienza con 'quien es', 'quién es' o similar seguido de un nombre, asegúrate de incluir las columnas 'nombre' y 'numero_identificador_unico_usuario' y las demas columnas en el SELECT. para el resumen "
        #f"IMPORTANTE: Siempre incluye las columnas 'nombre' y 'numero_identificador_unico_usuario' en el SELECT, independientemente de lo que se pregunte. "        
        f"No uses otras tablas ni caracteres de formato adicionales como backticks. "
        f"Si la consulta es acerca de el asigancion o desasignado las dos opciones es ASIGNADO y DESASIGNADO."
        f"Si la consulta es acerca del estad o estus del empleado solo hay ACTIVO en la tabla eso quiere decir que estan trabajando."
        f"Si la consulta es sobre un nombre, usa LIKE para permitir coincidencias parciales. "
        f"Si la consulta es sobre un habilidades tecnicas usa LIKE para permitir coincidencias parciales. "
        f"Si la consulta es sobre PAIS usa LIKE para permitir coincidencias parciales. "
        f"Si la consulta es por número de empleado (ID_usuario), busca exacto. "
        f"Si el nombre no se encuentra, devuelve un mensaje indicando que el usuario puede intentar de nuevo o usar el número de empleado. "
        f"Si la consulta implica funciones de agregación como MAX, asegúrate de usar una subconsulta o incluir todas las columnas necesarias en GROUP BY. "
        f"Si buscas el empleado con más tiempo en la empresa (fecha_contratacion), usa una subconsulta para obtener el empleado con el valor máximo en time_company. "
        f"Pregunta: {question}\nSQL Query:"
                )
        messages = [
            {"role": "system", "content": f"Devuelve solo la consulta SQL usando la tabla Chabot_Inventario_Talento.{tabla}."},
            {"role": "user", "content": prompt}
        ]

        sql_query = call_azure_openai(messages)

        if sql_query:
            return prompt, sql_query.replace("```sql", "").replace("```", "").strip()
        else:
            return None, None

    except Exception as e:
        print(traceback.format_exc())
        return None, None

# Generar respuesta basada en los resultados
def generate_response(question, results):
    try:
        columns, rows = results
        print("Columnas:", columns)
        print("Primera fila:", rows[0] if rows else "No hay filas")
        if not rows:
            print("No hay datos disponibles para responder.")
            return "No hay datos disponibles para responder."
        
        try:
            if rows and len(columns) != len(rows[0]):
                print(f"Inconsistencia detectada: columnas={len(columns)}, valores por fila={len(rows[0])}")
                return func.HttpResponse(json.dumps({'error': 'Inconsistencia entre columnas y datos'}), status_code=500, mimetype='application/json')

            if len(columns) != len(rows[0]):
                print(f"Inconsistencia detectada: {len(columns)} columnas vs {len(rows[0])} valores en la fila.")
                return "Error: La cantidad de columnas no coincide con los datos obtenidos."
            
            df = pd.DataFrame.from_records(rows, columns=columns)
            print("DataFrame generado:")
            #print(df)
            
            formatted_results = tabulate(df, headers='keys', tablefmt='grid')
            summary = f"Información detallada del usuario:\n{formatted_results}"
        except Exception as e:
            print(f"Error al procesar los resultados en DataFrame: {e}")
            formatted_results = "No se pudo formatear los resultados."
            summary = "Error procesando los datos."
        
        print(f"Datos obtenidos para la respuesta:\n{formatted_results}")
        prompt = (
            f"Pregunta: {question}\n\n"
            f"Datos obtenidos:\n{formatted_results}\n\n"
            f"Si la pregunta comienza con 'quien es', 'quién es', 'quien fue', 'quién fue' o cualquier variación similar seguida de un nombre, asegúrate de incluir siempre el nombre completo y el numero_identificador_unico_usuario en tu respuesta ademas del resumen de las demas columnas."
            #f"Siempre incluye el nombre completo y el numero_identificador_unico_usuario en tu respuesta, incluso si no se pregunta explícitamente por estos datos."
            #f"Formato de respuesta: 'Nombre: [nombre_completo], ID: [numero_identificador_unico_usuario]', seguido de la información solicitada."
            f"En caso de que venga vacio escribirlo como tal que esta vacio."
            #f"En caso de que la pregunta sea sobre un nombre, cargo, país, habilidades principales o certificaciones más relevantes, responde con el valor correspondiente."
            f"Si solo es una columna y el nombre de la columna es algo como 'total' solo responde en base a ese dato y no agregues algo mas."
            f"Si la columna está vacía, escribe 'no especificados' en lugar de dejarlo vacío y asumir que es el total.\n"
            f"Genera un resumen conciso del usuario con base en los datos proporcionados, resaltando aspectos clave como su nombre, cargo, país, habilidades principales y certificaciones más relevantes En caso de que no sea necesario no respondas con esto."
            f"Da un resumen unicamente en base a los datos proporcionados."
            f"Si es posible da el resultado en una solo Linea cuando convenga."
        )
        
        messages = [
            {"role": "system", "content": "Analiza la información y genera un resumen estructurado y explicativo."},
            {"role": "user", "content": prompt}
        ]

        return call_azure_openai(messages)

    except Exception as e:
        print(traceback.format_exc())
        return "Error procesando los datos."
    
def generar_grafico_auto(df, pregunta):
    try:
        if df.empty:
            print("No hay datos para graficar.")
            return None, None  # (contenido, nombre)

        num_cols = df.select_dtypes(include='number').columns
        cat_cols = df.select_dtypes(include='object').columns

        for col in cat_cols:
            df[col] = df[col].fillna("NO ESPECIFICADO")

        plt.figure(figsize=(10, 6))

        if len(num_cols) == 1 and len(cat_cols) == 1:
            df_sorted = df.sort_values(by=num_cols[0], ascending=True)
            plt.barh(df_sorted[cat_cols[0]], df_sorted[num_cols[0]])

            for index, value in enumerate(df_sorted[num_cols[0]]):
                plt.text(value + 5, index, str(value), va='center')

            plt.xlabel(num_cols[0])
            plt.ylabel(cat_cols[0])
            plt.title(f"{num_cols[0]} por {cat_cols[0]}")

        elif len(num_cols) == 1:
            df[num_cols[0]].hist()
            plt.title(f'Histograma de {num_cols[0]}')
            plt.xlabel(num_cols[0])
            plt.ylabel('Frecuencia')

        elif len(num_cols) >= 2:
            df.plot(kind='scatter', x=num_cols[0], y=num_cols[1])
            plt.title(f'Relación entre {num_cols[0]} y {num_cols[1]}')
            plt.xlabel(num_cols[0])
            plt.ylabel(num_cols[1])

        else:
            print("No se pudo determinar un gráfico adecuado.")
            return None, None

        plt.suptitle(f'Pregunta: \"{pregunta}\"', fontsize=10)
        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()

        # Nombre de archivo con timestamp
        nombre_archivo = f"grafico_{int(time.time())}.png"

        return buffer, nombre_archivo

    except Exception as e:
        print(traceback.format_exc())
        print(f"Error al generar gráfico: {e}")
        return None
        

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        question = req.get_body().decode('utf-8').strip()
        if not question:
            return func.HttpResponse(json.dumps({'error': 'Faltan parámetros'}), status_code=400, mimetype='application/json')
        
        # Paso 1: Generar consulta
        prompt, sql_query = generate_sql_query(question)
        if not sql_query:
            return func.HttpResponse(json.dumps({'error': 'No se pudo generar la consulta SQL', 'prompt': prompt, 'query': sql_query}), status_code=500, mimetype='application/json')
        
        print(sql_query)
        
        # Paso 2: Ejecutar la consulta
        results = execute_query(sql_query)
        if results is None:
            return func.HttpResponse(json.dumps({'error': 'Error ejecutando la consulta SQL', 'prompt': prompt, 'query': sql_query}), status_code=500, mimetype='application/json')
        
        columns, rows = results
        if not rows:
            return func.HttpResponse(json.dumps({'error': 'No hay datos disponibles'}), status_code=404, mimetype='application/json')
        
        df = pd.DataFrame(rows, columns=columns)

        # Paso 3: Generar gráfico
        output_path = f'output/grafico_{int(time.time())}.png'
        # Generar el gráfico
        buffer, nombre_archivo = generar_grafico_auto(df, question)
        url_grafico = None
        url_presignada = None

        if buffer and nombre_archivo:
            # Subir el gráfico a Blob Storage
            url_respuesta = subir_a_blob_storage(nombre_archivo, buffer)
            
            if url_respuesta:
                url_grafico = url_respuesta
                # Generar URL presignada por separado
                url_presignada = generar_url_presignada(nombre_archivo)

        # Paso 4: Generar respuesta textual
        response_text = generate_response(question, results)

        # Paso 5: Construir respuesta final
        return func.HttpResponse(
            json.dumps({
                'respuesta': response_text,
                'url_grafico': url_grafico if url_grafico else 'No se pudo generar o subir el gráfico',
                'url_presignada': url_presignada if url_presignada else 'No se pudo generar la URL presignada',
                'query': sql_query
            }, ensure_ascii=False),
            mimetype='application/json'
        )

    except Exception as e:
        print(traceback.format_exc())
        return func.HttpResponse(json.dumps({'error': 'Error interno del servidor'}), status_code=500, mimetype='application/json')