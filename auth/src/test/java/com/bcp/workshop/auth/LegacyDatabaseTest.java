package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import jakarta.inject.Inject;
import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@QuarkusTest
class LegacyDatabaseTest {
    private static final String USERNAME = "legacy-migration-test-user";
    private static final String LEGACY_PASSWORD = "Legacy-Test-Password";
    private static final String DB_URL = System.getenv().getOrDefault("AUTH_DB_URL", "jdbc:sqlite:./data/workshop.db");

    @Inject
    LegacyDatabase database;

    @Inject
    PasswordHasher passwordHasher;

    @Test
    void migratesLegacyPasswordIdempotentlyAndAuthenticatesUser() throws SQLException {
        insertUser(USERNAME, LEGACY_PASSWORD);
        try {
            database.migratePlaintextPasswords();
            String migratedPassword = storedPassword(USERNAME);
            database.migratePlaintextPasswords();

            assertNotEquals(LEGACY_PASSWORD, migratedPassword);
            assertTrue(passwordHasher.isHash(migratedPassword));
            assertTrue(passwordHasher.isHash(storedPassword(USERNAME)));
            assertNotNull(database.findByCredentials(USERNAME, LEGACY_PASSWORD));
            assertNull(database.findByCredentials(USERNAME, "Wrong-Test-Password"));
        } finally {
            deleteUser(USERNAME);
        }
    }

    @Test
    void findsUsernameContainingQuoteUsingBoundParameter() throws SQLException {
        String quotedUsername = "test-o'brien";
        String password = "Quoted-User-Password";
        insertUser(quotedUsername, passwordHasher.hash(password));
        try {
            assertNotNull(database.findByCredentials(quotedUsername, password));
        } finally {
            deleteUser(quotedUsername);
        }
    }

    @Test
    void migratesLegacyPasswordThatStartsWithHashVersionPrefix() throws SQLException {
        String username = "legacy-prefixed-test-user";
        String password = PasswordHasher.FORMAT_VERSION + "$legacy-password-text";
        insertUser(username, password);
        try {
            database.migratePlaintextPasswords();

            assertNotEquals(password, storedPassword(username));
            assertNotNull(database.findByCredentials(username, password));
        } finally {
            deleteUser(username);
        }
    }

    private void insertUser(String username, String password) throws SQLException {
        try (Connection connection = DriverManager.getConnection(DB_URL);
             PreparedStatement statement = connection.prepareStatement(
                     "INSERT OR REPLACE INTO legacy_users(username,password,display_name,role) VALUES (?,?,?,?)")) {
            statement.setString(1, username);
            statement.setString(2, password);
            statement.setString(3, "Test User");
            statement.setString(4, "STUDENT");
            statement.executeUpdate();
        }
    }

    private String storedPassword(String username) throws SQLException {
        try (Connection connection = DriverManager.getConnection(DB_URL);
             PreparedStatement statement = connection.prepareStatement(
                     "SELECT password FROM legacy_users WHERE username=?")) {
            statement.setString(1, username);
            try (ResultSet result = statement.executeQuery()) {
                if (!result.next()) {
                    throw new AssertionError("Expected test user was not found");
                }
                return result.getString("password");
            }
        }
    }

    private void deleteUser(String username) throws SQLException {
        try (Connection connection = DriverManager.getConnection(DB_URL);
             PreparedStatement statement = connection.prepareStatement(
                     "DELETE FROM legacy_users WHERE username=?")) {
            statement.setString(1, username);
            statement.executeUpdate();
        }
    }
}