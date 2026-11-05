# Proposal

## Why

GitHub Issue [#23](https://github.com/user-bcp-student22/ai-labs/issues/23) reports that crafted login credentials can alter authentication and allow an unauthorized login. Addressing this high-severity finding prevents credentials from bypassing the intended login check.

## What Changes

- **In scope:** Require crafted SQL-like values in either login credential to be rejected with HTTP 401 and without issuing a token.
- **Preserved behavior:** Valid workshop credentials continue to return HTTP 200 with `user.username` and a non-empty `token`.
- **Out of scope:** Changes to the successful response shape, token format or lifetime, API and web components, and unrelated authentication behavior.
- No breaking API change is intended.

### Contract baseline

`docs/ENDPOINTS.md` documents the `/api/*` endpoints and explicitly says that auth and web sections have not yet been added. It therefore does not define a baseline for `POST /auth/login`. This change does not alter the successful login behavior observed by `AuthResourceTest`; the observable expectations for that route come from the existing test and Issue #23. The issue adds rejection of SQL-injection attempts as a required security behavior, rather than changing the documented API contract. The general endpoint document remains untouched, including its existing API sections.

## Capabilities

### New Capabilities

- `auth-login`: Observable login success behavior and rejection of credential inputs that attempt to bypass authentication.

### Modified Capabilities

- None.

## Impact

- Component: `auth/` only.
- Endpoint: `POST /auth/login`.
- Behavior-level coverage: successful login response and unauthorized SQL-injection attempts.
- No dependencies or changes to `api/`, `web/`, or the general endpoint documentation are included.