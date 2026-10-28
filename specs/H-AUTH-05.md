# Spec H-AUTH-05: CORS permite orígenes mediante patrón amplio

Estado: APROBADO

## Fuente
H-AUTH-05 en [HALLAZGOS.md](../HALLAZGOS.md), severidad media, estado `Pendiente`. Aprobado en [PLAN.md](../PLAN.md).

## Contexto actual
[application.properties](../auth/src/main/resources/application.properties) define `quarkus.http.cors.origins=/.*/`, que acepta cualquier origen.

## Problema confirmado
Cualquier origen de navegador puede leer respuestas de `auth`. La autenticación no se ve afectada por CORS, pero la política es excesivamente permisiva.

## Comportamiento a preservar
- Métodos y headers requeridos por el contrato observado de `POST /auth/login`.
- Request, response y autorización del endpoint.
- El origen local de UI `http://localhost:4200` sigue funcionando.

## Alcance
- Reemplazar el patrón universal por una allowlist explícita, configurable por ambiente.

## Fuera de alcance
- Cambios en autenticación o en el contenido de las respuestas.
- Dependencias nuevas.
- Definición de orígenes de producción.

## Criterios de aceptación
1. Antes del cambio, una prueba de preflight con `Origin: http://localhost:4200` registra los headers CORS actuales.
2. Tras el cambio, `http://localhost:4200` recibe `Access-Control-Allow-Origin` con coincidencia exacta.
3. Un origen no permitido de prueba no recibe `Access-Control-Allow-Origin`.
4. Métodos y headers permitidos se mantienen.
5. La prueba no usa la respuesta permisiva actual como resultado esperado final.

## Contratos afectados/protegidos
- Política CORS del servicio `auth`. Request y response de `POST /auth/login` no cambian.

## Riesgos, supuestos y preguntas abiertas
- Pregunta abierta: ¿cuál es la allowlist de producción? Debe confirmarla el despliegue; no se inventa en esta spec.
- Riesgo: un origen de producción omitido bloqueará la UI desplegada.
- Supuesto: los orígenes de prueba son ficticios.
