package com.bcp.workshop.auth;

import io.quarkus.runtime.Startup;
import io.smallrye.jwt.algorithm.SignatureAlgorithm;
import io.smallrye.jwt.build.Jwt;
import jakarta.inject.Inject;
import jakarta.inject.Singleton;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import java.time.Clock;

/**
 * Emite tokens JWS HS256 con los claims sub, client, iat y exp.
 * Anotado con {@link Startup} para que la clave ausente impida el arranque del servicio.
 */
@Startup
@Singleton
public class TokenIssuer {
    private static final String CLAIM_CLIENT = "client";

    private final Clock clock;
    private final String secret;
    private final int ttlSeconds;

    @Inject
    public TokenIssuer(
            @ConfigProperty(name = "auth.token.secret") String secret,
            @ConfigProperty(name = "auth.token.ttl-seconds") int ttlSeconds) {
        this(Clock.systemUTC(), secret, ttlSeconds);
    }

    TokenIssuer(Clock clock, String secret, int ttlSeconds) {
        this.clock = clock;
        this.secret = secret;
        this.ttlSeconds = ttlSeconds;
    }

    public int ttlSeconds() {
        return ttlSeconds;
    }

    public String issue(String username, String client) {
        long issuedAt = clock.instant().getEpochSecond();
        return Jwt.claims()
                .subject(username)
                .claim(CLAIM_CLIENT, client)
                .issuedAt(issuedAt)
                .expiresAt(issuedAt + ttlSeconds)
                .jws()
                .algorithm(SignatureAlgorithm.HS256)
                .signWithSecret(secret);
    }
}
