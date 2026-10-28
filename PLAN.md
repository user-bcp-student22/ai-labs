# Plan de corrección

## Alcance y selección

Se seleccionaron `H-AUTH-02` por riesgo alto de exposición de credenciales y `H-AUTH-04` por tener un cambio acotado al manejo de errores del endpoint. Ambos estaban `Pendiente` al aprobarse el plan y ahora constan como `Resuelto` en `HALLAZGOS.md`, con evidencia de sus pruebas. Los demás IDs conservan su estado.

No existe `docs/ENDPOINTS.md`; por tanto, se toma como contrato observado el comportamiento registrado en `HALLAZGOS.md`: `POST /auth/login` conserva sus respuestas 400 para entrada incompleta, 401 para credenciales inválidas y 200 para autenticación correcta. En el 200 se mantienen los campos `token`, `expiresIn` y `user`.

## H-AUTH-02 — Contraseñas almacenadas en texto plano - APROBADO

**Hallazgo:** `H-AUTH-02`, componente `auth`, estado actual `Pendiente`.

**Problema:** `LegacyDatabase` crea una columna de contraseña en texto y siembra usuarios con credenciales legibles. Si alguien obtiene la base SQLite, obtiene directamente las contraseñas.

**Cambio propuesto:** almacenar un verificador derivado con salt aleatorio por usuario mediante `PBKDF2WithHmacSHA256` de la JCA, con parámetros nombrados y un formato versionado para poder verificar y migrar registros. No agregar una dependencia: la JCA viene con el JDK. Actualizar el alta inicial para guardar hashes y migrar de forma idempotente las filas heredadas en texto antes de retirar su compatibilidad. El login buscará el registro por username y verificará la contraseña con el hash; las respuestas HTTP para credenciales válidas e inválidas se mantienen.

**Archivos a tocar:**

- `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`: guardar hashes al sembrar, migrar filas heredadas y leer/verificar credenciales.
- `auth/src/main/java/com/bcp/workshop/auth/PasswordHasher.java`: nueva clase para generar salts, derivar hashes y verificar contraseñas, con cada método limitado a una responsabilidad.
- `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`: caracterización de respuestas de login.
- `auth/src/test/java/com/bcp/workshop/auth/LegacyDatabaseTest.java` y `auth/src/test/java/com/bcp/workshop/auth/PasswordHasherTest.java`: pruebas de migración/persistencia y de hash/salt. Crear estas clases solo si las pruebas existentes no ofrecen un lugar adecuado.

**Prueba de caracterización antes de tocar producción:** conservar `logsInWithWorkshopUser` y añadir primero una prueba de contraseña incorrecta que compruebe `401` y ausencia de token. Ejecutarlas contra una SQLite aislada antes del cambio para registrar el comportamiento actual. Después de implementar, ampliar las pruebas para verificar que el usuario legado sigue autenticándose tras migración, que la contraseña ya no queda almacenada en claro, que salts distintos producen hashes distintos y que una contraseña incorrecta no valida.

**Dependencia de alcance:** verificar un hash requiere recuperar el registro antes de comparar la contraseña. La consulta se reemplazó por una búsqueda parametrizada por username como parte de H-AUTH-02, según el cambio propuesto y aprobado. No se actualiza aquí el estado de `H-AUTH-01`; el plan requiere mantenerlo pendiente y darle seguimiento/cierre independiente aunque este cambio ya use `PreparedStatement`.

**Riesgo contractual pendiente:** los usuarios existentes deben seguir entrando durante la migración. La prueba de base aislada debe cubrir el formato heredado y el formato hash; no usar ni modificar una base real o compartida.

## H-AUTH-04 — Respuesta de error expone detalles internos - APROBADO

**Hallazgo:** `H-AUTH-04`, componente `auth`, estado actual `Pendiente`.

**Problema:** ante una excepción no controlada, `AuthResource` devuelve al cliente el mensaje y la clase de la excepción. Esos datos pueden revelar detalles internos de la implementación.

**Cambio propuesto:** conservar el estado HTTP 500 y devolver un mensaje genérico, sin incluir mensaje ni clase de excepción en el cuerpo. Registrar la excepción únicamente en el log del servidor, sin registrar credenciales. Mantener el manejo en un bloque pequeño y sin alterar las respuestas normales 400, 401 y 200.

**Archivos a tocar:**

- `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java`: logging del error y cuerpo 500 genérico.
- `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`: caracterización y regresión del error 500.

**Prueba de caracterización antes de tocar producción:** añadir una prueba con un `LegacyDatabase` de prueba que lance una excepción con un mensaje centinela. Antes del cambio, comprobar que el endpoint devuelve 500 y registrar la forma observada del cuerpo. Tras el cambio, ajustar la expectativa para exigir 500 con mensaje genérico y comprobar que ni el mensaje centinela ni la clase de excepción aparecen en la respuesta. Mantener las pruebas de 400, 401 y 200 como controles del contrato restante.

**Riesgo contractual:** no existe contrato acordado en `docs/ENDPOINTS.md`. Se conserva el 500 y la clave `message`, se elimina `exception` y el detalle se sustituye por texto genérico para cumplir la convención de errores. H-AUTH-04 está marcado como aprobado en este plan y el comportamiento quedó caracterizado antes y después.

## Orden y verificación

1. Escribir las pruebas de caracterización indicadas y ejecutarlas con una base SQLite aislada antes de modificar producción.
2. Resolver el solapamiento de alcance entre `H-AUTH-02` y `H-AUTH-01` antes de cambiar la consulta de credenciales.
3. Implementar cada corrección en un cambio revisable, sin mezclar token, CORS ni separación general de capas.
4. Ejecutar las pruebas de `auth/` después de cada cambio y verificar la cobertura de código modificado con JaCoCo; conservar cualquier fallo y resultado real en la evidencia correspondiente.

## Registro de ejecuciones

| componente | IDs | momento | comando y entorno | resultado |
|---|---|---|---|---|
| auth | H-AUTH-02, H-AUTH-04 | Antes del cambio de producción | `mvn test` desde `auth/`, con `AUTH_DB_URL=jdbc:sqlite:./target/auth-characterization-h02-h04.db` | 3 tests, 0 fallos, 0 errores. H-AUTH-02: contraseña incorrecta respondió 401 y el cuerpo no incluyó token. H-AUTH-04: la invocación controlada del método del recurso respondió 500 con el mensaje centinela y el nombre de clase de la excepción. |
| auth | H-AUTH-04 | Después del cambio | `mvn test` desde `auth/`, con la misma SQLite aislada | 3 tests, 0 fallos, 0 errores. Se conserva el 500 con `message` genérico; no salen el centinela ni el nombre de clase en el cuerpo. El centinela aparece en el log del servidor. Login válido e inválido continúan con 200 y 401. |
| auth | H-AUTH-02, H-AUTH-04 | Antes del cambio de H-AUTH-02 | `mvn test` desde `auth/`, con la misma SQLite aislada | 7 tests, 0 fallos, 0 errores. H-AUTH-02: la contraseña sembrada se leyó en claro; H-AUTH-04 continúa ocultando detalles al cliente. Se caracterizaron además las tres respuestas 400 (request nulo, username ausente y password ausente). |
| auth | H-AUTH-02, H-AUTH-04 | Después de ambos cambios | `mvn test` desde `auth/`, con la misma SQLite aislada | 11 tests, 0 fallos, 0 errores. El login mantiene 200/401/400; los errores 500 son genéricos; la fila `student` almacena hash versionado; la migración es repetible; passwords erróneos no validan; hashes usan salts distintos; y username con comilla se busca como valor enlazado. |
| auth | H-AUTH-02 | Regresión de formato legado, antes de endurecer detección | `mvn -Dtest=LegacyDatabaseTest test` desde `auth/`, SQLite aislada | 3 tests, 1 fallo esperado: la contraseña heredada que empezaba con el prefijo del formato se confundió con un hash y no se migró. |
| auth | H-AUTH-02 | Después de endurecer detección de formato | `mvn -Dtest=LegacyDatabaseTest test` desde `auth/`, SQLite aislada | 3 tests, 0 fallos. El prefijo por sí solo ya no clasifica texto legado como hash. |
| auth | H-AUTH-02, H-AUTH-04 | Verificación final | `mvn verify` desde `auth/`, con `AUTH_DB_URL=jdbc:sqlite:./target/auth-characterization-h02-h04.db` | BUILD SUCCESS; 13 tests, 0 fallos, 0 errores. JaCoCo, líneas de producción modificadas: `AuthResource` 24/24 (100.0%), `LegacyDatabase` 46/51 (90.2%), `PasswordHasher` 38/41 (92.7%), total 108/116 (93.1%). Informe: `auth/target/site/jacoco/index.html`. |

CodeQL y Dependency Review son controles remotos y no se ejecutan en este recorrido local.

## Selección adicional de auth

Esta selección toma los tres hallazgos `Pendiente` de mayor severidad en `HALLAZGOS.md`: H-AUTH-01 (alta), H-AUTH-03 (alta) y H-AUTH-05 (media). H-AUTH-02 y H-AUTH-04 ya están marcados `Resuelto` y no se reabren aquí. El contrato de `POST /auth/login` se toma de `docs/ENDPOINTS.md` como observado, no acordado; se preservarán método, ruta, estados y estructura JSON, excepto el formato interno del campo `token`, que H-AUTH-03 pide fortalecer explícitamente. No hay tests ejecutados como parte de esta actualización del plan.

## Item: H-AUTH-01 — Concatenación de credenciales en SQL - APROBADO

**Qué item:** `H-AUTH-01`, componente `auth`, estado actual `Pendiente`, severidad alta en `HALLAZGOS.md`.

**Problema y estado del código:** la matriz conserva el riesgo por el alcance histórico de H-AUTH-02, pero el código actual ya busca el usuario mediante `PreparedStatement` (`auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:25,89-105`). Existe una prueba de repositorio con username que contiene comilla (`auth/src/test/java/com/bcp/workshop/auth/LegacyDatabaseTest.java:49-58`); falta probar el recorrido HTTP completo y confirmar si queda alguna consulta de autenticación concatenada.

**Cambio propuesto:** no duplicar una corrección ya presente. Añadir la caracterización del login HTTP para un usuario ficticio cuyo username contiene una comilla, usando la SQLite aislada del test. Comprobar que el usuario se autentica y que el valor se trata como dato. Revisar las consultas de credenciales existentes dentro de `auth/`; si la prueba revela una ruta concatenada, cambiar únicamente esa ruta a parámetros enlazados. Con la evidencia completa, actualizar H-AUTH-01 en `HALLAZGOS.md`; no marcarlo resuelto solo por la prueba DAO existente.

**Archivos a tocar:** `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`; reutilizar `auth/src/test/java/com/bcp/workshop/auth/LegacyDatabaseTest.java`. Tocar `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java` solo si la caracterización o la revisión local encuentra una consulta de autenticación todavía concatenada.

**Prueba antes de tocar producción:** añadir primero `logsInWithUsernameContainingQuote`, que inserte en la DB aislada un usuario ficticio con comilla mediante `PreparedStatement`, haga `POST /auth/login` con credenciales válidas y exija `200` y el username exacto en `user.username`. Ejecutar también `findsUsernameContainingQuoteUsingBoundParameter`, ya existente. Si ambos pasan y no se encuentra otra consulta concatenada, no hace falta editar código de producción; registrar los resultados antes de cambiar el estado del hallazgo.

**Contrato y riesgos:** no cambia el contrato observado de endpoint. El valor de prueba no debe ser un usuario real y la DB debe vivir bajo `auth/target/`; las pruebas actuales tienen un fallback a `auth/data/workshop.db` si falta `AUTH_DB_URL`, por lo que la variable de aislamiento debe fijarse al ejecutarlas.

## Item: H-AUTH-03 — Token Base64 sin firma y con secreto embebido - APROBADO

**Qué item:** `H-AUTH-03`, componente `auth`, estado actual `Pendiente`, severidad alta en `HALLAZGOS.md`.

**Problema:** `LegacyTokenUtil` concatena username, role, timestamp y un secreto fijo y luego solo codifica el texto en Base64 (`auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java:8,12-15`). Base64 no acredita firma ni enforcement del vencimiento. La respuesta anuncia `expiresIn=3600` (`auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:41-49`).

**Cambio propuesto:** reemplazar la codificación Base64 por un token firmado con claims explícitos de identidad/rol y expiración verificable; mover la clave de firma a configuración externa, nunca al código fuente. Mantener `POST /auth/login`, los estados HTTP y las claves/estructura JSON observadas; el contenido de `token` cambiará por ser el objeto de este hallazgo. Evaluar la extensión SmallRye JWT de Quarkus (`auth/pom.xml` actualmente no la declara) como dependencia acotada para evitar implementar manualmente un formato criptográfico. Antes de agregarla, confirmar compatibilidad con Quarkus `3.27.4` y revisar advisories; no incluir claves privadas reales en pruebas o repositorio.

**Archivos a tocar:** `auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java`; `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java` si necesita recibir expiración/configuración; `auth/src/main/resources/application.properties` para configuración externa; `auth/pom.xml` solo si se aprueba la extensión; `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java` y una nueva prueba enfocada en el token, por ejemplo `auth/src/test/java/com/bcp/workshop/auth/LegacyTokenUtilTest.java`.

**Prueba antes de tocar producción:** ampliar primero `logsInWithWorkshopUser` para fijar el contrato observado: `200`, `token` no nulo, `expiresIn` igual a 3600 y los campos actuales de `user`/`debug`. Registrar el formato legacy solo como comportamiento previo, no como expectativa posterior. Después de implementar, comprobar firma y claims con la clave ficticia de test, expiración efectiva, rechazo de token alterado y que la respuesta del login conserve su estructura JSON.

**Contrato y riesgos:** ruta, request, status y campos JSON se conservan; el token deja de ser compatible con consumidores que decodifican manualmente el valor Base64. `docs/ENDPOINTS.md` debe actualizar su nota de seguridad durante la implementación, cuando la elección criptográfica y la validación estén comprobadas. La coordinación de consumidores queda pendiente y no autoriza leer o cambiar otros componentes dentro de este plan.

## Item: H-AUTH-05 — CORS permite orígenes mediante patrón amplio - APROBADO

**Qué item:** `H-AUTH-05`, componente `auth`, estado actual `Pendiente`, severidad media en `HALLAZGOS.md`.

**Problema:** CORS está habilitado con `quarkus.http.cors.origins=/.*/`, que permite una coincidencia amplia de orígenes (`auth/src/main/resources/application.properties:4-7`). Esto no autentica al usuario y permite a páginas de otros orígenes intentar leer respuestas desde el navegador.

**Cambio propuesto:** reemplazar el patrón universal por una allowlist explícita configurable por ambiente. El origen local de UI `http://localhost:4200` se desprende de `README.md`; los orígenes de producción deben proporcionarlos los responsables del despliegue y quedan pendientes, no se inventan en este plan. Mantener métodos y headers requeridos por el contrato observado; no agregar dependencia.

**Archivos a tocar:** `auth/src/main/resources/application.properties`; `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java` o una clase de test con `QuarkusTestProfile` para probar configuración CORS sin alterar otros perfiles.

**Prueba antes de tocar producción:** añadir primero una prueba de preflight que envíe `Origin: http://localhost:4200` y registre los headers CORS actuales. Añadir un origen de prueba distinto y caracterizar si hoy se refleja. Tras aplicar la allowlist, la regresión debe exigir que el origen permitido reciba `Access-Control-Allow-Origin` con coincidencia exacta y que el origen no permitido no reciba ese header. No usar la respuesta permisiva actual como resultado esperado final.

**Contrato y riesgos:** CORS cambia solo qué orígenes de navegador pueden leer respuestas; no cambia el request/response ni la autorización del endpoint. Confirmar con despliegue cuál es la allowlist productiva antes de activar la configuración en producción. La prueba debe usar origen ficticio/local y no afirmar que CORS reemplaza autenticación.