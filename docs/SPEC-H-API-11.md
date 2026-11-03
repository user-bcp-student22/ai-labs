# Validación de fortaleza de la clave JWT de la API

## Fuente

Hallazgo H-API-11, aprobado por el usuario para especificación.

Evidencia: `api/app/config.py:30-31` comprueba que `WORKSHOP_JWT_SECRET` no esté vacío, pero no aplica un mínimo de longitud o fortaleza.

Impacto: Una clave predecible podría facilitar la falsificación de tokens si se obtiene un JWT y se logra adivinar la clave. El riesgo depende del valor configurado.

## Contexto actual

La API requiere `WORKSHOP_JWT_SECRET` para iniciar. Los JWT se validan con HS256, emisor, audiencia y claims requeridos. Durante la transición también puede aceptarse el formato legacy cuando está configurado `WORKSHOP_LEGACY_TOKEN_SECRET`, según [ENDPOINTS.md](./ENDPOINTS.md#L29). El mínimo aprobado para la clave JWT es 32 bytes al codificarse como UTF-8; no se estima entropía.

## Problema confirmado

El arranque no rechaza una clave JWT menor de 32 bytes UTF-8 si no está vacía.

## Comportamiento a preservar

- La API no inicia si `WORKSHOP_JWT_SECRET` falta o está vacío.
- Los JWT válidos conservan el algoritmo, emisor, audiencia y claims requeridos documentados.
- Los tokens inválidos conservan la respuesta `401` con `{"detail":"Invalid token"}`.
- Esta especificación no cambia la aceptación del formato legacy cuando está habilitado.

## Alcance

- Aplicar el mínimo aprobado de 32 bytes UTF-8 para `WORKSHOP_JWT_SECRET`.
- Rechazar al iniciar la API las claves que no cumplan el criterio acordado.
- Validar la configuración con valores debajo, en y encima del umbral de 32 bytes UTF-8.

## Fuera de alcance

- Cambiar el algoritmo JWT, los claims o los formatos de respuesta.
- Rotar claves o cambiar la estrategia de distribución de secretos.
- Retirar el formato legacy.
- Modificar el servicio de autenticación u otros componentes.

## Criterios de aceptación

1. El arranque falla si `WORKSHOP_JWT_SECRET` falta o está vacío.
2. Una clave de menos de 32 bytes UTF-8 hace que el arranque falle con un error explícito de configuración.
3. Una clave de exactamente 32 bytes UTF-8 y una más larga permiten iniciar la API.
4. Las pruebas cubren valores debajo, en y encima del umbral de 32 bytes UTF-8.
5. Con una clave aceptada, se mantienen los contratos de validación JWT y la respuesta genérica para tokens inválidos.

## Contratos afectados/protegidos

- Interoperabilidad del JWT firmado por el servicio de autenticación con la API: HS256, emisor `workshop-auth`, audiencia `workshop-api` y claims requeridos, según [ENDPOINTS.md](./ENDPOINTS.md#L29).
- Formato de error `401` para autenticación inválida, descrito en [ENDPOINTS.md](./ENDPOINTS.md#L35).
- No se alteran endpoints ni formatos usados por los consumidores de la API.

## Riesgos, supuestos y preguntas abiertas

- Una validación más estricta puede impedir el arranque en entornos que actualmente usan claves débiles; los valores de cada entorno deben verificarse antes de aplicarla.
- El servicio de autenticación y la API deben acordar una política compatible para la clave compartida.
- Decisión aprobada: se mide la longitud en bytes UTF-8; no se estima entropía.
- No quedan preguntas abiertas dentro del alcance de esta spec.
