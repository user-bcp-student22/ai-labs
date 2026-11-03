# Hallazgos de Discovery

## api

### H-API-11 — La configuración acepta secretos JWT débiles
- Estado: Implementado — pendiente de revisión humana
- Evidencia: `api/app/config.py:34-35` rechaza claves de menos de 32 bytes UTF-8. `api/tests/test_config.py:13-41` verifica el límite, la clave exacta y el conteo UTF-8.
- Impacto: Una clave predecible podría permitir falsificar tokens si un atacante obtiene un JWT y logra adivinarla. El riesgo depende del valor configurado.
- Prioridad propuesta: Media.
- Contrato potencialmente afectado: Autenticación de endpoints protegidos mediante JWT.
- Cómo validarlo: `python tools/lab.py test api` — aprobado; 53 pruebas, 100% cobertura (gate mínimo 85%). El criterio de 32 bytes no estima entropía; revisar que las configuraciones de despliegue cumplan el mínimo antes de publicar.

### H-API-12 — La aceptación del token legacy no tiene una retirada verificable
- Estado: CANDIDATO
- Evidencia: `api/app/security.py:63-67` habilita el fallback cuando está configurado `WORKSHOP_LEGACY_TOKEN_SECRET`; `docs/ENDPOINTS.md:29` documenta que el formato sigue aceptándose durante la transición.
- Impacto: Mantener dos formatos de autenticación sin una fecha o mecanismo de retirada puede prolongar la compatibilidad con el formato antiguo y complicar la migración.
- Prioridad propuesta: Baja.
- Contrato potencialmente afectado: Formatos aceptados por el header `Authorization`.
- Cómo validarlo: Confirmar con responsables si la transición sigue vigente; probar el comportamiento con la variable definida y ausente, y acordar una condición verificable para retirar el formato legacy.

### H-API-13 — La respuesta de salud no limita el cuerpo recibido
- Estado: CANDIDATO
- Evidencia: `api/app/services/health.py:17` solicita la respuesta upstream y `api/app/services/health.py:24` decodifica el cuerpo completo. El timeout está limitado en `api/app/config.py:10`, pero no se observa un límite de tamaño.
- Impacto: Una respuesta inesperadamente grande del servicio configurado puede aumentar el consumo de memoria y el tamaño de la respuesta de la API.
- Prioridad propuesta: Media.
- Contrato potencialmente afectado: `GET /api/backend-health`, que devuelve un campo `body`.
- Cómo validarlo: Probar con un servicio upstream controlado que devuelva cuerpos de tamaño creciente y con solicitudes concurrentes; evaluar y acordar un límite compatible con el contrato.

### H-API-14 — Una conexión SQLite se comparte entre solicitudes sin sincronización explícita
- Estado: CANDIDATO
- Evidencia: `api/app/main.py:34` guarda una conexión en el estado de la aplicación; `api/app/db.py:24` desactiva la comprobación de hilo y `api/app/repository.py:31-32` ejecuta y confirma la escritura en operaciones separadas.
- Impacto: Bajo concurrencia, el uso simultáneo de la conexión podría causar errores o resultados inconsistentes; no se ha reproducido.
- Prioridad propuesta: Media.
- Contrato potencialmente afectado: `POST /api/tasks` y la persistencia de tareas.
- Cómo validarlo: Ejecutar solicitudes concurrentes de creación en una base aislada; comprobar códigos de respuesta, número de filas y consistencia, y registrar cualquier error SQLite.
