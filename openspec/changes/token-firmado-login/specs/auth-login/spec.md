# Spec Delta

## Purpose

Define el contrato observable de `POST /auth/login` del servicio auth, que debe preservarse durante el cambio a token firmado, incluida la validación del campo `client`.

## ADDED Requirements

### Requirement: Login endpoint contract is preserved
El servicio SHALL exponer `POST /auth/login` con cuerpo JSON y `Content-Type: application/json`, sin requerir autenticación previa, y SHALL mantener los códigos de estado y la estructura de respuesta documentados en docs/ENDPOINTS.md.

#### Scenario: Valid credentials return the documented success structure
- **WHEN** un cliente envía `username`, `password` y `client` válidos de un usuario registrado
- **THEN** el servicio responde `200` con los campos `token`, `expiresIn` (3600), `user.username`, `user.displayName`, `user.role` y `debug` con valor `authenticated-with-legacy-flow`

#### Scenario: Request without a JSON body
- **WHEN** el cuerpo de la solicitud es `null`
- **THEN** el servicio responde `400` con `{"message": "Request is null"}`

### Requirement: Missing or blank credentials are rejected
El servicio SHALL responder `400` cuando `username` o `password` sean nulos, vacíos o compuestos solo de espacios, con el mensaje documentado para cada campo.

#### Scenario: Username is missing or blank
- **WHEN** el request no incluye `username`, o su valor es vacío o solo espacios
- **THEN** el servicio responde `400` con `{"message": "Username is required"}`

#### Scenario: Password is missing or blank
- **WHEN** el request no incluye `password`, o su valor es vacío o solo espacios
- **THEN** el servicio responde `400` con `{"message": "Password is required"}`

### Requirement: Invalid credentials are rejected without revealing the password
El servicio SHALL responder `401` cuando no exista coincidencia entre usuario y contraseña. El mensaje SHALL incluir el username recibido y no SHALL indicar si el fallo fue del usuario o de la contraseña.

#### Scenario: Unknown user or wrong password
- **WHEN** el username no existe o la contraseña no coincide con su hash
- **THEN** el servicio responde `401` con `{"message": "Invalid user <username> or password"}`

### Requirement: Client field is validated against an allowlist
El servicio SHALL validar el campo `client` del request contra una allowlist exacta. Un `client` ausente, vacío o fuera de la allowlist SHALL recibir `400` y no SHALL emitir token. La allowlist propuesta es `angular-workshop` y está pendiente de confirmación.

#### Scenario: Allowed client is accepted
- **WHEN** el request incluye credenciales válidas y `client` con valor `angular-workshop`
- **THEN** el servicio responde `200`

#### Scenario: Client outside the allowlist is rejected
- **WHEN** el request incluye credenciales válidas y un `client` que no está en la allowlist
- **THEN** el servicio responde `400`, indica que `client` no es válido y no emite token

#### Scenario: Client missing or blank is rejected
- **WHEN** el request incluye credenciales válidas y `client` está ausente, vacío o solo contiene espacios
- **THEN** el servicio responde `400` y no emite token

### Requirement: Unexpected failures return a generic error
El servicio SHALL responder `500` con `{"message": "Internal server error"}` ante una excepción no controlada. La respuesta SHALL NOT exponer el nombre de la excepción, mensajes internos, tokens ni secretos.

#### Scenario: Unhandled exception during login
- **WHEN** ocurre una excepción no controlada durante el login
- **THEN** el servicio responde `500` con `{"message": "Internal server error"}` y el cuerpo no contiene el nombre de la excepción ni valores sensibles
