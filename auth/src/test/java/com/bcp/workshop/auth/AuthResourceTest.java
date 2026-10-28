package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import jakarta.inject.Inject;
import jakarta.ws.rs.core.Response;
import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.containsString;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.CoreMatchers.not;
import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.notNullValue;

@QuarkusTest
class AuthResourceTest {
    @Inject
    PasswordHasher passwordHasher;

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
    void logsInWithUsernameContainingQuote() throws SQLException {
        String username = "http-o'brien-test";
        String password = "Quoted-Http-Password";
        insertUser(username, passwordHasher.hash(password));
        try {
            given()
                    .contentType("application/json")
                    .body("{\"username\":\"" + username + "\",\"password\":\"" + password + "\"}")
                    .when().post("/auth/login")
                    .then()
                    .statusCode(200)
                    .body("user.username", is(username));
        } finally {
            deleteUser(username);
        }
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
    void storesWorkshopPasswordAsVersionedHash() throws SQLException {
        String storedPassword = storedPassword("student");
        assertNotEquals("Workshop123!", storedPassword);
        assertTrue(passwordHasher.isHash(storedPassword));
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
        java.util.Map<?, ?> body = (java.util.Map<?, ?>) response.getEntity();
        assertEquals("Internal server error", body.get("message"));
        assertFalse(body.containsKey("exception"));
        assertFalse(body.toString().contains("database-error-sentinel"));
        assertFalse(body.toString().contains(IllegalStateException.class.getName()));
    }

    private void insertUser(String username, String password) throws SQLException {
        String databaseUrl = System.getenv().getOrDefault("AUTH_DB_URL", "jdbc:sqlite:./data/workshop.db");
        try (Connection connection = DriverManager.getConnection(databaseUrl);
             PreparedStatement statement = connection.prepareStatement(
                     "INSERT OR REPLACE INTO legacy_users(username,password,display_name,role) VALUES (?,?,?,?)")) {
            statement.setString(1, username);
            statement.setString(2, password);
            statement.setString(3, "Test User");
            statement.setString(4, "STUDENT");
            statement.executeUpdate();
        }
    }

    private void deleteUser(String username) throws SQLException {
        String databaseUrl = System.getenv().getOrDefault("AUTH_DB_URL", "jdbc:sqlite:./data/workshop.db");
        try (Connection connection = DriverManager.getConnection(databaseUrl);
             PreparedStatement statement = connection.prepareStatement(
                     "DELETE FROM legacy_users WHERE username=?")) {
            statement.setString(1, username);
            statement.executeUpdate();
        }
    }

    private String storedPassword(String username) throws SQLException {
        String databaseUrl = System.getenv().getOrDefault("AUTH_DB_URL", "jdbc:sqlite:./data/workshop.db");
        try (Connection connection = DriverManager.getConnection(databaseUrl);
             PreparedStatement statement = connection.prepareStatement(
                     "SELECT password FROM legacy_users WHERE username = ?")) {
            statement.setString(1, username);
            try (ResultSet result = statement.executeQuery()) {
                if (!result.next()) {
                    throw new AssertionError("Expected test user was not initialized");
                }
                return result.getString("password");
            }
        }
    }
}
