package com.bcp.workshop.auth;

import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.apache.commons.text.StringEscapeUtils;
import org.jboss.logging.Logger;

import java.util.HashMap;
import java.util.Map;

@Path("/auth")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class AuthResource {
    private static final Logger LOGGER = Logger.getLogger(AuthResource.class);

    @Inject
    LoginService loginService;

    @Inject
    TokenIssuer tokenIssuer;

    @POST
    @Path("/login")
    public Response login(LoginRequest request) {
        try {
            UserRecord user = loginService.authenticate(request);
            return Response.ok(buildLoginResponse(request, user)).build();
        } catch (LoginRejectedException rejection) {
            return Response.status(rejection.status()).entity(Map.of("message", rejection.getMessage())).build();
        } catch (Exception error) {
            LOGGER.error("Login request failed", error);
            return Response.status(500).entity(Map.of("message", "Internal server error")).build();
        }
    }

    private Map<String, Object> buildLoginResponse(LoginRequest request, UserRecord user) {
        Map<String, Object> response = new HashMap<>();
        response.put("token", tokenIssuer.issue(user.username(), request.client));
        response.put("expiresIn", tokenIssuer.ttlSeconds());
        response.put("user", Map.of(
                "username", user.username(),
                "displayName", StringEscapeUtils.escapeHtml4(user.displayName()),
                "role", user.role()
        ));
        response.put("debug", "authenticated-with-legacy-flow");
        return response;
    }
}
