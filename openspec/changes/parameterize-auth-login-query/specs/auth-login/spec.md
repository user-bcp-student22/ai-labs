# Spec Delta

## Purpose

Defines the externally observable login behavior for valid workshop credentials and for credential values that attempt to bypass authentication.

## ADDED Requirements

### Requirement: Valid login preserves the successful response
The login endpoint MUST continue to authenticate the workshop user and return the established successful response fields.

#### Scenario: Workshop user logs in successfully
- **WHEN** `POST /auth/login` receives the valid credentials `student` and `Workshop123!`
- **THEN** the response status is 200
- **AND** the JSON response contains `user.username` equal to `student`
- **AND** the JSON response contains a non-empty `token`

### Requirement: Login rejects credential-based authentication bypass
The login endpoint MUST reject SQL-injection attempts in either credential and MUST NOT issue an authentication token for the attempt.

#### Scenario: SQL-injection attempt in username is rejected
- **WHEN** `POST /auth/login` receives `' OR '1'='1` as the username
- **THEN** the response status is 401
- **AND** the response does not contain a `token`

#### Scenario: SQL-injection attempt in password is rejected
- **WHEN** `POST /auth/login` receives `' OR '1'='1` as the password
- **THEN** the response status is 401
- **AND** the response does not contain a `token`