# Contratos de endpoints

Este documento se organiza por componente. Cada componente mantiene solo su sección; las secciones de `auth` y `web` se añaden en sus propios pasos y no se modifican desde `api`.

- [api](#api)

---

## api

API FastAPI de tareas y requerimientos (`api/app/main.py`, rutas en `api/app/routes/`). Todos los endpoints cuelgan del prefijo `/api`.

### Estado del contrato

| Tipo | Contenido |
|---|---|
| Contrato observado | Lo descrito en esta sección. Cada campo y cada ejemplo se comprobó ejecutando la API actual (`create_app`, `TestClient`) el 2026-11-02 y contra el código citado. |
| Contrato acordado | No existe un documento previo ni acuerdo registrado con `web` o `auth`. Hasta que exista, este contrato observado es la referencia. Ver [preguntas abiertas](#preguntas-abiertas-api). |
| Riesgos pendientes | H-API-01 y H-API-05 siguen en "Pendiente" en `api/prompts/HALLAZGOS.md`. Ver [riesgos pendientes](#riesgos-pendientes-api). |

### Convenciones comunes

**Autenticación.** Todos los endpoints exigen el header exacto:

```
Authorization: Bearer <token>
```

El token es un JWT HS256 firmado con `WORKSHOP_JWT_SECRET`. Se valida firma, expiración (`exp`), emisor (`iss` = `workshop-auth`), audiencia (`aud` = `workshop-api`) y la presencia de `sub` y `role` (`api/app/security.py:14-19`, `:36-45`). La identidad del llamante es `sub` (usuario) y `role` (rol). Durante la transición, si el servidor define `WORKSHOP_LEGACY_TOKEN_SECRET`, también acepta el formato legacy Base64 `usuario|rol|exp|secreto` (`api/app/security.py:48-69`). Ese formato es transitorio y no debe usarse en integraciones nuevas.

**Errores comunes a todos los endpoints.**

| Código | Cuándo ocurre | Cuerpo |
|---|---|---|
| 401 | Falta el header, el token es inválido, está expirado, tiene firma, `iss` o `aud` incorrectos, o le falta un claim requerido. | `{"detail": "Invalid token"}` |
| 422 | El request no cumple el esquema (campo ausente, tipo o valor no permitido). Formato estándar de FastAPI: lista en `detail` con `type`, `loc`, `msg`, `input` y, a veces, `ctx`. | Ver cada endpoint. |

El mensaje del 401 es siempre el mismo; el motivo real solo queda en el log del servidor (`api/app/security.py:72-78`).

**Formato de fechas.** `createdAt` es texto `YYYY-MM-DD HH:MM:SS` generado por SQLite con `datetime('now')` (UTC, sin zona horaria ni `T`) (`api/app/repository.py:7`).

**CORS.** Los orígenes permitidos se configuran con `WORKSHOP_CORS_ORIGINS` (lista separada por comas; por defecto `http://localhost:4200`). Sin credenciales (`allow_credentials=False`). Headers permitidos: `Authorization` y `Content-Type` (`api/app/main.py:36-42`, `api/app/config.py:9`, `:25-26`, `:37`). Para el origen por defecto, la respuesta de preflight incluye `access-control-allow-origin: http://localhost:4200` y no incluye `access-control-allow-credentials`.

---

### GET /api/tasks

**1. Qué hace.** Lista las tareas del usuario autenticado, ordenadas por `id`.

**2. Autenticación.** Obligatoria: `Authorization: Bearer <token>`.

**3. Request.**

| Campo / parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `owner` (query) | string | No | Propietario cuyas tareas se piden. Si se omite o está vacío, se usa el usuario del token. Si coincide con el usuario del token, se acepta. Si es otro usuario, solo se acepta cuando el rol del token es `TRAINER`; en cualquier otro caso responde 403. |

Ejemplo (rol `STUDENT`, usuario `student`):

```http
GET /api/tasks HTTP/1.1
Authorization: Bearer <JWT con sub=student, role=STUDENT>
```

Ejemplo de un `TRAINER` leyendo las tareas de otro usuario:

```http
GET /api/tasks?owner=student HTTP/1.1
Authorization: Bearer <JWT con sub=trainer, role=TRAINER>
```

**4. Respuesta exitosa.** `200 OK`, arreglo JSON de tareas (vacío si el propietario no tiene tareas).

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Identificador de la tarea, autoincremental. |
| `title` | string | Título. |
| `description` | string | Descripción. |
| `status` | string | Uno de `TODO`, `IN_PROGRESS`, `DONE`, `ARCHIVED` para tareas creadas por la API. |
| `owner` | string | Usuario propietario de la tarea. |
| `priority` | string | Uno de `LOW`, `MEDIUM`, `HIGH` para tareas creadas por la API. |
| `createdAt` | string | Fecha de creación `YYYY-MM-DD HH:MM:SS` (UTC). |

```json
[
  {
    "id": 1,
    "title": "Refactor login",
    "description": "Separar responsabilidades en frontend",
    "status": "TODO",
    "owner": "student",
    "priority": "HIGH",
    "createdAt": "2026-11-02 22:27:19"
  },
  {
    "id": 2,
    "title": "Review API",
    "description": "Revisar seguridad de endpoints",
    "status": "IN_PROGRESS",
    "owner": "student",
    "priority": "MEDIUM",
    "createdAt": "2026-11-02 22:27:19"
  }
]
```

**5. Errores.**

| Código | Cuándo ocurre | Cuerpo de ejemplo |
|---|---|---|
| 401 | Token ausente o inválido. | `{"detail": "Invalid token"}` |
| 403 | `owner` es distinto del usuario del token y el rol no es `TRAINER`. | `{"detail": "Forbidden"}` |

**6. Notas de seguridad.**
- La autorización depende de la identidad del token, no del parámetro `owner`: un `STUDENT` que envía `owner=trainer` recibe 403 (`api/app/services/tasks.py:18-27`).
- Solo `TRAINER` puede leer tareas de otro usuario; es lectura, no escritura.
- La consulta SQL está parametrizada (`api/app/repository.py:4`, `:10-11`).

---

### POST /api/tasks

**1. Qué hace.** Crea una tarea a nombre del usuario autenticado.

**2. Autenticación.** Obligatoria: `Authorization: Bearer <token>`.

**3. Request.** Cuerpo JSON (`Content-Type: application/json`), modelo `TaskCreate` (`api/app/schemas.py:14-21`).

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `title` | string | No (por defecto `""`) | Título, máximo 255 caracteres. Un número se convierte a texto. |
| `description` | string | No (por defecto `""`) | Descripción, máximo 2000 caracteres. Un número se convierte a texto. |
| `status` | string | No (por defecto `TODO`) | Uno de `TODO`, `IN_PROGRESS`, `DONE`, `ARCHIVED`. |
| `priority` | string | No (por defecto `MEDIUM`) | Uno de `LOW`, `MEDIUM`, `HIGH`. |
| `owner` | string | No | Si se envía, debe coincidir con el usuario del token; de lo contrario responde 403. Si se omite, se usa el usuario del token. |

Los campos desconocidos en el cuerpo se ignoran (no hay `extra="forbid"` en el modelo).

Ejemplo:

```http
POST /api/tasks HTTP/1.1
Authorization: Bearer <JWT con sub=student, role=STUDENT>
Content-Type: application/json

{
  "title": "Add tests",
  "description": "Improve coverage",
  "status": "TODO",
  "priority": "HIGH"
}
```

**4. Respuesta exitosa.** `201 Created`, la tarea creada (mismos campos que en `GET /api/tasks`).

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Identificador asignado. |
| `title` | string | Título guardado. |
| `description` | string | Descripción guardada. |
| `status` | string | Estado guardado. |
| `owner` | string | Siempre el usuario del token. |
| `priority` | string | Prioridad guardada. |
| `createdAt` | string | Fecha de creación `YYYY-MM-DD HH:MM:SS` (UTC). |

```json
{
  "id": 4,
  "title": "Add tests",
  "description": "Improve coverage",
  "status": "TODO",
  "owner": "student",
  "priority": "HIGH",
  "createdAt": "2026-11-02 22:27:19"
}
```

**5. Errores.**

| Código | Cuándo ocurre | Cuerpo de ejemplo |
|---|---|---|
| 401 | Token ausente o inválido. | `{"detail": "Invalid token"}` |
| 403 | `owner` distinto del usuario del token. Aplica también a `TRAINER`. | `{"detail": "Forbidden"}` |
| 422 | `status` o `priority` fuera de la lista. | `{"detail":[{"type":"literal_error","loc":["body","status"],"msg":"Input should be 'TODO', 'IN_PROGRESS', 'DONE' or 'ARCHIVED'","input":"FOO","ctx":{"expected":"'TODO', 'IN_PROGRESS', 'DONE' or 'ARCHIVED'"}}]}` |
| 422 | `title` de más de 255 caracteres (igual para `description` de más de 2000, con `loc` `["body","description"]`). | `{"detail":[{"type":"string_too_long","loc":["body","title"],"msg":"String should have at most 255 characters","input":"aaaa…","ctx":{"max_length":255}}]}` |
| 422 | El cuerpo no es un objeto JSON (por ejemplo `[]`). | `{"detail":[{"type":"model_attributes_type","loc":["body"],"msg":"Input should be a valid dictionary or object to extract fields from","input":[]}]}` |

**6. Notas de seguridad.**
- El propietario siempre se toma del token; `owner` en el cuerpo solo se acepta si coincide (`api/app/services/tasks.py:18-21`, `:47-56`). Un `TRAINER` tampoco puede escribir a nombre de otro usuario.
- `status` y `priority` se validan contra listas cerradas y la inserción usa SQL parametrizado (`api/app/repository.py:7`, `:22-33`).

---

### GET /api/summary

**1. Qué hace.** Devuelve el resumen de tareas de un usuario: total, conteo por estado y cuántas tareas de prioridad alta siguen abiertas.

**2. Autenticación.** Obligatoria: `Authorization: Bearer <token>`.

**3. Request.**

| Campo / parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `owner` (query) | string | No | Mismas reglas que en `GET /api/tasks`: por defecto el usuario del token; otro usuario solo para rol `TRAINER`. |

Ejemplo:

```http
GET /api/summary HTTP/1.1
Authorization: Bearer <JWT con sub=student, role=STUDENT>
```

**4. Respuesta exitosa.** `200 OK`.

| Campo | Tipo | Descripción |
|---|---|---|
| `owner` | string | Usuario al que corresponde el resumen. |
| `total` | integer | Número de tareas del usuario. |
| `byStatus` | objeto (string → integer) | Conteo por valor de `status`. Solo aparecen los estados con al menos una tarea. |
| `highPriorityOpen` | integer | Tareas con `priority` = `HIGH` y `status` distinto de `DONE` y `ARCHIVED`. |

```json
{
  "owner": "student",
  "total": 4,
  "byStatus": { "TODO": 3, "IN_PROGRESS": 1 },
  "highPriorityOpen": 2
}
```

**5. Errores.**

| Código | Cuándo ocurre | Cuerpo de ejemplo |
|---|---|---|
| 401 | Token ausente o inválido. | `{"detail": "Invalid token"}` |
| 403 | `owner` distinto del usuario del token y rol distinto de `TRAINER`. | `{"detail": "Forbidden"}` |

**6. Notas de seguridad.**
- Igual que `GET /api/tasks`: el resumen de otro usuario solo se entrega a `TRAINER` (`api/app/services/tasks.py:24-27`, `:59-61`); un `STUDENT` recibe 403.
- Consulta SQL parametrizada (`api/app/repository.py:6`, `:18-19`).

---

### POST /api/requirements

**1. Qué hace.** Recibe un archivo de requerimientos (`.txt`, `.md` o `.pdf`) y lo guarda en el servidor a nombre del usuario autenticado.

**2. Autenticación.** Obligatoria: `Authorization: Bearer <token>`.

**3. Request.** `multipart/form-data` con una parte de archivo.

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `file` | archivo | Sí | Archivo a subir. Tamaño máximo 5 MiB (5 242 880 bytes). Extensión permitida: `.txt`, `.md`, `.pdf` (sin distinguir mayúsculas). |

Reglas sobre el nombre (`api/app/files.py:13-29`): se toma solo el nombre base (se descarta cualquier ruta), los caracteres fuera de `A-Za-z0-9._-` se reemplazan por `_`, se quitan los puntos iniciales, y se rechaza si queda vacío, supera 120 caracteres, la extensión no está permitida o el nombre sin extensión es reservado de Windows (`CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`). No se valida el `Content-Type` del archivo ni su contenido.

Ejemplo:

```http
POST /api/requirements HTTP/1.1
Authorization: Bearer <JWT con sub=student, role=STUDENT>
Content-Type: multipart/form-data; boundary=----b

------b
Content-Disposition: form-data; name="file"; filename="requirements.txt"
Content-Type: text/plain

Login must be accessible
------b--
```

**4. Respuesta exitosa.** `201 Created`.

| Campo | Tipo | Descripción |
|---|---|---|
| `owner` | string | Usuario del token que subió el archivo. |
| `fileName` | string | Nombre sanitizado del archivo (el que se aceptó, sin prefijo). |
| `storedAt` | string | Ruta en el servidor donde quedó guardado; el nombre en disco lleva un prefijo aleatorio (UUID hexadecimal) más `-` y `fileName`. |
| `size` | integer | Tamaño en bytes. |

```json
{
  "owner": "student",
  "fileName": "requirements.txt",
  "storedAt": "<WORKSHOP_UPLOAD_DIR>/fba8b9e03c064c6c99aad09eb540d3ff-requirements.txt",
  "size": 24
}
```

`storedAt` varía por petición y por servidor (en Windows usa `\`); el ejemplo sustituye la ruta real por `<WORKSHOP_UPLOAD_DIR>`.

**5. Errores.**

| Código | Cuándo ocurre | Cuerpo de ejemplo |
|---|---|---|
| 400 | Nombre vacío tras sanitizar, de más de 120 caracteres, con extensión no permitida (por ejemplo `a.exe`) o nombre reservado (por ejemplo `CON.txt`). | `{"detail": "Invalid file name or extension"}` |
| 401 | Token ausente o inválido. | `{"detail": "Invalid token"}` |
| 413 | El archivo supera 5 MiB. | `{"detail": "File too large"}` |
| 422 | Falta la parte `file`. | `{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input":null}]}` |

**6. Notas de seguridad.**
- El nombre enviado no controla dónde se guarda: un nombre como `../../x.md` se reduce a `x.md` y se guarda con prefijo UUID dentro del directorio de cargas, así que no hay recorrido de rutas ni sobrescritura entre cargas con el mismo nombre (`api/app/files.py:13-16`, `api/app/services/requirements.py:9-12`).
- La lectura se limita a 5 MiB + 1 byte para no cargar archivos grandes en memoria (`api/app/routes/requirements.py:22-24`).
- `owner` en la respuesta viene del token; el cliente no puede elegirlo.
- `storedAt` expone la ruta del servidor al cliente.

---

### GET /api/backend-health

**1. Qué hace.** Consulta el estado del servicio de autenticación en nombre del usuario y devuelve lo que ese servicio responde, o un aviso de que no está disponible.

**2. Autenticación.** Obligatoria: `Authorization: Bearer <token>`.

**3. Request.** Sin parámetros ni cuerpo. La URL consultada la define el servidor con `AUTH_HEALTH_URL` (por defecto `http://localhost:8080/q/health`) y el cliente no puede cambiarla (`api/app/config.py:8`, `:36`).

Ejemplo:

```http
GET /api/backend-health HTTP/1.1
Authorization: Bearer <JWT con sub=student, role=STUDENT>
```

**4. Respuesta exitosa.** `200 OK`, también cuando el servicio de autenticación no responde.

| Campo | Tipo | Descripción |
|---|---|---|
| `requestedBy` | string | Usuario del token. |
| `status` | integer | Código HTTP devuelto por el servicio de autenticación, o `0` si no se pudo conectar. |
| `body` | string | Cuerpo devuelto por el servicio de autenticación (texto UTF-8), o `auth backend unavailable` si no se pudo conectar. |

Con el servicio de autenticación disponible (valores ilustrativos: `status` y `body` son los que devuelva ese servicio; este ejemplo no se capturó contra un servicio real):

```json
{ "requestedBy": "student", "status": 200, "body": "UP" }
```

Con el servicio no disponible:

```json
{ "requestedBy": "student", "status": 0, "body": "auth backend unavailable" }
```

**5. Errores.**

| Código | Cuándo ocurre | Cuerpo de ejemplo |
|---|---|---|
| 401 | Token ausente o inválido. | `{"detail": "Invalid token"}` |

La indisponibilidad del servicio de autenticación no genera error HTTP: se informa con `status: 0` en un `200`.

**6. Notas de seguridad.**
- Cuando falla la conexión no se reenvía el texto de la excepción; solo `auth backend unavailable`, y el detalle se registra en el log del servidor (`api/app/services/health.py:15-20`).
- La petición al servicio de autenticación tiene un tiempo máximo de 3 segundos y la URL no es controlable por el cliente.
- En éxito se reenvía el cuerpo del servicio de autenticación tal cual, sin límite de tamaño.

---

## Riesgos pendientes (api)

| ID | Riesgo | Efecto en el contrato |
|---|---|---|
| H-API-01 | Con `WORKSHOP_LEGACY_TOKEN_SECRET` definido, la API acepta el token Base64 legacy sin firma JWT. | Dejará de aceptarse cuando se retire el formato legacy; los clientes deben migrar a JWT con `iss` y `aud` indicados. |
| H-API-05 | La versión mínima exigida de `urllib3` (>= 2.6.0) es inferior a la que corrige los advisories CVE-2026-44431/44432 (2.7.0). | Sin efecto en los endpoints. |
| — | `WORKSHOP_JWT_SECRET` es obligatorio y no tiene longitud mínima validada (`api/app/config.py:30-32`). | Sin él, la API no arranca. |

## Preguntas abiertas (api)

1. ¿Qué componente emite los JWT y con qué `iss` y `aud` finales? El código exige `workshop-auth` y `workshop-api`, pero no hay acuerdo documentado con `auth`.
2. ¿`web` depende del texto del `detail` del 401 (`Invalid token`), del origen CORS `http://localhost:4200` o del cuerpo de `backend-health`? No se leyó código de `web` para confirmarlo.
3. ¿Se acepta que `POST /api/tasks` aplique valores por defecto (`""`, `TODO`, `MEDIUM`) cuando faltan campos, incluso un cuerpo vacío `{}`? Hoy responde 201.
4. ¿Debe `storedAt` exponer la ruta del servidor al cliente?
5. ¿Debe `GET /api/backend-health` devolver un código distinto de 200 cuando el servicio de autenticación no está disponible o responde con error? Hoy siempre devuelve 200.
6. ¿Qué respuesta se espera en caso de errores 5xx? El código no define un formato propio para ellos.
7. ¿Un `TRAINER` que consulta con `owner` de un usuario inexistente debe recibir `[]` (hoy) o 404?
