# Spec Delta

## Purpose

Define el token de sesión emitido por el login de auth: claims obligatorios, coherencia con `expiresIn`, verificación de integridad y vigencia, y manejo de la clave de firma fuera del código fuente.

## ADDED Requirements

### Requirement: Issued token contains the required claims
El token devuelto en `token` SHALL contener los claims `sub`, `client`, `iat` y `exp`. `sub` SHALL identificar al usuario autenticado y `client` SHALL reflejar el valor validado del request.

#### Scenario: Token carries identity and client claims
- **WHEN** el login es exitoso con username `student` y client `angular-workshop`
- **THEN** al verificar el token, `sub` es `student`, `client` es `angular-workshop`, e `iat` y `exp` están presentes

### Requirement: Token has a verifiable signature
El token SHALL incluir una firma que el servicio puede verificar con la clave configurada. Un token cuya firma no coincida con su contenido SHALL ser rechazado por el verificador.

#### Scenario: Altered token is rejected
- **WHEN** se modifica cualquier parte del contenido de un token emitido, sin volver a firmarlo
- **THEN** el verificador rechaza el token

#### Scenario: Freshly issued token is accepted
- **WHEN** se verifica un token recién emitido por el login, sin modificar
- **THEN** el verificador lo acepta

### Requirement: expiresIn matches the token expiration
El valor `expiresIn` de la respuesta de login SHALL coincidir con `exp - iat` dentro de la tolerancia de 2 segundos propuesta y pendiente de confirmación. La respuesta SHALL mantener `expiresIn` igual a 3600.

#### Scenario: Expiration is consistent with expiresIn
- **WHEN** el login es exitoso
- **THEN** la diferencia entre `exp` e `iat` del token no excede la tolerancia respecto a `expiresIn` (3600)

### Requirement: Expired tokens are rejected
El verificador SHALL rechazar un token cuyo `exp` sea anterior al momento de verificación.

#### Scenario: Token past its expiration
- **WHEN** se verifica un token emitido cuyo `exp` ya pasó
- **THEN** el verificador rechaza el token

### Requirement: Signing key is external and never logged
La clave de firma SHALL leerse desde `AUTH_TOKEN_SECRET` o configuración externa equivalente. Fuera del perfil de laboratorio, el servicio SHALL NOT arrancar si la clave falta y SHALL NOT usar un valor por defecto. Ni el token ni la clave SHALL aparecer en logs.

#### Scenario: Missing key outside the lab profile
- **WHEN** el servicio arranca fuera del perfil de laboratorio sin `AUTH_TOKEN_SECRET`
- **THEN** el arranque falla y el servicio no atiende solicitudes de login

#### Scenario: Lab profile uses an isolated test value
- **WHEN** el servicio arranca en el perfil de laboratorio con un valor ficticio de prueba
- **THEN** el login funciona con ese valor y el valor no aparece en el código fuente

#### Scenario: Token and key are not logged
- **WHEN** se realiza un login exitoso y uno fallido
- **THEN** los logs generados no contienen el token emitido, la clave de firma ni la contraseña
