package com.bcp.workshop.auth;

import org.junit.jupiter.api.Test;

import java.util.Base64;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PasswordHasherTest {
    private final PasswordHasher passwordHasher = new PasswordHasher();

    @Test
    void hashesWithUniqueSaltsAndMatchesOriginalPassword() {
        String firstHash = passwordHasher.hash("Test-Only-Password");
        String secondHash = passwordHasher.hash("Test-Only-Password");

        assertNotEquals(firstHash, secondHash);
        assertTrue(passwordHasher.matches("Test-Only-Password", firstHash));
        assertTrue(passwordHasher.matches("Test-Only-Password", secondHash));
    }

    @Test
    void rejectsIncorrectPasswordsAndMalformedHashes() {
        String hash = passwordHasher.hash("Test-Only-Password");
        String validSalt = Base64.getEncoder().encodeToString(new byte[16]);
        String shortHash = Base64.getEncoder().encodeToString(new byte[1]);

        assertFalse(passwordHasher.matches("Wrong-Test-Password", hash));
        assertFalse(passwordHasher.matches(null, hash));
        assertFalse(passwordHasher.matches("Test-Only-Password", "not-a-hash"));
        assertFalse(passwordHasher.matches("Test-Only-Password", PasswordHasher.FORMAT_VERSION + "$bad$%%%$%%%"));
        assertFalse(passwordHasher.matches("Test-Only-Password", PasswordHasher.FORMAT_VERSION + "$600000$" + validSalt));
        assertFalse(passwordHasher.matches("Test-Only-Password", PasswordHasher.FORMAT_VERSION + "$99999$" + validSalt + "$" + shortHash));
        assertFalse(passwordHasher.matches("Test-Only-Password", PasswordHasher.FORMAT_VERSION + "$600000$" + validSalt + "$" + shortHash));
    }

    @Test
    void rejectsNullPasswordWhenCreatingHash() {
        assertThrows(IllegalArgumentException.class, () -> passwordHasher.hash(null));
    }
}