# Design

## Context

See [proposal.md](proposal.md) for the motivation and scope, and [specs/auth-login/spec.md](specs/auth-login/spec.md) for the observable requirements.

`auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java` currently builds the credential lookup by concatenating `username` and `password` into SQL and executes it with a `Statement`. `AuthResource.login` treats a missing user as unauthorized and creates a token only after a user is returned. The existing `AuthResourceTest` covers the successful `student` login and checks the username and token.

`docs/ENDPOINTS.md` explicitly has no auth section. For this change, the protected success behavior is therefore grounded in the existing auth test and Issue #23, as recorded in the proposal. Scope remains within `auth/`.

## Goals / Non-Goals

**Goals:**

- Make credential values data in the database lookup, so SQL syntax in either value cannot alter which user is authenticated.
- Preserve the current login endpoint, successful response, request validation, and unauthorized status behavior.
- Prove the existing success contract and the issue's rejection behavior with focused auth tests.

**Non-Goals:**

- Change token generation, token contents or lifetime, login response fields, or unrelated authentication behavior.
- Change the API or web components, introduce a persistence framework, or alter the database schema.
- Redesign authentication layering or update the broader endpoint documentation in this change.

## Protected Contracts

- Valid workshop credentials continue to make `POST /auth/login` return HTTP 200, `user.username` equal to `student`, and a non-empty `token`. Preserve the existing successful response shape beyond those required assertions.
- An SQL-injection attempt in either username or password returns HTTP 401 and does not issue a token.
- Existing request validation for null or blank credentials remains unchanged. The exact auth error bodies are not documented by `docs/ENDPOINTS.md` and are not expanded into new guarantees by this change.

## Components Affected

- `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java`: credential lookup boundary; this is the only production behavior expected to change.
- `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java`: contract boundary to keep stable; no response or token behavior change is intended.
- `auth/src/test/java/com/bcp/workshop/auth/AuthResourceTest.java`: characterization and regression coverage.
- No changes to `api/`, `web/`, or the existing sections of `docs/ENDPOINTS.md`.

## Decisions

### Bind credentials as SQL parameters

Use a JDBC `PreparedStatement` for the existing username-and-password lookup, binding both credential values while retaining the current query predicates and returned user fields. This directly prevents either input from being interpreted as SQL while keeping the persistence boundary and endpoint contract intact.

Alternatives considered:

- Escaping quotes or filtering suspicious characters was rejected because it is fragile, database-dependent, and can reject legitimate credentials without reliably preventing injection.
- Replacing the persistence layer or introducing an ORM was rejected because it expands the change beyond the identified root cause and adds migration and dependency risk.

### Keep endpoint and token behavior unchanged

Keep `AuthResource` as the owner of HTTP status and response construction, and leave token creation untouched. A lookup that finds no matching credentials continues through the existing unauthorized path; tests assert the required status and absence of a token, not an undocumented error-body format.

Alternatives considered:

- Refactoring login validation, response construction, or token handling was rejected as unrelated to Issue #23 and likely to broaden compatibility risk.
- Changing the unauthorized response body was rejected because neither the issue nor the auth spec requires a body change.

## Incremental Strategy and Tests

1. Before changing the credential lookup, retain and run the existing successful-login characterization: `student` / `Workshop123!` returns 200, the expected username, and a non-empty token. Add focused characterization for ordinary invalid credentials and the existing null/blank validation statuses if needed to protect those behaviors.
2. Add regression cases for the issue's SQL-like value in `username` and in `password`. Each must assert HTTP 401 and no token. Run these before the production change to establish that they detect the current defect; a failing injection case at this point is expected.
3. Change only the auth credential lookup to bind both values, then rerun the success, invalid-credential, validation, and injection cases.
4. Run the full auth test suite with Maven from `auth/`. Meet the repository's auth target of at least 85% coverage for modified code; do not suppress JaCoCo or security scanner findings.

## Risks / Trade-offs

- **The current unauthorized message includes the submitted username** -> Keep response-body changes out of scope and avoid asserting the message in the new regression tests; record any decision to remove that reflection as a separate security change.
- **Tests can accidentally depend on persisted SQLite state** -> Keep test data isolated using the auth test configuration and use the seeded workshop credentials for the compatibility case.
- **Changing more than value binding could alter login semantics** -> Keep the existing lookup predicates and verify both valid and invalid credential cases before merging.
- **The auth endpoint is absent from the endpoint baseline** -> The proposal records this gap; treat the issue and existing auth test as the contract sources for this narrowly scoped change, without editing the API sections of the general document.

## Rollback

No schema or data migration is planned, so there is no database rollback. Prefer fixing forward if a regression appears. Reverting the auth-only lookup change is technically small but restores the reported authentication-bypass risk; it should be an emergency measure only, with the login path kept unavailable until a corrected fix is applied.