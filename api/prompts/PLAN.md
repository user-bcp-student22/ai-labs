# Plan de corrección

## api

### Alcance y fuentes

- Hallazgos: H-API-01 a H-API-10. Todos aparecen como `Aprobado` en `api/prompts/HALLAZGOS.md`. Ese archivo está en `api/prompts/`, no en la raíz que indica el ámbito; no lo moví. Confirma la ubicación. Mientras tanto, la matriz de seguimiento sigue siendo esa.
- Este plan no cambia el estado de ningún hallazgo. Las filas siguen `Aprobado` hasta que haya cambios y pruebas.
- Base de contrato: `HEAD` (`e52bc26`) y el comportamiento observado en `HALLAZGOS.md`. `docs/ENDPOINTS.md` no existe, así que no hay contrato acordado formal. Todo cambio de status, campo o formato visible requiere aprobación explícita (ver "Decisiones pendientes").
- El árbol de trabajo ya tiene correcciones sin commit (`api/app/files.py`, `api/app/repository.py`, `resolve_owner`, mensaje 401 genérico, `requirements.txt`). Este plan las toma como punto de partida candidato. Ninguna está verificada con pruebas registradas.

### Contrato a preservar (observado)

- `GET /api/tasks`: query `owner` opcional; lista ordenada por id; claves `id, title, description, status, owner, priority, createdAt`.
- `POST /api/tasks`: 201; defaults `status=TODO`, `priority=MEDIUM`, `owner=identidad`; devuelve la tarea creada.
- `GET /api/summary`: `owner, total, byStatus, highPriorityOpen`.
- `POST /api/requirements`: 201 con `owner, fileName, storedAt, size`.
- `GET /api/backend-health`: 200 con `requestedBy, status, body`; `status=0` si auth no responde.
- Errores observados: 401 para token inválido o ausente (el `detail` cambia, ver H-API-06); 403 cuando el owner no es el de la identidad (ya en el árbol de trabajo); 400 y 413 en carga (árbol de trabajo).

### Orden de ejecución

1. Caracterización base: correr `python -m pytest` con cwd `api/` antes de tocar nada. Resultado: pendiente (no ejecutado).
2. H-API-05 (dependencias): cambio aislado en `requirements.txt`.
3. H-API-07 (capas): mover código sin cambiar comportamiento. Debe ir antes de los cambios de lógica para reducir conflictos.
4. H-API-03 y H-API-09 (SQL parametrizado, schemas Pydantic, funciones pequeñas).
5. H-API-02 (autorización por identidad).
6. H-API-01 (verificación real de token). Depende de la decisión de formato con auth.
7. H-API-04 (carga segura de archivos).
8. H-API-06 (errores genéricos).
9. H-API-08 (CORS).
10. H-API-10 (backend-health).

Cada paso termina con la suite completa en verde antes del siguiente.

### Estructura objetivo (propuesta)

- `app/main.py`: solo compone `create_app`. Conserva `create_app(db_path, upload_dir)` y el símbolo `app` (ambos usados por `tests/support.py` y el arranque).
- `app/config.py`: lectura de variables de entorno con nombre y valor por defecto explícitos. Sin secretos en código.
- `app/db.py`: conexión, esquema y datos de ejemplo.
- `app/repository.py`: consultas parametrizadas (ya existe en el árbol de trabajo).
- `app/schemas.py`: modelos Pydantic de entrada y salida.
- `app/security.py`: verificación del token y dependencia de identidad.
- `app/services/tasks.py`: resolución de owner y creación/consulta de tareas.
- `app/services/summary.py`: cálculo del resumen como función pura.
- `app/files.py`: normalización del nombre y validación de extensión (ya existe).
- `app/routes/tasks.py`, `app/routes/requirements.py`, `app/routes/health.py`: solo HTTP.

Reglas de Clean Code de `AGENTS.md` que aplican a todo el plan: una responsabilidad por función, sin duplicación (por ejemplo, la lista de columnas SELECT y el seed), sin anidamiento profundo (guard clauses), y sin números o cadenas mágicas (constantes con nombre como `UPSTREAM_TIMEOUT_SECONDS`, `MAX_UPLOAD_BYTES`).

### H-API-01 — Token Base64 con secreto embebido

- **Problema:** `LEGACY_SECRET` está en código (`api/app/main.py:14` en HEAD, `:23` en el árbol de trabajo). El token es Base64 sin firma: cualquiera que lea el repositorio puede forjar `usuario|rol|exp|secreto`. Solo se valida la expiración.
- **Cambio propuesto:** verificación real de JWT HS256. Clave desde `WORKSHOP_JWT_SECRET` sin valor por defecto; si falta, la app no arranca. Validar firma, `exp`, `iss`, `aud`, y los claims `sub` (usuario) y `role`. Algoritmo fijado a `HS256` en la verificación. Sin tolerancia de reloj (constante explícita).
- **Dependencia nueva:** `PyJWT`. Justificación: maneja verificación de firma, `exp`, `iss` y `aud` y fija el algoritmo, que es donde los errores manuales son más frecuentes. Alternativa sin dependencia: `hmac` + `base64` de la biblioteca estándar (unas 30 líneas más propensas a error). Requiere aprobación.
- **Archivos:** `app/security.py` (nuevo), `app/config.py` (nuevo), `app/main.py` (quitar `LEGACY_SECRET` y el parseo), `requirements.txt` (pin de PyJWT), `tests/support.py` (generar token de prueba), `tests/test_api.py` (su helper `token()` hardcodea el secreto; debe usar el helper común).
- **Dependencia de coordinación:** el token lo emite `auth/`, fuera del ámbito de `api/`. Cambiar el formato rompe el contrato entre ambos servicios. Hay que elegir: (a) aceptar ambos formatos durante una transición, o (b) corte coordinado con auth. No se cambia nada en `auth/` desde este plan.
- **Caracterización antes de tocar:** conservar `test_char_missing_authorization_is_401`, `test_char_wrong_secret_is_401`, `test_char_expired_token_is_401`, `test_char_malformed_token_is_401` (`tests/test_characterization.py`). Agregar `test_char_token_identity_drives_response` (usuario del token aparece en `requestedBy`/`owner`). Escribir `test_fix_h_api_01_unsigned_token_is_401` (token Base64 con el secreto conocido debe dar 401 tras el cambio). Ese caso no se caracteriza como comportamiento deseado porque hoy devuelve 200.

### H-API-02 — Autorización: el cliente elige el owner

- **Problema:** `owner` de query o body reemplaza la identidad (`api/app/main.py:69`, `:83`, `:92` en HEAD). En el árbol de trabajo, `resolve_owner` ya devuelve 403 para otro owner (`api/app/main.py:45-48`).
- **Cambio propuesto:** una función `owner_for_request(identity, requested)` en `services/tasks.py`: si no hay owner o coincide con la identidad, devuelve la identidad; en otro caso, 403. Se aplica a `GET /api/tasks`, `GET /api/summary` y `POST /api/tasks`. Por defecto no hay excepciones por rol.
- **Archivos:** `services/tasks.py` (nuevo), `routes/tasks.py` (incluye `GET /api/summary`), `tests/test_corrections.py` (ya tiene `test_fix_h_api_02_*`).
- **Caracterización antes de tocar:** `test_char_list_tasks_with_own_owner_query` y `test_char_create_task_keeps_explicit_fields` (owner igual a la identidad). Agregar `test_char_list_without_owner_returns_identity_tasks`. No se caracteriza que otro owner funcione en HEAD, porque es la vulnerabilidad.
- **Decisión pendiente:** si el rol `TRAINER` debe poder leer otros owners. Por defecto, no.

### H-API-03 — SQL con concatenación

- **Problema:** filtros, inserts y lookup por id se arman con concatenación (`api/app/main.py:70`, `:84`, `:87`, `:93` en HEAD). Las comillas simples rompen el insert.
- **Cambio propuesto:** usar solo `repository.py` con placeholders `?` (ya está en el árbol de trabajo). El `INSERT` deja de ser SQL armado y el lookup por `lastrowid` usa `find_task_by_id`. Los campos del insert llegan ya validados por el modelo de H-API-09.
- **Archivos:** `repository.py`, `services/tasks.py`, `routes/tasks.py`.
- **Caracterización antes de tocar:** `test_char_create_task_applies_defaults` y `test_char_create_task_keeps_explicit_fields`. Escribir `test_fix_h_api_03_quoted_title_is_stored_literally` (ya en `test_corrections.py`), que usa un título con comilla simple como caso normal. No se usan payloads de explotación.

### H-API-09 — Calidad: `dict` crudo, excepciones amplias, anidamiento, duplicación

- **Problema:** `create_task` recibe `dict[str, Any]` y convierte cualquier valor con `str()` (`api/app/main.py:78-84` en HEAD). `summary` tiene tres niveles de `if` (`:103-105`). Los SELECT y los INSERT del seed se repiten (`:40-42`, `:70`, `:87`). `except Exception` es amplio (`:25`, `:120`). `on_event` está deprecado (`:123`).
- **Cambio propuesto:**
  - `schemas.py`: `TaskCreate` (campos con tipos y `max_length`), `TaskOut`, `SummaryOut`, `UploadOut`, `HealthOut`. `response_model` en las rutas.
  - `services/summary.py`: `build_summary(rows, owner)` como función pura, sin anidamiento.
  - Seed como tupla constante y un solo `executemany`.
  - Excepciones capturadas en el sitio exacto (`ValueError` o `jwt.PyJWTError` en `security.py`; `urllib3.exceptions.HTTPError` en salud).
  - `lifespan` en lugar de `on_event`.
- **Archivos:** `schemas.py`, `services/summary.py`, `db.py`, `main.py`.
- **Caracterización antes de tocar:** `test_char_summary_counts_identity_tasks` (JSON exacto), `test_char_list_tasks_returns_identity_tasks_in_order`. Agregar pruebas unitarias de `build_summary` con los casos HIGH abierto, HIGH DONE y HIGH ARCHIVED.
- **Decisión pendiente:** `status` y `priority` como texto libre (contrato actual) o enumeraciones (`TODO`, `IN_PROGRESS`, `DONE`, `ARCHIVED`; `LOW`, `MEDIUM`, `HIGH`). Enumerar cambia el comportamiento: hoy se aceptan valores arbitrarios. Recomendación: enumerar y documentarlo como cambio aprobado.
- **Decisión pendiente:** con Pydantic, un número en el body devuelve 422, mientras que hoy se convierte a texto. Aceptar el cambio o usar `coerce_numbers_to_str`.

### H-API-07 — Arquitectura: todo en `create_app`

- **Problema:** rutas, SQL, reglas y serialización están en una función de unas 100 líneas (`api/app/main.py:29-129` en HEAD).
- **Cambio propuesto:** separación en las capas de "Estructura objetivo", sin cambio de comportamiento. Primero se mueve código; luego, en pasos aparte, se aplican H-API-01 a H-API-10.
- **Archivos:** todos los de la estructura objetivo.
- **Caracterización antes de tocar:** toda la suite actual (`tests/test_api.py`, `tests/test_characterization.py`) debe pasar sin editar sus casos. Ese es el criterio de aceptación de este paso.

### H-API-04 — Carga de archivos

- **Problema:** `file.filename` se une a `WORKSHOP_UPLOAD_DIR` sin normalizar (`api/app/main.py:109-111` en HEAD). Un nombre con ruta escapa del directorio. No hay límite de extensión ni de tamaño. En el árbol de trabajo, `safe_file_name` y `has_allowed_extension` cubren nombre y extensión (`api/app/files.py:9-16`) y el límite de 5 MB (`api/app/main.py:126-131`). Un nombre repetido sobrescribe el archivo (`api/app/main.py:133`).
- **Cambio propuesto:**
  - Mantener `safe_file_name`. Agregar la lista de nombres reservados de Windows (`CON`, `NUL`, etc.) y una longitud máxima (constante).
  - Verificar que la ruta resuelta quede dentro de `upload_dir` antes de escribir (defensa en profundidad).
  - Evitar sobrescritura: ver decisión pendiente.
- **Archivos:** `files.py`, `services/requirements.py` (nuevo), `routes/requirements.py`.
- **Caracterización antes de tocar:** `test_char_upload_returns_stable_shape` (claves exactas y `fileName`). Las pruebas `test_fix_h_api_04_*` de `test_corrections.py` cubren nombre, extensión y tamaño.
- **Decisión pendiente:** si un nombre repetido devuelve 409 (conserva `fileName` y `storedAt`, pero cambia el 201 actual) o se guarda con nombre único (conserva `fileName` y cambia `storedAt`). Recomendación: nombre único, y documentar el cambio en `storedAt`.

### H-API-05 — SCA: urllib3 y python-multipart

- **Problema:** `api/requirements.txt:4-5` en HEAD fija `urllib3==2.5.0` y `python-multipart==0.0.21`. `backend-health` usa urllib3 y la carga multipart usa python-multipart.
- **Cambio propuesto:** versiones corregidas en `requirements.txt`. En el árbol de trabajo ya están `urllib3==2.8.0` y `python-multipart==0.0.33`. Confirmar compatibilidad con `fastapi==0.128.2` y ejecutar la suite. No agregar herramientas nuevas al repositorio; `pip-audit` se corre una vez fuera de él.
- **Archivos:** `requirements.txt`.
- **Caracterización antes de tocar:** la suite completa en verde antes y después del cambio. `test_fix_h_api_05_pins_patched_versions` fija `>= 2.6.0` y `>= 0.0.22`.
- **Pendiente externo:** IDs de CVE y versiones corregidas no verificados (sin advisories ni `pip-audit` ejecutado).

### H-API-06 — Errores: detalle interno en 401

- **Problema:** el 401 concatena `str(error)` (`api/app/main.py:25-26` en HEAD).
- **Cambio propuesto:** `detail` fijo `"Invalid token"` (constante); el tipo de excepción se registra en el log del servidor. El árbol de trabajo ya hace esto (`api/app/main.py:40-42`).
- **Archivos:** `security.py`.
- **Caracterización antes de tocar:** las pruebas de estado 401 existentes (sin depender del texto del detalle). `test_fix_h_api_06_401_detail_is_generic` y `test_fix_h_api_06_error_detail_goes_to_server_log` ya existen.
- **Nota de compatibilidad:** el texto del `detail` cambia de `"Invalid token: ..."` a `"Invalid token"`. Si el frontend lee ese texto, hay que coordinarlo; no se verifica desde `api/`.

### H-API-08 — CORS con `*` y credenciales

- **Problema:** `allow_origins=["*"]` con `allow_credentials=True` (`api/app/main.py:50-51` en HEAD; `:72-73` en el árbol de trabajo).
- **Cambio propuesto:** orígenes desde `WORKSHOP_CORS_ORIGINS` (lista separada por comas). `allow_credentials=False`, porque la autenticación va por header y no por cookie. `allow_headers` explícito con `Authorization` y `Content-Type`.
- **Archivos:** `config.py`, `main.py`.
- **Caracterización antes de tocar:** preflight `OPTIONS /api/tasks` desde un origen permitido responde 200 con `Access-Control-Allow-Origin`. Escribir `test_fix_h_api_08_unknown_origin_is_not_allowed` (origen no listado no se refleja).
- **Decisiones pendientes:**
  - Valor por defecto de orígenes (propuesta: `http://localhost:4200`, según README). Hay que confirmarlo con el frontend.
  - Confirmar con el frontend que no depende de cookies ni credenciales.

### H-API-10 — `backend-health` reenvía el cuerpo de auth

- **Problema:** `body` devuelve la respuesta completa del servicio auth y `str(error)` (`api/app/main.py:118-121` en HEAD; `:139-144` en el árbol de trabajo). El timeout `3.0` es un número mágico.
- **Cambio propuesto:** `AUTH_HEALTH_URL` y el timeout desde `config.py` (constante `UPSTREAM_TIMEOUT_SECONDS = 3.0`). Capturar `urllib3.exceptions.HTTPError`, no `Exception`. El cuerpo en error se reemplaza por un texto genérico. El detalle queda en el log.
- **Archivos:** `routes/health.py`, `config.py`.
- **Caracterización antes de tocar:** `test_char_backend_health_shape_when_auth_is_down` (claves exactas, `status=0`, `body` string). Ese test sigue siendo válido después del cambio.
- **Decisión pendiente:** si el frontend muestra el `body` de auth. Si lo muestra, la respuesta exitosa debe seguir incluyéndolo y solo se corrige el error.

### Decisiones pendientes (requieren aprobación humana antes de codificar)

1. H-API-01: PyJWT (recomendado) o biblioteca estándar.
2. H-API-01: transición de formato de token con `auth/` (aceptar ambos formatos, o corte coordinado). Valores de `iss` y `aud` (propuesta: `workshop-auth` y `workshop-api`).
3. H-API-02: si `TRAINER` puede leer otros owners. Por defecto, no.
4. H-API-09: `status` y `priority` como enumeración o texto libre; comportamiento con números en el body.
5. H-API-04: nombre repetido: 409 o nombre único.
6. H-API-08: orígenes por defecto y confirmación con el frontend.
7. H-API-10: contenido del `body` cuando auth responde.
8. Variable nueva `WORKSHOP_JWT_SECRET`: debe declararse en el despliegue, fuera de `api/`. Requiere coordinación; este plan no edita esos archivos.

### Pendientes de evidencia

- Ejecución baseline de `python -m pytest` con cwd `api/`: no ejecutada.
- Ejecución de `python tools/lab.py test api` desde la raíz: no ejecutada. Requiere `setup api` previo.
- Advisories y CVE de urllib3 y python-multipart: no verificados.
- Compatibilidad real del formato de token con `auth/`: no verificada, porque `auth/` está fuera del ámbito.
- Frontend (`web/`): no leído. Las decisiones de CORS, `detail` y `body` dependen de su comportamiento real.
- `docs/ENDPOINTS.md` y `docs/TESTING.md`: no existen. Se crean en pasos posteriores si se piden.

### Registro de ejecución (componente api, IDs H-API-01 a H-API-10)

- Aprobación humana: confirmada con `approve_plan=true`. Decisiones elegidas: PyJWT 2.15.1, transición de token, enumeraciones para `status` y `priority`, nombre único en carga, origen CORS `http://localhost:4200`, body de health conservado en éxito y `trainer_can_read_others=true` (ver desviaciones).
- Caracterización antes de cambios (14 pruebas en `tests/test_characterization.py`): pasa en el árbol de trabajo y en `HEAD` (copia temporal, ya eliminada).
- Corrección antes de cambios: en `HEAD`, 19 de 20 pruebas de `tests/test_corrections.py` (sin las de H-API-01) fallan; solo pasa la lectura de otro owner por TRAINER. En el árbol de trabajo, 8 fallan (H-API-02 lectura de TRAINER; H-API-04 nombre único y reservado; H-API-08 origen y credenciales; H-API-09 `status` y `priority`; H-API-10 texto de error).
- Después de H-API-07 (capas, sin cambio de comportamiento): las 26 caracterizaciones siguen pasando; las mismas 8 pruebas de corrección siguen fallando.
- Después de H-API-03 y H-API-09: pasan las pruebas de SQL y de enumeraciones; se agregan `tests/test_summary.py` (2 pruebas).
- Después de H-API-02, H-API-04, H-API-08, H-API-10 y H-API-01: todas las pruebas de corrección pasan.
- Resultado final: `python tools/lab.py test api` (cwd raíz, que ejecuta pruebas en `api/`): 49 pruebas pasan, cobertura 100 % de `app/` (umbral 85 % cumplido), código de salida 0.
- Estado de hallazgos en `api/prompts/HALLAZGOS.md`: Resuelto para H-API-02, 03, 04, 06, 07, 08, 09, 10; Parcial para H-API-01 y H-API-05.

### Desviaciones del plan

1. H-API-02: `trainer_can_read_others=true` (el plan recomendaba `false`). Se implementó solo lectura: `TRAINER` puede leer `GET /api/tasks` y `GET /api/summary` de otros owners; escribir sigue ligado a la identidad.
2. H-API-01: la transición deja activo el formato legacy mientras `WORKSHOP_LEGACY_TOKEN_SECRET` esté definido. Ese valor ya no está en código, pero el formato legacy sigue siendo válido con ese secreto. Por eso el hallazgo queda Parcial hasta el corte con `auth/`.
3. H-API-01: `WORKSHOP_JWT_SECRET` es obligatorio; sin él la app no arranca (`api/app/config.py`). Cualquier despliegue (por ejemplo `compose.yaml`, fuera de `api/`) debe declararlo; no se editó.
4. H-API-04: se usa nombre único en el almacenamiento y se mantiene `fileName`. Eso cambia `storedAt`. Se actualizaron tres aserciones de ruta en `tests/test_api.py`, `tests/test_characterization.py` y `tests/test_corrections.py`; el contrato HTTP no cambió. No se agregó la comprobación de contención de ruta: el nombre sanitizado no contiene separadores.
5. H-API-03/09: `TaskCreate` agrega límites de longitud (título 255, descripción 2000) que el plan pedía con `max_length`, pero que no estaban en el contrato observado. Requiere confirmación.
6. H-API-09: los números en el body se convierten a texto (`coerce_numbers_to_str`), como en el comportamiento observado.
7. Pruebas de identidad de token: `tests/support.py` firma tokens JWT con claves de prueba de al menos 32 bytes y el secreto legacy se toma del entorno de `tests/conftest.py`.
8. Caracterizaciones nuevas (`test_char_backend_health_forwards_upstream_body_on_success`, `test_char_token_identity_drives_response`) se agregaron al final, después del cambio; no se ejecutaron contra `HEAD` porque el helper ahora usa el secreto del entorno.

### Pendientes

- Verificar CVE, IDs y versiones corregidas de urllib3 y python-multipart con advisories o `pip-audit`. No se ejecutó.
- Coordinar con `auth/` el formato de token (JWT con `iss` `workshop-auth` y `aud` `workshop-api`, y la variable `WORKSHOP_LEGACY_TOKEN_SECRET`).
- Coordinar con `web/`: texto del `detail` del 401 (ahora `Invalid token`), origen CORS y body de `backend-health`.
- Declarar `WORKSHOP_JWT_SECRET` en el despliegue antes de arrancar la API.
- `docs/ENDPOINTS.md` y `docs/TESTING.md`: no creados; corresponden a pasos de documentación posteriores.