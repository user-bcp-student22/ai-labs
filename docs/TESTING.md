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