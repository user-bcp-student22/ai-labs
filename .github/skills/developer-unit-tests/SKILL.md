---
name: developer-unit-tests
description: "Crea o amplía pruebas unitarias como parte del trabajo del desarrollador. Úsalo para escribir pruebas unitarias, aplicar TDD, cubrir casos límite y verificar cobertura sin inventar requisitos."
---

# Skill: Developer Unit Tests

## 1) Metadata
- **Skill ID:** developer-unit-tests
- **Version:** 0.1.0
- **Purpose:** Guiar al desarrollador para crear pruebas unitarias confiables, trazables y coherentes con el comportamiento requerido y las convenciones del proyecto.
- **Audience (roles):** Desarrollador Backend, Desarrollador Frontend
- **When to use:** Al agregar o corregir pruebas unitarias para una funcionalidad, método, servicio, componente o módulo.
- **When NOT to use:** Para pruebas de integración o end-to-end, incidentes P1 de producción o tareas cuyo objetivo sea únicamente crear una estrategia de pruebas.
- **Sensitive inputs:** No incluyas secretos, credenciales ni datos reales. Usa los valores ficticios y aislados establecidos por el proyecto.
- **Expected output:** Pruebas unitarias creadas o actualizadas, ejecutadas con el comando correspondiente y un resumen conciso de los casos cubiertos y resultados.

## 2) Inputs
Usa la información disponible en la solicitud y el código. Cuando sea necesario, identifica:

- **Componente:** auth, api o web.
- **Objetivo de prueba:** comportamiento o requisito que debe verificarse.
- **Código bajo prueba:** archivo, símbolo o flujo indicado.
- **Restricciones:** contrato que se debe preservar, casos especiales o herramientas permitidas.
- **Comando de pruebas:** comando documentado para el componente, si se conoce.

Si falta un detalle que cambia el resultado esperado, consúltalo o regístralo como pendiente; no conviertas una suposición en requisito.

## 3) Procedure
1. Confirma el componente y el alcance. Si no se puede determinar qué componente corresponde, solicita aclaración antes de explorar código.
2. Lee las instrucciones aplicables y revisa el código bajo prueba, las pruebas existentes y sus patrones. Limita la exploración al componente acordado.
3. Traduce cada requisito explícito en uno o más casos observables. Separa los comportamientos confirmados de los detalles no especificados.
4. Crea primero la prueba que caracteriza el comportamiento solicitado. Si el encargo incluye implementar una funcionalidad o corregir un defecto, usa un ciclo rojo-verde-refactor: comprueba que la prueba falla por la razón esperada antes del cambio de producción.
5. Mantén las pruebas unitarias enfocadas en una unidad: sustituye dependencias externas usando los mecanismos y convenciones existentes; no conviertas la prueba en una prueba de integración.
6. Cubre, cuando aplique, el caso válido, entradas inválidas o límites relevantes y errores esperados. No agregues casos basados únicamente en comportamiento supuesto.
7. Usa datos de prueba deterministas, aísla el estado entre casos y limpia los recursos que la prueba cree.
8. Ejecuta las pruebas específicas y luego el comando documentado más pequeño que valide el cambio. Si corresponde al repositorio, desde la raíz puede usarse `python tools/lab.py test auth`, `python tools/lab.py test api` o `python tools/lab.py test web`, seleccionando solo el componente acordado.
9. Informa fallas reales sin ocultarlas. Si una prueba revela un defecto y no se pidió corregirlo, no cambies código de producción: documenta el resultado y solicita autorización para corregirlo.

## 4) Output
Entrega los cambios de pruebas y resume:

- Archivos de prueba agregados o modificados.
- Comportamientos y casos cubiertos.
- Comando exacto ejecutado y resultado.
- Cobertura obtenida, si el comando la reporta, y cualquier brecha relevante.
- Bloqueos, fallas o decisiones pendientes, sin presentarlos como exitosos.

## 5) Constraints
- No inventes requisitos ni afirmes que una conducta es esperada si no está especificada o caracterizada.
- Sigue el framework, estilo, fixtures, utilidades y comandos ya usados por el componente.
- No leas ni modifiques código de otros componentes sin ampliar el alcance acordado.
- No cambies código de producción salvo que la solicitud también pida implementar o corregir el comportamiento.
- No agregues dependencias, skips, exclusiones de cobertura, aserciones debilitadas ni supresión de hallazgos para hacer pasar las pruebas.
- No uses valores reales de producción, credenciales ni secretos.
- Conserva los contratos existentes. En auth, caracteriza el flujo antes de refactorizar persistencia o tokens; en api y web, conserva los endpoints y formatos requeridos por el componente.
- Aplica la meta de cobertura de al menos 85% al código modificado cuando corresponda a las instrucciones del componente. No declares cobertura que no haya sido medida.

## 6) Validation Rules
La entrega es válida si:
- Cada caso de prueba se vincula con un comportamiento requerido o existente claramente identificado.
- Las pruebas son unitarias, deterministas y ejecutables con las herramientas del proyecto.
- Las pruebas relevantes pasan; los fallos no resueltos se reportan explícitamente.
- Se informa el comando exacto y su resultado.
- La cobertura se reporta solo si fue medida y no se ocultan alertas ni se reducen los quality gates.

## 7) Evidence
Adjunta o referencia en la entrega:
- Archivos de pruebas unitarias agregados o actualizados.
- Salida del comando de pruebas ejecutado.
- Reporte de cobertura, si está disponible.
- Identificador del requisito o comportamiento probado, si el proyecto lo utiliza.
