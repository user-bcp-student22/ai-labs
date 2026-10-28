# Spec H-AUTH-03: Token Base64 sin firma y con secreto embebido 
Estado: APROBADO

## Fuente
H-AUTH-03 en [HALLAZGOS.md](../HALLAZGOS.md), severidad alta, estado `Pendiente`. Aprobado en [PLAN.md](../PLAN.md).

## Contexto actual
[LegacyTokenUtil.java](../auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java) concatena username, rol, expiración y un secreto fijo, y luego codifica el texto en Base64. [AuthResource.java](../auth/src/main/java/com/bcp/workshop/auth/AuthResource.java) devuelve el token con `expiresIn` igual a 3600.

## Problema confirmado
Base64 no garantiza integridad ni autenticidad. El secreto está embebido en el código fuente y el token no tiene firma verificable.

## Comportamiento a preservar
- Ruta, método, request y códigos HTTP de `POST /auth/login`.
- Campos JSON `token`, `expiresIn`, `user` y `debug`.
- `expiresIn` coherente con la expiración del token.

## Alcance
- Reemplazar la codificación Base64 por un token firmado con claims de identidad, rol y expiración.
- Mover la clave de firma a configuración externa.

## Fuera de alcance
- Cambios en la estructura JSON de la respuesta de login.
- Consumidores externos del token (coordinación pendiente).
- Cambios en otros componentes.

## Criterios de aceptación
1. Antes de cambiar producción, la prueba `logsInWithWorkshopUser` fija `200`, `token` no nulo, `expiresIn` igual a 3600 y los campos `user`/`debug`.
2. El token generado tiene firma verificable con la clave de prueba.
3. Un token alterado es rechazado por la verificación.
4. La expiración del token coincide con `expiresIn`.
5. La clave de firma se lee de configuración externa y no aparece en el código fuente.
6. La respuesta de login conserva su estructura JSON.
7. Ningún secreto real aparece en pruebas o repositorio.

## Contratos afectados/protegidos
- `POST /auth/login`: ruta, request, códigos y estructura JSON. El contenido de `token` cambia por ser objeto de este hallazgo.
- [docs/ENDPOINTS.md](../docs/ENDPOINTS.md): nota de seguridad a actualizar durante la implementación.

## Riesgos, supuestos y preguntas abiertas
- Discrepancia abierta: el borrador [HU-01.md](../HU-01.md) describe HMAC con `AUTH_TOKEN_SECRET`, pero el código actual no implementa HMAC y `application.properties` no declara `AUTH_TOKEN_SECRET`. Debe resolverse antes de implementar.
- Pregunta abierta: ¿HMAC propio o la extensión SmallRye JWT? La decisión queda para `architecture-decision`.
- Pregunta abierta: ruta del HU (`auth/HU-01.md` vs `HU-01.md` raíz vs `workshop-auth-backend/HU-01.md`, que no existe).
- Riesgo: consumidores que decodifican el token en Base64 dejarán de funcionar.
- Riesgo: confirmar compatibilidad con Quarkus `3.27.4` y revisar advisories antes de agregar dependencias.
