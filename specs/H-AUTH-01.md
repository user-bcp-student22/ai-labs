# Spec H-AUTH-01: Concatenación de credenciales en SQL

Estado: APROBADO

## Fuente
H-AUTH-01 en [HALLAZGOS.md](../HALLAZGOS.md), severidad alta, estado `Pendiente`. Aprobado en [PLAN.md](../PLAN.md).

## Contexto actual
La búsqueda de credenciales usa `PreparedStatement` con parámetro enlazado ([LegacyDatabase.java](../auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java)). Existe la prueba de repositorio `findsUsernameContainingQuoteUsingBoundParameter` ([LegacyDatabaseTest.java](../auth/src/test/java/com/bcp/workshop/auth/LegacyDatabaseTest.java)).

## Problema confirmado
El riesgo original (concatenación de SQL) no tiene evidencia en el código actual para la búsqueda de credenciales. Falta confirmar la ruta HTTP completa y revisar si queda alguna consulta de autenticación concatenada en `auth/`.

## Comportamiento a preservar
- `POST /auth/login` con credenciales válidas responde `200` con `user.username` exacto.
- Credenciales inválidas responden `401`; requests incompletos responden `400`.

## Alcance
- Caracterizar el login HTTP con un username que contenga comilla simple.
- Revisar las consultas de credenciales dentro de `auth/`.

## Fuera de alcance
- Cambios en otros componentes (`api`, `web`).
- Cambios en el contrato del endpoint.
- Marcar el hallazgo como `Resuelto` solo con la prueba DAO existente.

## Criterios de aceptación
1. Existe una prueba HTTP `logsInWithUsernameContainingQuote` que crea en la DB aislada un usuario ficticio con comilla mediante `PreparedStatement` y responde `200` con el username exacto.
2. La prueba `findsUsernameContainingQuoteUsingBoundParameter` sigue en verde.
3. Si la revisión encuentra una consulta de autenticación concatenada, esa ruta usa parámetros enlazados y la prueba sigue en verde.
4. La DB de prueba se fija con `AUTH_DB_URL` bajo `auth/target/`.
5. El estado de H-AUTH-01 en `HALLAZGOS.md` se actualiza solo con los resultados registrados.

## Contratos afectados/protegidos
- `POST /auth/login`: ruta, request, códigos 200/400/401 y campos JSON.

## Riesgos, supuestos y preguntas abiertas
- Supuesto: el usuario de prueba es ficticio y no existe en datos reales.
- Riesgo: el fallback a `auth/data/workshop.db` si falta `AUTH_DB_URL` podría tocar datos locales.
- Pregunta abierta: ¿la revisión debe cubrir también `api/` y `web/`? Fuera de alcance según el plan.
