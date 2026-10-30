package com.bcp.workshop.auth;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Base64;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TokenIssuerTest {
    private static final String SECRET = "unit-test-only-secret-value-0123456789abcdef";
    private static final String OTHER_SECRET = "unit-test-other-secret-value-0123456789XYZ";
    private static final String CLIENT = "angular-workshop";
    private static final String SUBJECT = "student";
    private static final long ISSUED_AT = 1_800_000_000L;
    private static final int TTL_SECONDS = 3600;
    private static final int ONE_SECOND = 1;
    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final ObjectMapper JSON = new ObjectMapper();

    @Test
    void issuedTokenCarriesSubjectClientIssuedAtAndExpiration() throws Exception {
        JsonNode claims = payload(issuerAt(ISSUED_AT).issue(SUBJECT, CLIENT));

        assertEquals(SUBJECT, claims.get("sub").asText());
        assertEquals(CLIENT, claims.get("client").asText());
        assertEquals(ISSUED_AT, claims.get("iat").asLong());
        assertEquals(ISSUED_AT + TTL_SECONDS, claims.get("exp").asLong());
    }

    @Test
    void issuedTokenUsesHs256() throws Exception {
        String token = issuerAt(ISSUED_AT).issue(SUBJECT, CLIENT);

        assertEquals("HS256", header(token).get("alg").asText());
    }

    @Test
    void freshlyIssuedTokenHasVerifiableSignature() throws Exception {
        String token = issuerAt(ISSUED_AT).issue(SUBJECT, CLIENT);

        assertTrue(isAccepted(token, SECRET, ISSUED_AT));
    }

    @Test
    void alteredPayloadIsRejected() throws Exception {
        String token = issuerAt(ISSUED_AT).issue(SUBJECT, CLIENT);
        String[] parts = token.split("\\.");
        String forgedPayload = encode("{\"sub\":\"trainer\",\"client\":\"" + CLIENT
                + "\",\"iat\":" + ISSUED_AT + ",\"exp\":" + (ISSUED_AT + TTL_SECONDS) + "}");

        assertFalse(isAccepted(parts[0] + "." + forgedPayload + "." + parts[2], SECRET, ISSUED_AT));
    }

    @Test
    void tokenIsRejectedWhenVerifiedWithAnotherKey() throws Exception {
        String token = issuerAt(ISSUED_AT).issue(SUBJECT, CLIENT);

        assertFalse(isAccepted(token, OTHER_SECRET, ISSUED_AT));
    }

    @Test
    void expiresInMatchesExpMinusIat() throws Exception {
        TokenIssuer issuer = issuerAt(ISSUED_AT);
        JsonNode claims = payload(issuer.issue(SUBJECT, CLIENT));

        assertEquals(issuer.ttlSeconds(), claims.get("exp").asLong() - claims.get("iat").asLong());
        assertEquals(TTL_SECONDS, issuer.ttlSeconds());
    }

    @Test
    void tokenIsAcceptedJustBeforeExpiration() throws Exception {
        String token = issuerAt(ISSUED_AT).issue(SUBJECT, CLIENT);

        assertTrue(isAccepted(token, SECRET, ISSUED_AT + TTL_SECONDS - ONE_SECOND));
    }

    @Test
    void tokenPastExpirationIsRejected() throws Exception {
        String token = issuerAt(ISSUED_AT).issue(SUBJECT, CLIENT);

        assertFalse(isAccepted(token, SECRET, ISSUED_AT + TTL_SECONDS + ONE_SECOND));
    }

    private static TokenIssuer issuerAt(long epochSeconds) {
        Clock clock = Clock.fixed(Instant.ofEpochSecond(epochSeconds), ZoneOffset.UTC);
        return new TokenIssuer(clock, SECRET, TTL_SECONDS);
    }

    // Verificador independiente del emisor: recalcula HMAC-SHA256 y compara la expiracion.
    private static boolean isAccepted(String token, String secret, long nowEpochSeconds) throws Exception {
        return signatureMatches(token, secret) && payload(token).get("exp").asLong() > nowEpochSeconds;
    }

    private static boolean signatureMatches(String token, String secret) throws GeneralSecurityException {
        String[] parts = token.split("\\.");
        if (parts.length != 3) {
            return false;
        }
        Mac mac = Mac.getInstance(HMAC_ALGORITHM);
        mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), HMAC_ALGORITHM));
        byte[] expected = mac.doFinal((parts[0] + "." + parts[1]).getBytes(StandardCharsets.UTF_8));
        byte[] actual = Base64.getUrlDecoder().decode(parts[2]);
        return MessageDigest.isEqual(expected, actual);
    }

    private static JsonNode payload(String token) throws Exception {
        return JSON.readTree(Base64.getUrlDecoder().decode(token.split("\\.")[1]));
    }

    private static JsonNode header(String token) throws Exception {
        return JSON.readTree(Base64.getUrlDecoder().decode(token.split("\\.")[0]));
    }

    private static String encode(String json) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(json.getBytes(StandardCharsets.UTF_8));
    }
}
