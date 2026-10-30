# Pruebas

## auth

Las pruebas de endpoint y persistencia están en `auth/src/test/java/com/bcp/workshop/auth/`. La suite Quarkus necesita una base local aislada: `LegacyDatabase` usa `AUTH_DB_URL` y, si falta, escribe en `./data/workshop.db`. Define la variable explícitamente antes de correr tests para no tocar una base local existente. Los ejemplos siguientes usan SQLite dentro de `auth/target/` y no contienen secretos reales.

### Matriz de casos

| endpoint | caso | tipo | resultado esperado |
|---|---|---|---|
| `GET /q/health` | Estado saludable sin autenticación | Camino feliz | `200`, `status=UP`; comprobado en el test local. |
| `GET /q/health` | Sin checks de salud configurados en auth | Borde | `200`, `checks=[]`; observado en la configuración actual del componente. |
| `GET /q/health` | Check `DOWN` o servicio no saludable | Pendiente | No hay un check auth ni una respuesta de error documentada; estado/cuerpo por verificar si se agrega un check. |
| `POST /auth/login` | Credenciales ficticias válidas | Camino feliz | `200`, usuario `student` y token no nulo. |
| `POST /auth/login` | Username vacío | Borde | `400`, `Username is required`. |
| `POST /auth/login` | Password solo con espacios | Borde | `400`, `Password is required`. |
| `POST /auth/login` | JSON `null` | Error documentado | `400`, `Request is null`. |
| `POST /auth/login` | Username ausente | Error documentado | `400`, `Username is required`. |
| `POST /auth/login` | Password ausente | Error documentado | `400`, `Password is required`. |
| `POST /auth/login` | Contraseña incorrecta | Error documentado | `401`, `Invalid user student or password`; sin token. |
| `POST /auth/login` | Excepción inesperada dentro del recurso | Error documentado | `500`, `Internal server error`; el cuerpo no contiene detalle de excepción. El test invoca `AuthResource.login` directamente, no la serialización HTTP. |

### Código de tests de endpoint

Extractos de `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`; los helpers y pruebas de almacenamiento están en el archivo completo.

```java
@Test
void reportsHealthAsUpWithoutAuthentication() {
    given()
            .when().get("/q/health")
            .then()
            .statusCode(200)
            .body("status", is("UP"));
}

@Test
void reportsEmptyCheckListWhenNoHealthChecksAreConfigured() {
    given()
            .when().get("/q/health")
            .then()
            .statusCode(200)
            .body("checks", empty());
}

@Test
void logsInWithWorkshopUser() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(200)
            .body("user.username", is("student"))
            .body("token", notNullValue());
}

@Test
void rejectsEmptyUsername() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"\",\"password\":\"Test-Only-Password\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(400)
            .body("message", is("Username is required"));
}

@Test
void rejectsWhitespaceOnlyPassword() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"student\",\"password\":\"   \"}")
            .when().post("/auth/login")
            .then()
            .statusCode(400)
            .body("message", is("Password is required"));
}

@Test
void rejectsNullLoginRequest() {
    given()
            .contentType("application/json")
            .body("null")
            .when().post("/auth/login")
            .then()
            .statusCode(400)
            .body("message", is("Request is null"));
}

@Test
void rejectsLoginWithoutUsername() {
    given()
            .contentType("application/json")
            .body("{\"password\":\"Test-Only-Password\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(400)
            .body("message", is("Username is required"));
}

@Test
void rejectsLoginWithoutPassword() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"student\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(400)
            .body("message", is("Password is required"));
}

@Test
void rejectsWorkshopUserWithIncorrectPassword() {
    given()
            .contentType("application/json")
            .body("{\"username\":\"student\",\"password\":\"Incorrect-Test-Password\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(401)
            .body("message", is("Invalid user student or password"))
            .body(not(containsString("token")));
}

@Test
void hidesExceptionDetailsWhenDatabaseLookupFails() {
    AuthResource resource = new AuthResource();
    resource.database = new LegacyDatabase() {
        @Override
        public UserRecord findByCredentials(String username, String password) {
            throw new IllegalStateException("database-error-sentinel");
        }
    };
    LoginRequest request = new LoginRequest();
    request.username = "student";
    request.password = "Test-Only-Password";

    Response response = resource.login(request);

    assertEquals(500, response.getStatus());
    Map<?, ?> body = (Map<?, ?>) response.getEntity();
    assertEquals("Internal server error", body.get("message"));
    assertFalse(body.containsKey("exception"));
    assertFalse(body.toString().contains("database-error-sentinel"));
}
```

Las pruebas de persistencia/hash adicionales caracterizan migración idempotente, hash con salt, contraseña incorrecta y username con comilla en `LegacyDatabaseTest` y `PasswordHasherTest`.

### Ejecuciones

| componente | IDs/endpoint | comando y directorio | código de salida | resultado |
|---|---|---|---:|---|
| auth | `GET /q/health`, `POST /auth/login` | PowerShell, `cwd=auth/`, `AUTH_DB_URL=jdbc:sqlite:./target/auth-testing-docs.db`; `mvn -Dtest=AuthResourceTest test` | 0 | 11 tests, 0 fallos, 0 errores. Health respondió 200/UP y `checks=[]`; login válido, errores y bordes de campos pasaron. |
| auth | Suite completa | PowerShell, `cwd=auth/`, misma `AUTH_DB_URL`; `mvn verify` | 0 | BUILD SUCCESS; 17 tests, 0 fallos, 0 errores. |
| auth | H-AUTH-03, línea base 1 (1.2) | PowerShell, `cwd=raíz`, `AUTH_DB_URL=jdbc:sqlite:./target/auth-testing.db`; `python tools/lab.py test auth` | 1 | BUILD FAILURE de entorno: `Port already bound: 8081`. El puerto lo ocupa un proceso `node` de mcp-proxy del usuario (PID 16152), que no se detuvo. |
| auth | H-AUTH-03, línea base 2 (1.2) | Igual que la anterior, más `QUARKUS_HTTP_TEST_PORT=18081`; base SQLite nueva | 1 | Fallo de fixture: `no such table: legacy_users` en `AuthResourceTest.insertUser` (llamado desde `logsInWithUsernameContainingQuote`). La tabla la crea `LegacyDatabase.initialize()` solo al instanciar el bean; la prueba escribe por JDBC antes de que exista. 18 tests, 1 error, 14 omitidos. |
| auth | H-AUTH-03, línea base 3 (1.2) | Igual, con la base aislada ya creada por la ejecución anterior | 0 | BUILD SUCCESS; 18 tests, 0 fallos, 0 errores (12 `AuthResourceTest`, 3 `LegacyDatabaseTest`, 3 `PasswordHasherTest`). |
| auth | H-AUTH-03, caracterización 2.1-2.4 | Igual, `QUARKUS_HTTP_TEST_PORT=18081` | 0 | BUILD SUCCESS; 21 tests, 0 fallos, 0 errores (15 `AuthResourceTest`). Pruebas nuevas listadas abajo. |
| api | H-AUTH-03, setup del entorno | PowerShell, `cwd=raíz`; `python tools/lab.py setup api` | 0 | Creó `api/.venv` con Python 3.13 e instaló `requirements.txt` y `requirements-dev.txt`. |
| api | H-AUTH-03, caracterización 3.1-3.3 | PowerShell, `cwd=raíz`; `python tools/lab.py test api` | 0 | 6 passed, 0 fallos. Cobertura total 91.96%; compuerta `--cov-fail-under=85` cumplida. No hubo ejecución previa a las pruebas nuevas porque `api/.venv` no existía. |
| auth | H-AUTH-03, baseline 1.2 previo a refactor | PowerShell, `cwd=raíz`; `openspec validate token-firmado-login --strict`; `AUTH_DB_URL=jdbc:sqlite:./target/auth-testing.db`, `QUARKUS_HTTP_TEST_PORT=18081`; `python tools/lab.py test auth` | 0 | Change valid. BUILD SUCCESS; 21 tests, 0 fallos, 0 errores. Mensaje de error en log de `hidesExceptionDetailsWhenDatabaseLookupFails` es esperado (fallo inyectado). |
| api | H-AUTH-03, baseline 1.2 previo a refactor | PowerShell, `cwd=raíz`; `python tools/lab.py test api` | 0 | 6 passed, 0 fallos. Cobertura total 92.86%; compuerta 85% cumplida. |
| auth | H-AUTH-03, refactor 4.1 (LoginService) | PowerShell, `cwd=raíz`; `AUTH_DB_URL=jdbc:sqlite:./target/auth-testing.db`, `QUARKUS_HTTP_TEST_PORT=18081`; `python tools/lab.py test auth` | 0 | BUILD SUCCESS; 21 tests, 0 fallos, 0 errores. Cambio de wiring en `hidesExceptionDetailsWhenDatabaseLookupFails` (usa `LoginService.database`); aserciones sin cambio. |
| auth | H-AUTH-03, refactor 4.2 (TokenIssuer con Clock, LegacyTokenUtil eliminado) | Igual que 4.1 | 0 | BUILD SUCCESS; 21 tests, 0 fallos, 0 errores. Formato Base64 sin cambio. |

#### Caracterización H-AUTH-03 (pruebas nuevas o completadas)

| prueba | requisito que protege | estado actual |
|---|---|---|
| `AuthResourceTest.logsInWithWorkshopUser` (ampliada) | Estructura del login: `expiresIn=3600`, `user.displayName`, `user.role`, `debug=authenticated-with-legacy-flow` | Pasa |
| `AuthResourceTest.escapesDisplayNameAsHtml4InLoginResponse` | `displayName` escapado en HTML4 (`<`, `&`, `"`) | Pasa |
| `AuthResourceTest.acceptsLoginWithoutClientFieldCurrentlyReturns200` | Login sin `client` responde 200; cambia a 400 en la tarea 5.6 | Pasa (comportamiento a cambiar) |
| `AuthResourceTest.rejectsWhitespaceOnlyUsername` | Username con solo espacios responde 400 | Pasa |
| `AuthResourceTest` (existentes) | Health, 400, 401, 500 | Pasan |
| `api/tests/test_api.py::test_lists_only_trainer_tasks_for_trainer_token` | Owner por defecto es el usuario del token | Pasa |
| `api/tests/test_api.py::test_rejects_expired_legacy_token` | Token legacy vencido responde 401 | Pasa |
| `api/tests/test_api.py::test_rejects_invalid_token` (existente) | Token inválido responde 401 | Pasa |

Hallazgo de fixture (no corregido en esta tarea): `AuthResourceTest.insertUser` depende de que `LegacyDatabase` haya creado la tabla antes. Con una base SQLite nueva, la primera prueba que escribe falla. Requiere revisión antes de tomar la suite como reproducible desde cero.

### Cobertura

Reporte JaCoCo: `auth/target/site/jacoco/index.html`, generado por `mvn verify` con el plugin existente de `auth/pom.xml`. Método: sumar `covered` y `missed` del contador XML `LINE` para las clases de producción tocadas en el flujo (`AuthResource`, `LegacyDatabase`, `PasswordHasher`); no es la cobertura global del bundle.

| clase | líneas cubiertas | cobertura de líneas |
|---|---:|---:|
| `AuthResource` | 24/24 | 100.0% |
| `LegacyDatabase` | 49/54 | 90.7% |
| `PasswordHasher` | 38/41 | 92.7% |
| **Total de clases de producción modificadas** | **111/119** | **93.3%** |

### Fallos, pendientes y pruebas propuestas

**Fallos:** ninguno en la ejecución enfocada ni en `mvn verify`.

**Pendientes:** no se verificó la respuesta de health cuando hay un check `DOWN`; auth no declara checks propios. No se caracterizó el cuerpo/status que REST/Jackson produce para JSON malformado. El error 500 se prueba invocando el método del recurso directamente, no mediante petición HTTP completa.

**Pruebas propuestas:** si se agrega un `HealthCheck`, añadir caso `DOWN` con el status y cuerpo observados; caracterizar JSON malformado en el runtime Quarkus antes de documentar su formato; sustituir el test directo de 500 por una prueba HTTP con bean CDI de fallo controlado cuando se disponga de un perfil/alternativa de test adecuado.