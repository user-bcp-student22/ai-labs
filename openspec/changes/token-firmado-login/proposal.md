# Proposal

Fuente: GitHub Issue [#22](https://github.com/user-bcp-student22/ai-labs/issues/22), "HU-01 — Token firmado con expiración y claims mínimos". Hallazgo H-AUTH-03 (severidad alta). Componente: `auth/`.

## Why

El `token` que devuelve `POST /auth/login` se construye concatenando username, rol, expiración y un secreto fijo en [LegacyTokenUtil.java](/C:/Users/Usuario/Documents/T14495-cesarvaldiviezo/ai-labs/auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java), y luego lo codifica en Base64. Cualquiera que vea el token puede leer su contenido, modificarlo y volver a generarlo, porque no hay firma verificable y el secreto está en el código fuente. Además, `expiresIn: 3600` se devuelve sin que el servicio verifique la expiración. El cambio se necesita ahora porque es un hallazgo de severidad alta y bloquea que el token sea una credencial confiable.

El Issue también señala una discrepancia: la descripción de la HU afirma que ya se usa HMAC con `AUTH_TOKEN_SECRET`, pero el código actual no lo hace y `application.properties` no declara esa variable. Esta propuesta parte del código real, no de esa afirmación.

## What Changes

- El token de `POST /auth/login` deja de ser Base64 sin firma y pasa a ser un token firmado con los claims `sub`, `client`, `iat` y `exp`.
- `sub` identifica al usuario autenticado; `client` refleja el valor del request validado contra una allowlist.
- `expiresIn` debe coincidir con `exp - now` dentro de una tolerancia explícita.
- La clave de firma se lee de `AUTH_TOKEN_SECRET` o configuración externa equivalente. Se elimina el secreto embebido en el código.
- El campo `client`, que hoy se acepta pero se ignora, pasa a validarse.
- Los logs no deben contener tokens, secretos ni valores sensibles.
- **BREAKING** (solo para consumidores del token): quien decodifique el token como Base64 dejará de poder leerlo. El contrato HTTP de `POST /auth/login` no cambia.

Valores propuestos que deben confirmarse antes de implementar (la HU exige definirlos antes de cerrar criterios):

- Allowlist de `client`: `angular-workshop`. Un `client` ausente, vacío o fuera de la allowlist responde `400`.
- Tolerancia entre `expiresIn` y `exp - now`: 2 segundos.
- Política de `AUTH_TOKEN_SECRET`: fuera del perfil de laboratorio, el arranque falla si la variable falta; no hay valor por defecto. Solo el perfil de laboratorio puede usar un valor ficticio aislado.

## Capabilities

### New Capabilities

- `auth-login`: contrato observable de `POST /auth/login` que debe preservarse (rutas, request, códigos `200`, `400`, `401`, `500` y estructura de respuesta), incluyendo la validación del campo `client`.
- `auth-token`: emisión y verificación del token de sesión: claims requeridos, coherencia de `expiresIn`, rechazo de tokens alterados o vencidos, y manejo de la clave de firma sin embebido ni fallback fuera de laboratorio.

### Modified Capabilities

Ninguna. `openspec/specs/` no contiene capacidades previas.

## Preserved Behavior

Según [docs/ENDPOINTS.md](/C:/Users/Usuario/Documents/T14495-cesarvaldiviezo/ai-labs/docs/ENDPOINTS.md):

- Ruta y método `POST /auth/login`, con `Content-Type: application/json`.
- Request con `username` y `password` obligatorios; `client` opcional en el contrato actual, que este cambio pasa a validar (ver Decisiones pendientes).
- Códigos `200`, `400` (`Request is null`, `Username is required`, `Password is required`), `401` (`Invalid user <username> or password`) y `500` (`Internal server error`).
- Campos de la respuesta `200`: `token`, `expiresIn` (3600), `user.username`, `user.displayName`, `user.role` y `debug` (`authenticated-with-legacy-flow`).
- `GET /q/health` no cambia.

El formato interno de `token` sí puede cambiar, según la HU.

## Scope

- Token de `POST /auth/login` en `auth/`: firma, claims, verificación y expiración.
- Validación del campo `client`.
- Lectura de la clave de firma desde configuración externa.
- Verificación de firma, vigencia y `sub` en `api/` (`legacy_identity` reemplazado), y eliminación del secreto embebido en `api/`.
- Variable `AUTH_TOKEN_SECRET` en `compose.yaml` para `auth` y `api`.
- Pruebas de caracterización del login antes del cambio y pruebas de token alterado, vencido y claims.
- Actualización de la nota de seguridad de `POST /auth/login` y de `api/` en `docs/ENDPOINTS.md` durante la implementación.

## Out of Scope

- Cambios en `web/` (solo reenvía el token; no requiere cambios).
- Cambios en el formato JSON de la respuesta de login o en los códigos de estado.
- Consumidores externos del token (coordinación pendiente).
- Hallazgos H-AUTH-01 (SQL) y H-AUTH-05 (CORS), que tienen sus propias specs.
- Definición de orígenes o allowlists de producción fuera de `client`.
- Diseño técnico detallado (librería, algoritmo y estructura de clases): se decide en `design.md`.

## Decisiones pendientes

- Esquema de firma: HMAC propio frente a biblioteca JWT de Quarkus (SmallRye JWT). Debe decidirse antes de implementar y comprobar compatibilidad con Quarkus 3.27.4 y advisories.
- Confirmar allowlist de `client`, comportamiento cuando falta `client` (propuesta: `400`) y tolerancia de 2 segundos.
- Confirmar la política de `AUTH_TOKEN_SECRET` fuera de laboratorio.
- Ruta de la HU: el borrador existe en `HU-01.md` de la raíz; `auth/HU-01.md` no existe.

## Impact

- Código: `auth/src/main/java/com/bcp/workshop/auth/` (`LegacyTokenUtil`, `AuthResource`, `LoginRequest`) y `auth/src/main/resources/application.properties`.
- Código: `api/app/main.py` (`legacy_identity`) y `api/requirements.txt` solo si cambia la decisión D3.
- Pruebas: `auth/src/test/java/com/bcp/workshop/auth/` y `api/tests/test_api.py`.
- Infraestructura: `compose.yaml` (variable `AUTH_TOKEN_SECRET`) y `README.md`.
- Documentación: `docs/ENDPOINTS.md`.
- Dependencias: posible biblioteca JWT, solo si se decide frente a HMAC propio.
- Consumidores que lean el token como Base64.
