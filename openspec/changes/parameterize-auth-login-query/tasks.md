# Tasks

Alcance: Issue #23 (H-AUTH-01), solo componente `auth/`. Las pruebas se ejecutan desde `auth/`; Git y OpenSpec desde la raíz de `ai-labs`.

## 1. Pruebas de caracterización (antes del cambio funcional)

- [x] 1.1 Ejecutar `mvn test` desde `auth/` sobre el código actual y verificar que `AuthResourceTest.logsInWithWorkshopUser` pasa (línea base: 200, `user.username` = `student`, `token` no vacío).
- [x] 1.2 Agregar en `AuthResourceTest` una prueba de credenciales inválidas normales (usuario válido con contraseña incorrecta) que verifique 401 y ausencia de `token`; verificar que pasa contra el código actual.
- [x] 1.3 Agregar en `AuthResourceTest` pruebas de validación existente (usuario y contraseña vacíos o nulos) que verifiquen solo el código de estado actual (400); verificar que pasan contra el código actual.

## 2. Pruebas de regresión del hallazgo (antes del cambio funcional)

- [x] 2.1 Agregar en `AuthResourceTest` una prueba con `' OR '1'='1` como contraseña (usuario `student`) que verifique 401 y ausencia de `token`; ejecutarla contra el código actual y registrar el resultado (se espera fallo, lo que confirma el defecto).
- [x] 2.2 Agregar en `AuthResourceTest` una prueba con `' OR '1'='1` como usuario que verifique 401 y ausencia de `token`; ejecutarla contra el código actual y registrar el resultado (puede pasar ya, por la precedencia de `AND`/`OR`; se conserva como regresión).
- [x] 2.3 Verificar que las pruebas nuevas no asertan el texto del mensaje de error ni dependen de datos persistidos fuera de los usuarios semilla.

## 3. Implementación incremental

- [x] 3.1 Cambiar solo `LegacyDatabase.findByCredentials` para usar `PreparedStatement` con parámetros para `username` y `password`, conservando la consulta, los campos devueltos y el manejo de resultado vacío; verificar que no queda concatenación de valores en el SQL.
- [x] 3.2 Ejecutar `mvn test` desde `auth/` y verificar que pasan las pruebas de las secciones 1 y 2, incluyendo las dos de inyección.
- [x] 3.3 Verificar con `git diff` desde la raíz que los únicos archivos modificados son `LegacyDatabase.java` y `AuthResourceTest.java` dentro de `auth/` (sin cambios en `AuthResource`, `LegacyTokenUtil`, `api/`, `web/` ni `docs/ENDPOINTS.md`).

## 4. Validación final

- [x] 4.1 Ejecutar `mvn verify` (o el comando de cobertura configurado) desde `auth/` y verificar cobertura del código modificado de 85% o superior, sin suprimir JaCoCo ni escáneres.
- [x] 4.2 Ejecutar `openspec validate parameterize-auth-login-query --type change` desde la raíz y verificar que no reporta incidencias.
- [x] 4.3 Contrastar cada escenario de `specs/auth-login/spec.md` con su prueba correspondiente y verificar que los tres escenarios (éxito, inyección en usuario, inyección en contraseña) están cubiertos.

## Workflow follow-up

- Revisión humana y pruebas reales antes de integrar.
- Archivar el cambio cuando se cumplan los requisitos de revisión del proyecto.
