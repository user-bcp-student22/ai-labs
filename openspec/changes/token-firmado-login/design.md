# Design

Cambio: `token-firmado-login`. Fuente: Issue [#22](https://github.com/user-bcp-student22/ai-labs/issues/22) (HU-01, H-AUTH-03). Artefactos aprobados: [proposal.md](./proposal.md), [specs/auth-login/spec.md](./specs/auth-login/spec.md), [specs/auth-token/spec.md](./specs/auth-token/spec.md).

## Ampliación de alcance (decisión del usuario)

La propuesta excluía `api/`, pero el código lo acopla al token: [api/app/main.py](/C:/Users/Usuario/Documents/T14495-cesarvaldiviezo/ai-labs/api/app/main.py) (`legacy_identity`) decodifica el Bearer como Base64, valida el mismo secreto embebido y usa `username` como identidad en `/api/tasks`, `/api/tasks/summary`, `/api/requirements` y `/api/backend/health`. [web/src/app/dashboard/dashboard.component.ts](/C:/Users/Usuario/Documents/T14495-cesarvaldiviezo/ai-labs/web/src/app/dashboard/dashboard.component.ts) envía ese token tal como lo recibe. Sin un cambio en `api/`, cambiar `auth/` rompe el dashboard.

El usuario eligió **ampliar el alcance a `api/`** en este mismo cambio. `web/` no requiere cambios: solo guarda y reenvía el token sin decodificarlo. **Pendiente:** actualizar [proposal.md](./proposal.md) (sección Scope/Out of Scope e Impact) para incluir `api/` y `compose.yaml`; no se modificó en este paso.

## Contexto técnico

- `auth/` es Quarkus 3.27.4 (`quarkus-rest-jackson`, `quarkus-arc`, `quarkus-smallrye-health`, SQLite). `POST /auth/login` construye el token con `LegacyTokenUtil.create(username, role)`: Base64 de `username|role|expiry|WORKSHOP_SECRET_2026`. La respuesta fija `expiresIn` en `3600` dentro de `AuthResource`.
- `AuthResource` mezcla validación, acceso a datos y armado de respuesta. Las reglas de proyecto piden separar API, servicio, repositorio y seguridad.
- `application.properties` no declara ningún secreto; `quarkus.http.host` es `127.0.0.1` fuera de `%prod`.
- `api/` es FastAPI (`requirements.txt` sin librería JWT). Sus pruebas (`api/tests/test_api.py`) generan tokens legacy con el mismo secreto.
- `compose.yaml` no pasa variables de seguridad a `auth` ni a `api`. El contenedor de `auth` ejecuta `java -jar` sin `QUARKUS_PROFILE`, así que usa el perfil por defecto.
- `docs/ENDPOINTS.md` documenta el token legacy en la nota de seguridad de `POST /auth/login`.

## Goals

- Emitir un token firmado con `sub`, `client`, `iat` y `exp`, verificable con una clave externa (specs `auth-token`).
- Validar `client` contra una allowlist exacta y responder `400` si falta o no coincide (spec `auth-login`).
- Hacer que `expiresIn` y `exp` provengan de una sola fuente.
- Que `api/` verifique firma y vigencia, y tome la identidad de `sub`.
- Eliminar el secreto embebido de `auth/` y de `api/`.

## Non-goals

- No cambiar rutas, métodos, códigos HTTP ni la estructura JSON de `POST /auth/login`, `GET /q/health` ni los endpoints de `api/`.
- No cambiar la autorización de `api/` por `owner` (el parámetro `owner` sigue permitiendo consultar tareas de otro usuario); es un hallazgo distinto.
- No tratar H-AUTH-01 (SQL), H-AUTH-05 (CORS) ni la lógica de `LegacyDatabase`.
- No introducir refresh tokens, revocación ni almacenamiento de sesiones.
- No rediseñar `web/` ni la UI de login.

## Contratos protegidos

| Contrato | Quién depende | Cambia |
|---|---|---|
| `POST /auth/login`: ruta, request, 200/400/401/500, campos `token`, `expiresIn`, `user.*`, `debug` | `web/` y pruebas | No. Se añade `400` por `client` inválido (nuevo mensaje). |
| Valor de `token` | `web/` lo guarda; `api/` lo valida | Sí: pasa de Base64 a JWS firmado (formato interno, aprobado en la HU). |
| `GET /q/health` | `compose.yaml` (`AUTH_HEALTH_URL`) y `api/` | No. |
| `/api/*` con `Authorization: Bearer` | `web/` | Mismas rutas y códigos; cambia la validación del token (`401` para token legacy). |
| Campo `username` de identidad en `api/` | Respuestas de `api/` | No: se toma de `sub`. |

## Componentes afectados

- `auth/src/main/java/com/bcp/workshop/auth/`:
  - `LegacyTokenUtil` se reemplaza por un emisor de token (capa de seguridad).
  - Una capa de servicio de login valida `client` y coordina credenciales y emisión.
  - `AuthResource` queda como capa HTTP delgada.
  - `LoginRequest` conserva `client` (ya existe).
  - `LegacyDatabase`, `PasswordHasher`, `UserRecord`: sin cambios.
- `auth/src/main/resources/application.properties`: TTL, allowlist de `client` y secreto configurados.
- `auth/pom.xml`: librería JWT (ver decisión D2).
- `api/app/main.py`: reemplazar `legacy_identity` y eliminar `LEGACY_SECRET`.
- `api/tests/test_api.py`: helpers de token.
- `api/requirements.txt`: solo si se elige librería JWT en Python (ver D3; por defecto no cambia).
- `compose.yaml`: variable `AUTH_TOKEN_SECRET` para `auth` y `api`.
- `docs/ENDPOINTS.md`: nota de seguridad de `POST /auth/login` y de `api/`.
- `web/`: sin cambios.

## Decisiones técnicas y alternativas

**D1. Formato del token: JWS compacto HS256 (RFC 7519).**
- Elegido: `base64url(header).base64url(payload).base64url(HMAC-SHA256)`. Es estándar, lo verifica `api/` con la biblioteca estándar de Python (`hmac`, `hashlib`) sin dependencias nuevas, y lo produce `auth/` con una librería.
- Alternativa: formato propio firmado. Descartada: reinventa el formato y complica la interoperabilidad entre Java y Python.
- Alternativa: JWE o RS256. Descartada: el Issue pide clave simétrica externa; RS256 implicaría gestión de claves que no pidió la HU.

**D2. Librería de firma en `auth/`.**
- Elegido (propuesto): `quarkus-smallrye-jwt` / `smallrye-jwt-build` del BOM de Quarkus 3.27.4, para firmar y verificar HS256. Evita implementar criptografía a mano.
- Alternativa: `javax.crypto` del JDK. Sin dependencia nueva, pero obliga a escribir y mantener el parser y la verificación de JWS.
- Condición: antes de agregar la dependencia, revisar advisories y compatibilidad con 3.27.4 (requisito de la HU y de la spec `auth-token`).

**D3. Verificación en `api/`.**
- Elegido: verificación HS256 con biblioteca estándar (`hmac.compare_digest`, `base64.urlsafe_b64decode`) y validación de `exp` contra `time.time()`. Requiere `AUTH_TOKEN_SECRET` en el entorno.
- Alternativa: PyJWT. Válida, pero añade una dependencia y un cambio de `requirements.txt` solo para una verificación pequeña. Se elige la alternativa si la revisión de dependencias del equipo lo prefiere.
- `api/` valida `alg` (solo `HS256`), firma, `exp` y `sub` presente. Rechaza cualquier otro algoritmo, incluido `none`.

**D4. Fuente única de TTL.**
- Una propiedad `auth.token.ttl-seconds=3600`. `exp = iat + ttl` y `expiresIn = ttl`. Esto cumple la coherencia de la spec `auth-token` sin depender del reloj en dos sitios.
- Nota sobre la spec: la HU habla de `exp - now`. En la emisión, `iat` es `now`, por lo que `exp - iat` y `exp - now` coinciden dentro de la tolerancia de 2 s; la prueba usa `exp - iat`.

**D5. Allowlist de `client`.**
- Propiedad `auth.client.allowed=angular-workshop` (valor no secreto, puede tener default). Coincidencia exacta, sin distinguir mayúsculas por defecto.
- Un `client` ausente, vacío o no permitido responde `400` con un mensaje nuevo (`Client is not allowed`). Este mensaje no está en `docs/ENDPOINTS.md`; hay que documentarlo.

**D6. Clave de firma (`AUTH_TOKEN_SECRET`).**
- `auth`: `auth.token.secret=${AUTH_TOKEN_SECRET}` sin default en la configuración base. Si falta, Quarkus falla al arrancar, que es el comportamiento pedido fuera de laboratorio.
- Perfiles `%dev` y `%test` definen valores ficticios aislados solo para desarrollo y pruebas. Son la implementación del "perfil de laboratorio" que menciona la spec `auth-token`; ningún otro perfil (incluido el por defecto y `%prod`) recibe valor.
- `compose.yaml`: `AUTH_TOKEN_SECRET: ${AUTH_TOKEN_SECRET:?Defina AUTH_TOKEN_SECRET}` en `auth` y `api`. El contenedor no usa perfil de laboratorio, así que no hay fallback. No se escribe ningún valor en el repositorio.
- `api`: lee `AUTH_TOKEN_SECRET` en `create_app`. Si falta, la aplicación no arranca (mismo criterio que `auth`).
- Alternativa: fallback de laboratorio en compose. Descartada: vuelve a embebir un valor en el repositorio.

**D7. Claims y `role`.**
- El token lleva `sub`, `client`, `iat`, `exp`. No se incluye `role`: `api/` lo parsea pero no lo usa en ninguna respuesta, y la spec no lo exige.
- Riesgo: si una ruta futura necesita rol, deberá agregarse el claim. Queda como decisión registrada.

**D8. Separación en capas (auth).**
- `AuthResource` recibe la petición y traduce resultados a códigos HTTP.
- Un servicio de login valida `request`, `client` y credenciales (delegando en `LegacyDatabase`).
- Un emisor de token (`TokenIssuer`) recibe un `Clock` inyectable para que las pruebas de expiración no dependan del tiempo real.
- La validación de `client` vive en el servicio, no en el recurso.

**D9. Errores de verificación en `api/`.**
- Token ausente, mal formado, con firma inválida, alg no permitido, vencido o sin `sub`: `401` con `detail` genérico (sin revelar la causa ni el token). El detalle actual (`"Invalid token: " + str(error)`) se elimina para no exponer detalles de verificación.
- Esto cambia un detalle de mensaje en `api/`; los códigos se mantienen. Se documenta en `docs/ENDPOINTS.md`.

**D10. Logs.**
- `AuthResource` ya registra solo el mensaje del error. El servicio y el emisor no deben loguear el token, la clave ni la contraseña. Las pruebas comprueban la ausencia de estos valores en la salida.

## Estrategia incremental

Cada paso debe ser revisable y dejar el sistema funcionando.

1. **Caracterización de auth (sin cambios de comportamiento).** Agregar pruebas que fijen el contrato actual (ver sección siguiente). Deben pasar sin cambiar producción.
2. **Caracterización de api.** Agregar pruebas de `/api/tasks` con token legacy válido (200) e inválido (401), con el secreto actual. Pasan antes del cambio.
3. **Extracción sin cambio de formato.** Mover la emisión a `TokenIssuer` y el login a un servicio, manteniendo Base64 y las pruebas en verde.
4. **Nuevo emisor en `auth`.** Reemplazar Base64 por JWS HS256 con `sub`, `client`, `iat`, `exp`; leer la clave desde `AUTH_TOKEN_SECRET`; agregar la validación de `client` y el `400` nuevo. Las pruebas de token nuevo se escriben primero (rojo) y luego pasan.
5. **Verificación en `api`.** Agregar `verify_token` con HS256 y reemplazar `legacy_identity`. Actualizar los helpers de `test_api.py` para generar tokens firmados con un secreto de prueba.
6. **Configuración.** `compose.yaml` y `application.properties`: variable `AUTH_TOKEN_SECRET`; documentar en `README.md` cómo definirla.
7. **Documentación.** Actualizar `docs/ENDPOINTS.md` (nota de seguridad de login, `client` y `api/`).

Los pasos 4 y 5 cambian el formato del token; deben integrarse en la misma entrega, porque `web/` envía el token que `api/` valida.

## Pruebas de caracterización

Antes de tocar comportamiento crítico:

**auth** (`AuthResourceTest` y pruebas nuevas):
- Login válido: `200`, campos exactos `token`, `expiresIn` (3600), `user.username`, `user.displayName`, `user.role`, `debug`. Ya existe parcialmente (`logsInWithWorkshopUser`); completar las aserciones de estructura.
- `displayName` escapado en HTML4 (caracterización de `StringEscapeUtils`).
- `400` para request nulo, username y password vacíos o solo espacios; ya existen.
- `401` con credenciales incorrectas; ya existe.
- `500` sin detalles de excepción; ya existe (`hidesExceptionDetailsWhenDatabaseLookupFails`).
- Login sin `client` responde `200` **hoy**. Esta prueba se registra como caracterización y su resultado esperado cambia en el paso 4, de forma explícita.
- `GET /q/health`: ya existe.

**api** (`test_api.py`):
- Lista, creación, resumen y subida con token legacy válido: ya existen; se mantienen como baseline antes del paso 5.
- Token inválido: `401`; ya existe (`test_rejects_invalid_token`).

**Nuevas pruebas tras el cambio** (escritas primero en rojo):
- Token con `sub`, `client`, `iat`, `exp`; firma verificable con la clave de prueba.
- Token alterado y token vencido (usando `Clock` en auth y un `exp` pasado en api) son rechazados.
- `expiresIn` coincide con `exp - iat` dentro de 2 s.
- `client` válido/ausente/no permitido.
- La clave no aparece en logs ni en el código; el arranque falla sin `AUTH_TOKEN_SECRET` fuera de `%dev`/`%test` (prueba de configuración).
- `api` rechaza `alg` distinto de HS256 y tokens legacy Base64.

Las pruebas usan una base SQLite aislada (`AUTH_DB_URL` bajo `auth/target/`) y valores de clave ficticios. Cobertura del código modificado: 85% o más (JaCoCo en `auth/`; cobertura equivalente en `api/`, si la herramienta está configurada).

## Riesgos y trade-offs

- **Romper el dashboard si se despliega solo `auth`.** Mitigación: auth y api se publican en el mismo cambio; el paso 5 se integra con el 4.
- **Tokens legacy en `localStorage` del navegador.** Tras el despliegue, `api/` responderá `401` y el usuario debe volver a iniciar sesión. Trade-off aceptado para el taller; debe anunciarse.
- **Clave compartida entre `auth` y `api`.** Un secreto simétrico permite a `api` también emitir tokens. Es un trade-off de HS256; RS256 eliminaría esa exposición, pero queda fuera de alcance según la HU.
- **Arranque fallido sin variable.** `docker compose up` sin `AUTH_TOKEN_SECRET` se detiene con mensaje claro. Se documenta en `README.md`.
- **Dependencia nueva en `auth/`** (D2). Riesgo de advisories y de compatibilidad; requiere revisión antes de implementar.
- **Pérdida del claim `role`** (D7). Sin consumidores actuales.
- **Mensaje de `api/` en 401 más genérico** (D9). Pierde detalle para depuración; se compensa con logs del lado del servidor sin token.
- **Autorización por `owner` en `api/`** queda sin cambio; el token firmado identifica al usuario, pero no restringe el parámetro `owner`.

## Rollback

- Cada paso es un commit revisable. Revertir el paso 4 y el paso 5 juntos restaura el formato Base64 en ambos componentes; revertir solo uno deja el dashboard roto.
- `compose.yaml` y `application.properties`: revertir el paso 6 quita la variable obligatoria.
- No hay migración de datos: el token es efímero y no se persiste en SQLite ni en `api/`.
- Tras el rollback, los tokens firmados en `localStorage` dejan de ser aceptados por el formato legacy; el usuario vuelve a iniciar sesión.
- Si la dependencia JWT (D2) genera un problema, se revierte a `javax.crypto` sin cambiar la interfaz del token.
