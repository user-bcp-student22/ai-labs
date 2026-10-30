package com.bcp.workshop.auth;

public class LoginRejectedException extends RuntimeException {
    private final int status;

    public LoginRejectedException(int status, String message) {
        super(message);
        this.status = status;
    }

    public int status() {
        return status;
    }
}
