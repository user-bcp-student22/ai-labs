package com.bcp.workshop.auth;

import jakarta.annotation.PostConstruct;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

@ApplicationScoped
public class LegacyDatabase {
    private static final String DB_URL = System.getenv().getOrDefault("AUTH_DB_URL", "jdbc:sqlite:./data/workshop.db");
    private static final String CREATE_USERS_TABLE_SQL = "CREATE TABLE IF NOT EXISTS legacy_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT NOT NULL, display_name TEXT NOT NULL, role TEXT NOT NULL)";
    private static final String INSERT_USER_SQL = "INSERT OR IGNORE INTO legacy_users(username,password,display_name,role) VALUES (?,?,?,?)";
    private static final String SELECT_LEGACY_PASSWORDS_SQL = "SELECT id, password FROM legacy_users";
    private static final String UPDATE_PASSWORD_SQL = "UPDATE legacy_users SET password=? WHERE id=?";
    private static final String FIND_USER_SQL = "SELECT id, username, display_name, role, password FROM legacy_users WHERE username=?";

    @Inject
    PasswordHasher passwordHasher;

    @PostConstruct
    void initialize() {
        try {
            Files.createDirectories(Path.of("data"));
            try (Connection connection = DriverManager.getConnection(DB_URL)) {
                createUsersTable(connection);
                seedUser(connection, "student", "Workshop123!", "Workshop Student", "STUDENT");
                seedUser(connection, "trainer", "Trainer123!", "Workshop Trainer", "TRAINER");
                migratePlaintextPasswords(connection);
            }
        } catch (Exception error) {
            error.printStackTrace();
        }
    }

    private void createUsersTable(Connection connection) throws SQLException {
        try (Statement statement = connection.createStatement()) {
            statement.executeUpdate(CREATE_USERS_TABLE_SQL);
        }
    }

    private void seedUser(Connection connection, String username, String password, String displayName, String role) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement(INSERT_USER_SQL)) {
            statement.setString(1, username);
            statement.setString(2, passwordHasher.hash(password));
            statement.setString(3, displayName);
            statement.setString(4, role);
            statement.executeUpdate();
        }
    }

    void migratePlaintextPasswords() throws SQLException {
        try (Connection connection = DriverManager.getConnection(DB_URL)) {
            migratePlaintextPasswords(connection);
        }
    }

    private void migratePlaintextPasswords(Connection connection) throws SQLException {
        List<StoredPassword> plaintextPasswords = new ArrayList<>();
        try (PreparedStatement statement = connection.prepareStatement(SELECT_LEGACY_PASSWORDS_SQL);
             ResultSet result = statement.executeQuery()) {
            while (result.next()) {
                String storedPassword = result.getString("password");
                if (!passwordHasher.isHash(storedPassword)) {
                    plaintextPasswords.add(new StoredPassword(result.getLong("id"), storedPassword));
                }
            }
        }

        try (PreparedStatement statement = connection.prepareStatement(UPDATE_PASSWORD_SQL)) {
            for (StoredPassword storedPassword : plaintextPasswords) {
                statement.setString(1, passwordHasher.hash(storedPassword.password()));
                statement.setLong(2, storedPassword.userId());
                statement.addBatch();
            }
            statement.executeBatch();
        }
    }

    public UserRecord findByCredentials(String username, String password) {
        try (Connection connection = DriverManager.getConnection(DB_URL);
             PreparedStatement statement = connection.prepareStatement(FIND_USER_SQL)) {
            statement.setString(1, username);
            try (ResultSet result = statement.executeQuery()) {
                if (!result.next()) {
                    return null;
                }
                if (!passwordHasher.matches(password, result.getString("password"))) {
                    return null;
            }
                return new UserRecord(result.getLong("id"), result.getString("username"), result.getString("display_name"), result.getString("role"));
            }
        } catch (Exception error) {
            error.printStackTrace();
        }
        return null;
    }

    private record StoredPassword(long userId, String password) {}
}
