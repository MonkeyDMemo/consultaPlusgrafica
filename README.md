# 🔍 Sistema de Consulta de Talento HR con Azure Functions

Sistema inteligente que permite realizar consultas en lenguaje natural sobre una base de datos de recursos humanos, generando respuestas detalladas y visualizaciones automáticas mediante Azure OpenAI y SQL Server.

## 🎯 Descripción General

Esta Azure Function convierte preguntas en español a consultas SQL, ejecuta las consultas contra una base de datos de empleados, genera respuestas en lenguaje natural y crea gráficos automáticos basados en los resultados.

### Flujo de Trabajo
1. **📝 Pregunta en lenguaje natural** → 
2. **🤖 Azure OpenAI genera SQL** → 
3. **💾 Ejecuta consulta en SQL Server** → 
4. **📊 Genera gráfico automático** → 
5. **💬 Respuesta en lenguaje natural**

## ✨ Características Principales

- **🗣️ Consultas en lenguaje natural**: Los usuarios pueden preguntar en español sin conocer SQL
- **🤖 Generación automática de SQL**: Usa GPT-4 para convertir preguntas a consultas SQL
- **📊 Visualización automática**: Genera gráficos relevantes basados en los datos
- **☁️ Almacenamiento en Azure Blob**: Los gráficos se guardan con URLs pre-firmadas
- **🔒 URLs temporales seguras**: Enlaces con expiración configurable (60 minutos por defecto)
- **📋 Respuestas formateadas**: Información estructurada y fácil de leer

## 🏗️ Arquitectura Técnica

### Componentes de Azure
- **Azure Functions**: Hosting de la aplicación serverless
- **Azure SQL Database**: Base de datos de empleados
- **Azure OpenAI Service**: Generación de consultas SQL y respuestas
- **Azure Blob Storage**: Almacenamiento de gráficos generados

### Base de Datos
- **Servidor**: `chatbotinventariosqlserver.database.windows.net`
- **Base de datos**: `Chabot_Inventario_Talento_SQLDB`
- **Tabla principal**: `HR_tabular_dev`

## 📋 Configuración

### Variables de Entorno Requeridas

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "...",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "OPENAI_API_KEY": "tu-api-key-de-openai",
    "STORAGE_CONNECTION_STRING": "tu-connection-string-de-storage"
  }
}
```

### Dependencias (`requirements.txt`)
```txt
azure-functions
requests
pyodbc
pandas
tabulate
matplotlib
azure-storage-blob
```

## 🔌 API Endpoint

### POST `/api/tu-endpoint-name`

**Request Body** (texto plano):
```
¿Quién es Juan Pérez?
```

**Response** (JSON):
```json
{
  "respuesta": "Juan Pérez es un Desarrollador Senior con ID: 12345...",
  "url_grafico": "https://storage.blob.core.windows.net/...",
  "url_presignada": "https://storage.blob.core.windows.net/...?sv=...",
  "query": "SELECT * FROM HR_tabular_dev WHERE nombre LIKE '%Juan Pérez%'"
}
```

## 💡 Ejemplos de Consultas Soportadas

### 👤 Consultas de Personas
- "¿Quién es María González?"
- "Muéstrame información de Juan Pérez"
- "Busca al empleado con ID 12345"

### 📊 Consultas Estadísticas
- "¿Cuántos empleados hay por país?"
- "¿Cuál es el promedio de tiempo en la empresa?"
- "Muestra los empleados con más certificaciones"

### 🔍 Consultas de Búsqueda
- "Empleados con habilidades en Python"
- "Lista de empleados ASIGNADOS"
- "Empleados ACTIVOS en México"

### 📈 Consultas Analíticas
- "¿Quién tiene más tiempo en la empresa?"
- "Top 10 empleados por experiencia"
- "Distribución de empleados por cargo"

## 📊 Tipos de Gráficos Generados

El sistema detecta automáticamente el tipo de gráfico más apropiado:

- **📊 Gráfico de barras horizontales**: Para categorías vs. valores numéricos
- **📈 Histograma**: Para distribución de valores numéricos
- **🔵 Gráfico de dispersión**: Para relación entre dos variables numéricas

## 🛠️ Detalles de Implementación

### Generación de SQL
- Usa coincidencias parciales con `LIKE` para nombres
- Maneja estados: ASIGNADO/DESASIGNADO, ACTIVO
- Incluye siempre `nombre` y `numero_identificador_unico_usuario` para consultas de personas
- Soporta agregaciones complejas con subconsultas

### Procesamiento de Datos
- Maneja valores nulos como "NO ESPECIFICADO"
- Formatea resultados usando `tabulate` para mejor legibilidad
- Valida consistencia entre columnas y datos

### Gestión de Archivos
- Nombres únicos con timestamp: `grafico_{timestamp}.png`
- URLs pre-firmadas con expiración de 60 minutos
- Creación automática del contenedor si no existe

## 🔒 Seguridad

- ⚠️ **Credenciales de base de datos**: Mover a Azure Key Vault en producción
- 🔐 URLs pre-firmadas con tokens SAS temporales
- 🛡️ Validación de entrada para prevenir inyección SQL
- 📝 Logging detallado para auditoría

## 🐛 Manejo de Errores

El sistema maneja múltiples tipos de errores:
- ❌ Error de generación de SQL
- ❌ Error de conexión a base de datos
- ❌ Datos no encontrados (404)
- ❌ Error de generación de gráficos
- ❌ Error de almacenamiento en blob

## 📈 Monitoreo y Logs

- Logging detallado en cada etapa del proceso
- Trazas completas de errores con `traceback`
- Mensajes de estado para debugging

## 🚀 Mejoras Recomendadas

1. **🔐 Seguridad**:
   - Migrar credenciales a Azure Key Vault
   - Implementar autenticación en el endpoint

2. **🎨 Visualizaciones**:
   - Agregar más tipos de gráficos
   - Personalización de colores y estilos

3. **🚄 Performance**:
   - Implementar caché de consultas frecuentes
   - Optimizar consultas SQL generadas

4. **📊 Funcionalidades**:
   - Exportar resultados a Excel
   - Generar reportes PDF
   - Consultas multi-tabla

## 📞 Soporte

Para problemas o sugerencias:
- 🐛 Revisa los logs en Azure Portal
- 📧 Contacta al equipo de desarrollo
- 📚 Consulta la documentación de Azure Functions

---

**⚡ Desarrollado para facilitar el acceso a información de recursos humanos mediante lenguaje natural**