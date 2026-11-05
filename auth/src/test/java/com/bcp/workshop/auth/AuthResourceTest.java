package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.notNullValue;
import static org.hamcrest.Matchers.nullValue;

@QuarkusTest
class AuthResourceTest {
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

    // Protege el rechazo de credenciales ordinarias inválidas: 401 y sin token.
    @Test
    void rejectsValidUsernameWithWrongPassword() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"WrongPassword!\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(401)
                .body("token", nullValue());
    }

    // Protege la validación existente: usuario o contraseña ausente, vacío o en blanco responde 400.
    @ParameterizedTest
    @ValueSource(strings = {
            "{\"password\":\"Workshop123!\"}",
            "{\"username\":\"\",\"password\":\"Workshop123!\"}",
            "{\"username\":\"   \",\"password\":\"Workshop123!\"}",
            "{\"username\":\"student\"}",
            "{\"username\":\"student\",\"password\":\"\"}",
            "{\"username\":\"student\",\"password\":\"   \"}",
            "{}"
    })
    void rejectsMissingOrBlankCredentialsWithBadRequest(String requestBody) {
        given()
                .contentType("application/json")
                .body(requestBody)
                .when().post("/auth/login")
                .then()
                .statusCode(400);
    }

    // Spec "SQL-injection attempt in password is rejected": 401 y sin token.
    @Test
    void rejectsSqlInjectionInPassword() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"' OR '1'='1\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(401)
                .body("token", nullValue());
    }

    // Spec "SQL-injection attempt in username is rejected": 401 y sin token.
    @Test
    void rejectsSqlInjectionInUsername() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"' OR '1'='1\",\"password\":\"WrongPassword!\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(401)
                .body("token", nullValue());
    }
}
