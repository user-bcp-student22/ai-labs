package com.bcp.workshop.auth;

import jakarta.enterprise.context.ApplicationScoped;

import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Base64;

@ApplicationScoped
public class PasswordHasher {
    static final String FORMAT_VERSION = "pbkdf2-sha256-v1";
    private static final int ITERATION_COUNT = 600_000;
    private static final int MIN_ITERATION_COUNT = 100_000;
    private static final int MAX_ITERATION_COUNT = 1_000_000;
    private static final int SALT_LENGTH_BYTES = 16;
    private static final int HASH_LENGTH_BITS = 256;

    private final SecureRandom secureRandom = new SecureRandom();

    public String hash(String password) {
        if (password == null) {
            throw new IllegalArgumentException("Password is required");
        }

        byte[] salt = new byte[SALT_LENGTH_BYTES];
        secureRandom.nextBytes(salt);
        byte[] derivedKey = deriveKey(password, salt, ITERATION_COUNT);
        return FORMAT_VERSION + "$" + ITERATION_COUNT + "$"
                + Base64.getEncoder().encodeToString(salt) + "$"
                + Base64.getEncoder().encodeToString(derivedKey);
    }

    public boolean matches(String password, String encodedHash) {
        if (password == null) {
            return false;
        }

        EncodedHash parsedHash = parseHash(encodedHash);
        if (parsedHash == null) {
            return false;
        }

        byte[] actualHash = deriveKey(password, parsedHash.salt(), parsedHash.iterations());
        return MessageDigest.isEqual(parsedHash.derivedKey(), actualHash);
    }

    boolean isHash(String encodedHash) {
        return parseHash(encodedHash) != null;
    }

    private EncodedHash parseHash(String encodedHash) {
        if (encodedHash == null) {
            return null;
        }

        String[] parts = encodedHash.split("\\$", -1);
        if (parts.length != 4 || !FORMAT_VERSION.equals(parts[0])) {
            return null;
        }

        try {
            int iterations = Integer.parseInt(parts[1]);
            if (iterations < MIN_ITERATION_COUNT || iterations > MAX_ITERATION_COUNT) {
                return null;
            }
            byte[] salt = Base64.getDecoder().decode(parts[2]);
            byte[] derivedKey = Base64.getDecoder().decode(parts[3]);
            if (salt.length != SALT_LENGTH_BYTES || derivedKey.length != HASH_LENGTH_BITS / Byte.SIZE) {
                return null;
            }
            return new EncodedHash(iterations, salt, derivedKey);
        } catch (IllegalArgumentException error) {
            return null;
        }
    }

    private byte[] deriveKey(String password, byte[] salt, int iterations) {
        char[] passwordCharacters = password.toCharArray();
        PBEKeySpec keySpec = new PBEKeySpec(passwordCharacters, salt, iterations, HASH_LENGTH_BITS);
        try {
            SecretKeyFactory keyFactory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256");
            return keyFactory.generateSecret(keySpec).getEncoded();
        } catch (GeneralSecurityException error) {
            throw new IllegalStateException("Password hashing is unavailable", error);
        } finally {
            keySpec.clearPassword();
            Arrays.fill(passwordCharacters, '\0');
        }
    }

    private record EncodedHash(int iterations, byte[] salt, byte[] derivedKey) {}
}