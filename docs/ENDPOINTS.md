# Contratos HTTP

## auth

Base local: `http://localhost:8080` (`auth/src/main/resources/application.properties:1-3`; también indicado en `README.md`). El componente ofrece JSON en `POST /auth/login` y el endpoint de salud de Quarkus SmallRye Health en `GET /q/health` (`auth/pom.xml:40`). No se encontró un contrato acordado anterior; lo siguiente describe el comportamiento derivado del código y de la extensión declarada.

### GET /q/health

**1. Qué hace**

Permite al orquestador o a un cliente comprobar el estado de salud del servicio de autenticación.

**2. Autenticación**

El código de `auth/` no configura autenticación para este endpoint ni requiere un header `Authorization`. En configuración local, Quarkus escucha en `127.0.0.1`; en perfil de producción escucha en `0.0.0.0` (`auth/src/main/resources/application.properties:1-3`). Limita el acceso por red según el despliegue.

**3. Request**

No lleva cuerpo JSON ni requiere campos. La aplicación no declara headers específicos para la solicitud.

| campo | tipo | obligatorio | descripcion |
|---|---|---|---|
| — | — | no aplica | Solicitud GET sin cuerpo. |

Ejemplo de solicitud: `GET /q/health`, sin cuerpo.

**4. Response exitosa**

Estado observado en `AuthResourceTest`: `200 OK` cuando el estado agregado es `UP`. SmallRye Health genera esta respuesta; el repositorio no implementa un recurso propio ni checks de salud de auth.

| campo | tipo | descripcion |
|---|---|---|
| `status` | string | Estado agregado de salud. El valor esperado en éxito es `UP`. |
| `checks` | array | Checks que la extensión de salud incluye en el resultado. La aplicación auth no declara checks propios. |

Ejemplo de éxito observado por `AuthResourceTest.reportsHealthAsUpWithoutAuthentication` y `AuthResourceTest.reportsEmptyCheckListWhenNoHealthChecksAreConfigured`:

```json
{
  "status": "UP",
  "checks": []
}
```

**5. Respuestas de error**

El código de auth no define cuerpos de error para health. La comprobación local a `127.0.0.1:8080/q/health` no respondió dentro del timeout, por lo que no se verificó el comportamiento de la extensión ni hay un ejemplo de error observado que pueda documentarse sin asumirlo.

Pregunta abierta: verificar el estado HTTP y el cuerpo que produce SmallRye Health ante un check `DOWN` o un servicio no saludable. Un fallo de conexión al servicio no tiene respuesta HTTP del endpoint.

**6. Notas de seguridad**

En producción el listener se enlaza a `0.0.0.0` (`auth/src/main/resources/application.properties:3`). No se observó un mecanismo de autenticación para health ni una política de red en este componente; el despliegue debe restringir quién puede consultar el endpoint.

### POST /auth/login

**1. Qué hace**

Autentica a una persona con su nombre de usuario y contraseña y, si coinciden con un usuario registrado, devuelve los datos básicos de usuario y el token usado por el flujo del taller (`auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:24-49`).

**2. Autenticación**

No requiere autenticación previa ni header `Authorization`; es el endpoint de inicio de sesión. Envía el cuerpo como JSON con `Content-Type: application/json` (`auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:15-16`).

**3. Request**

Los campos y sus tipos Java se definen en `auth/src/main/java/com/bcp/workshop/auth/LoginRequest.java:3-6`; las validaciones de obligatoriedad están en `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:27-33`.

| campo | tipo | obligatorio | descripcion |
|---|---|---|---|
| `username` | string | sí | Usuario que se desea autenticar. No puede ser nulo, vacío ni contener solo espacios. |
| `password` | string | sí | Contraseña del usuario. No puede ser nula, vacía ni contener solo espacios. |
| `client` | string | no | Campo aceptado por el DTO; el recurso no lo valida ni lo usa para autenticar. |

Ejemplo JSON completo:

```json
{
  "username": "student",
  "password": "Workshop123!",
  "client": "angular-workshop"
}
```

El ejemplo usa el usuario ficticio que el componente siembra localmente (`auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:36`).

**4. Response exitosa**

Estado: `200 OK`.

| campo | tipo | descripcion |
|---|---|---|
| `token` | string | Token generado para el username y rol autenticados. |
| `expiresIn` | integer | Duración declarada por la respuesta en segundos: `3600`. |
| `user` | object | Datos básicos del usuario autenticado. |
| `user.username` | string | Nombre de usuario. |
| `user.displayName` | string | Nombre de presentación escapado con HTML4. |
| `user.role` | string | Rol almacenado para el usuario. |
| `debug` | string | Indicador fijo `authenticated-with-legacy-flow`. |

Ejemplo JSON completo con valores ficticios. El token es Base64 del formato observado en `LegacyTokenUtil`; su vencimiento es solo ilustrativo y no debe reutilizarse:

```json
{
  "token": "c3R1ZGVudHxTVFVERU5UfDE3OTMwNTQ5NDF8V09SS1NIT1BfU0VDUkVUXzIwMjY=",
  "expiresIn": 3600,
  "user": {
    "username": "student",
    "displayName": "Workshop Student",
    "role": "STUDENT"
  },
  "debug": "authenticated-with-legacy-flow"
}
```

La estructura de respuesta se arma en `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:39-49`. El formato de token se genera en `auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java:8-15`.

**5. Respuestas de error**

`400 Bad Request` — El cuerpo JSON representa `null`:

```json
{
  "message": "Request is null"
}
```

`400 Bad Request` — Falta `username`, es nulo, vacío o solo contiene espacios:

```json
{
  "message": "Username is required"
}
```

`400 Bad Request` — Falta `password`, es nula, vacía o solo contiene espacios:

```json
{
  "message": "Password is required"
}
```

`401 Unauthorized` — No existe una coincidencia de usuario y contraseña:

```json
{
  "message": "Invalid user student or password"
}
```

El mensaje incluye el username recibido (`auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:35-37`).

`500 Internal Server Error` — Una excepción no controlada alcanza el manejador del recurso. El cuerpo ya no expone mensaje ni clase de excepción:

```json
{
  "message": "Internal server error"
}
```

La respuesta y el registro en servidor están en `auth/src/main/java/com/bcp/workshop/auth/AuthResource.java:57-59`.

Pregunta abierta: un JSON malformado o incompatible puede ser rechazado por la capa REST/Jackson antes de invocar el recurso. El cuerpo exacto de ese error no está definido en `AuthResource` y no se caracterizó aquí; no asumir una forma estable para integraciones.

**6. Notas de seguridad**

- Las contraseñas nuevas se derivan con PBKDF2-HMAC-SHA256 y salt aleatorio; las filas antiguas en texto se migran al iniciar la base (`auth/src/main/java/com/bcp/workshop/auth/PasswordHasher.java:15-49`, `auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:31-38,67-85`).
- La consulta recupera por username con `PreparedStatement`; la contraseña se verifica contra el hash (`auth/src/main/java/com/bcp/workshop/auth/LegacyDatabase.java:25,89-105`).
- El token actual es Base64 de datos concatenados con un secreto fijo, no un token firmado. Aunque la respuesta declara `expiresIn: 3600` y el valor incluye una marca temporal, no se observó verificación criptográfica ni enforcement del vencimiento en este componente (`auth/src/main/java/com/bcp/workshop/auth/LegacyTokenUtil.java:8,13-15`). No lo trates como credencial firmada ni confíes en que expire efectivamente.
- CORS está habilitado con el patrón de origen `/.*/`; revisa el riesgo antes de exponer el servicio a navegadores de otros orígenes (`auth/src/main/resources/application.properties:4-7`).
