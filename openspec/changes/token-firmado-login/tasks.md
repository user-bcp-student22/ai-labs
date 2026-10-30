# Tasks

Fuente: Issue [#22](https://github.com/user-bcp-student22/ai-labs/issues/22) (HU-01, H-AUTH-03). Artefactos: [proposal.md](./proposal.md), [specs/auth-login/spec.md](./specs/auth-login/spec.md), [specs/auth-token/spec.md](./specs/auth-token/spec.md), [design.md](./design.md).

Decisiones confirmadas: librería SmallRye JWT en `auth/`; verificación HS256 con biblioteca estándar en `api/`; `client` ausente o vacío responde `400`; `proposal.md` se actualiza para incluir `api/` y `compose.yaml`. Tolerancia de `expiresIn` frente a `exp - iat`: 2 s (valor de `design.md`, no respondido explícitamente).

Comandos desde la raíz: `python tools/lab.py test auth` y `python tools/lab.py test api`. Evidencias generales en la raíz con ID `H-AUTH-03`.

## 1. Alineación de alcance y baseline

- [x] 1.1 Actualizar [proposal.md](./proposal.md) para incluir `api/` y `compose.yaml` en Scope e Impact, quitar `api/` de Out of Scope, y verificar con `openspec validate token-firmado-login --strict`.
- [x] 1.2 Ejecutar `python tools/lab.py test auth` y `python tools/lab.py test api` sin cambios de código, y registrar en la evidencia general de la raíz (`H-AUTH-03`) comando, directorio, código de salida y resultado.

## 2. Caracterización de auth (antes de cualquier cambio)

- [x] 2.1 Completar en `AuthResourceTest.logsInWithWorkshopUser` las aserciones de estructura exacta: campos `token`, `expiresIn` (3600), `user.username`, `user.displayName`, `user.role` y `debug` con valor `authenticated-with-legacy-flow`; verificar que la prueba pasa sobre el código actual.
- [x] 2.2 Agregar prueba de `displayName` escapado en HTML4 para un usuario con caracteres especiales en la base aislada; verificar que pasa sobre el código actual.
- [x] 2.3 Agregar prueba que caracteriza el login sin `client` como `200` (estado actual, documentado como cambiante en 5.5); verificar que pasa sobre el código actual.
- [x] 2.4 Confirmar que las pruebas existentes de health, `400` (request nulo, username y password vacíos o con solo espacios), `401` y `500` pasan; verificar con `python tools/lab.py test auth`.

## 3. Caracterización de api (antes de cualquier cambio)

- [x] 3.1 Agregar prueba en `api/tests/test_api.py` que `GET /api/tasks` con token legacy válido responde `200` y usa el usuario del token como owner por defecto; verificar con `python tools/lab.py test api`.
- [x] 3.2 Agregar prueba que un token legacy con expiración pasada responde `401`; verificar con `python tools/lab.py test api`.
- [x] 3.3 Confirmar que la suite de `api/` queda en verde antes del cambio, incluido `test_rejects_invalid_token`; verificar con `python tools/lab.py test api`.

## 4. Refactor sin cambio de comportamiento en auth

- [x] 4.1 Extraer la validación de request y credenciales de `AuthResource` a un servicio de login, manteniendo el token Base64 actual; verificar que las pruebas de los grupos 2.x siguen en verde con `python tools/lab.py test auth`.
- [x] 4.2 Extraer la emisión del token a `TokenIssuer` con `Clock` inyectable, sin cambiar el formato; verificar que las pruebas de los grupos 2.x siguen en verde con `python tools/lab.py test auth`.

## 5. Token firmado y client en auth

- [x] 5.1 Agregar la dependencia SmallRye JWT en `auth/pom.xml` gestionada por el BOM de Quarkus 3.27.4, tras revisar advisories y registrar el resultado; verificar que Maven resuelve dependencias con `python tools/lab.py test auth`.
- [x] 5.2 Escribir en rojo las pruebas de `auth-token`: claims `sub`, `client`, `iat` y `exp`; firma verificable con clave de prueba; token alterado rechazado; token vencido rechazado con `Clock`; `expiresIn` igual a `exp - iat` dentro de 2 s; la salida de logs no contiene token, clave ni contraseña. Verificar que fallan antes de implementar.
- [x] 5.3 Escribir en rojo las pruebas de `auth-login` para `client`: válido `angular-workshop` responde `200`; no permitido o ausente, vacío o solo espacios responde `400` sin token. Verificar que fallan antes de implementar.
- [x] 5.4 Agregar en `application.properties` `auth.token.ttl-seconds=3600`, `auth.client.allowed=angular-workshop` y `auth.token.secret=${AUTH_TOKEN_SECRET}` sin valor por defecto; definir valores ficticios solo en `%dev` y `%test`. Verificar con `python tools/lab.py test auth`.
- [x] 5.5 Implementar el emisor HS256 que firma con la clave configurada, reemplazar `LegacyTokenUtil` y derivar `expiresIn` y `exp` del mismo TTL; verificar que 5.2 pasa.
- [x] 5.6 Implementar la validación de `client` contra la allowlist exacta en el servicio de login, con mensaje `Client is not allowed` y sin emitir token; actualizar la caracterización 2.3 al nuevo resultado `400`; verificar que 5.3 pasa.
- [ ] 5.7 Agregar prueba de configuración que confirma que el arranque falla sin `AUTH_TOKEN_SECRET` fuera de `%dev` y `%test`; verificar con `python tools/lab.py test auth`.
- [ ] 5.8 Agregar `AUTH_TOKEN_SECRET` en `compose.yaml` para el servicio `auth` con sintaxis `${AUTH_TOKEN_SECRET:?...}` y documentar en [README.md](../../../README.md) cómo definirla localmente y en compose, sin valores reales; verificar con `docker compose config` (si Docker está disponible; si no, registrar que no se ejecutó) y ejecutar los comandos del README tal como están escritos.
- [ ] 5.9 Actualizar en [docs/ENDPOINTS.md](../../../docs/ENDPOINTS.md) la sección de `POST /auth/login`: formato del token, validación de `client` con `400`, `expiresIn` y nota de seguridad; verificar que cada escenario de `specs/auth-login` y `specs/auth-token` tiene su correspondencia en el documento.
- [ ] 5.10 Verificar cobertura JaCoCo del código modificado de `auth/` igual o superior a 85% con `python tools/lab.py test auth`.

## 6. Verificación de token en api

- [ ] 6.1 Escribir en rojo las pruebas de `api/`: token HS256 válido con `sub` responde `200`; firma alterada, `alg` distinto de HS256 (incluido `none`), token vencido, token legacy Base64 y token sin `sub` responden `401` con `detail` genérico; verificar que fallan antes de implementar.
- [ ] 6.2 Implementar `verify_token` con biblioteca estándar (`hmac.compare_digest`, `base64.urlsafe_b64decode`) que valida alg, firma, `exp` y `sub`, y lee `AUTH_TOKEN_SECRET` en `create_app`, fallando al arrancar si falta; verificar que 6.1 pasa con `python tools/lab.py test api`.
- [ ] 6.3 Reemplazar `legacy_identity` por la verificación nueva, eliminar `LEGACY_SECRET` y el detalle de error interno; actualizar los helpers de `api/tests/test_api.py` para generar tokens firmados con clave de prueba; verificar que 3.1 y 3.2 siguen válidos y que la suite pasa con `python tools/lab.py test api`.
- [ ] 6.4 Agregar `AUTH_TOKEN_SECRET` en `compose.yaml` para el servicio `api` con `${AUTH_TOKEN_SECRET:?...}`; verificar con `docker compose config` (si Docker está disponible).
- [ ] 6.5 Actualizar en [docs/ENDPOINTS.md](../../../docs/ENDPOINTS.md) la nota de `api/`: validación HS256, `401` genérico y dependencia de `AUTH_TOKEN_SECRET`; verificar que la descripción coincide con el comportamiento de las pruebas de 6.1.
- [ ] 6.6 Verificar cobertura del código modificado de `api/` igual o superior a 85% con `python tools/lab.py test api`.

## 7. Integración y cierre

- [ ] 7.1 Verificar que no quedan `WORKSHOP_SECRET_2026` ni `LEGACY_SECRET` en `auth/src` ni `api/app`; verificar con búsqueda de texto en esas rutas (sin contar historial de `HALLAZGOS.md`).
- [ ] 7.2 Ejecutar la prueba de integración local: login en `auth`, `GET /api/tasks` con el token recibido responde `200`, y un token alterado responde `401`; verificar con `curl` contra el servicio levantado con `AUTH_TOKEN_SECRET` ficticio.
- [ ] 7.3 Confirmar que `web/` no tiene cambios en el diff del cambio; verificar con `git --no-pager diff --stat -- web/`.

## Workflow follow-up

- Revisión y aprobación humanas antes de integrar; en el Día 1 no se hace push ni se crea PR ni tags.
- Ejecutar `openspec archive token-firmado-login` después de que la revisión esté aprobada y las pruebas reales se hayan registrado.
