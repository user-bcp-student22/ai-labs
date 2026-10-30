package com.bcp.workshop.auth;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;

@ApplicationScoped
public class LoginService {
    private static final String CLIENT_NOT_ALLOWED_MESSAGE = "Client is not allowed";

    @Inject
    LegacyDatabase database;

    @ConfigProperty(name = "auth.client.allowed")
    String allowedClient;

    public UserRecord authenticate(LoginRequest request) {
        validate(request);
        UserRecord user = database.findByCredentials(request.username, request.password);
        if (user == null) {
            throw new LoginRejectedException(401, "Invalid user " + request.username + " or password");
        }
        return user;
    }

    private void validate(LoginRequest request) {
        if (request == null) {
            throw new LoginRejectedException(400, "Request is null");
        }
        if (isBlank(request.username)) {
            throw new LoginRejectedException(400, "Username is required");
        }
        if (isBlank(request.password)) {
            throw new LoginRejectedException(400, "Password is required");
        }
        if (!allowedClient.equals(request.client)) {
            throw new LoginRejectedException(400, CLIENT_NOT_ALLOWED_MESSAGE);
        }
    }

    private static boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}
