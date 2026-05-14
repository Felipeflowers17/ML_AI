# PRD — Monitor de Licitaciones
### Guía de intención para reconstrucción con SDD + Engram + Agent Teams Lite

> No prescribe implementación. Define el problema, los principios de decisión y el criterio de éxito.

---

## El Problema

Los proveedores del Estado chileno enfrentan un problema de volumen: Mercado Público publica cientos o miles de licitaciones diarias. Revisarlas manualmente consume horas de trabajo, genera inconsistencias en la evaluación, y hace que oportunidades relevantes pasen desapercibidas.

**El dolor real es de atención, no de datos.** La información ya es pública y accesible vía API. Lo que falta es un filtro inteligente y configurable por el usuario que convierta el ruido en señal.

---

## Qué debe hacer la app

**Extraer → Evaluar → Clasificar → Gestionar.**

1. **Extraer** licitaciones desde `api.mercadopublico.cl` — automáticamente, bajo demanda por código específico y/o manual.
2. **Evaluar** cada licitación con un motor de scoring basado en reglas que el usuario configura: palabras clave con pesos diferenciados por campo (título, descripción, productos) más una valoración fija por organismo comprador.
3. **Clasificar** el resultado en un pipeline de tres etapas operativas: *Candidata → Seguimiento → Ofertada*. Las licitaciones que no superan el umbral de puntaje se ignoran y no ocupan espacio visual.
4. **Gestionar** el flujo: mover licitaciones entre etapas manualmente, consultar su ficha técnica completa con auditoría del puntaje, exportar datos a Excel o CSV.
5. **Automatizar** la extracción diaria con un piloto programable por hora, con reintentos automáticos si falla.

---

## Principios de Diseño

Cada principio resuelve un problema concreto y predecible dado el contexto de uso. No son preferencias estéticas.

**Separación estricta entre UI y lógica de negocio.**  
La UI nunca accede directamente a la base de datos. Las operaciones pesadas (extracción masiva, exportación) corren en hilos separados para no congelar la interfaz. Esta separación también hace que la lógica sea testeable de forma aislada, sin necesidad de levantar una ventana.

**El scoring debe ser recargable en caliente.**  
El usuario modifica sus reglas de negocio mientras la app está corriendo. La calculadora debe actualizarse sin reiniciar la aplicación y sin corromper evaluaciones que estén en curso en otro hilo. Cualquier mecanismo que garantice esto es válido; lo que no es negociable es el comportamiento.

**La extracción masiva debe asumir que la red falla.**  
La API de Mercado Público es una API gubernamental: tiene rate limits, devuelve errores 500 sin razón aparente y puede estar caída por mantenimiento. El flujo de extracción debe implementar pausas controladas entre peticiones y reintentos con backoff. No hacerlo hace la app inútil en uso real.

**UPSERT, no INSERT ciego.**  
Una misma licitación puede aparecer en múltiples extracciones (mismo día en días distintos, extracción manual más extracción masiva). El sistema siempre debe poder correr sobre datos existentes sin duplicar registros ni perder información. Si ya existe, actualiza; si no existe, crea.

**Fail-fast en configuración.**  
Si el usuario no tiene configuradas las credenciales (`DATABASE_URL`, `TICKET_MERCADO_PUBLICO`), la app debe decirlo inmediatamente al arrancar, no fallar silenciosamente en la primera extracción. El usuario necesita saber exactamente qué falta y dónde configurarlo.

**Sin magic strings ni magic numbers.**  
Las etapas del pipeline, los umbrales de puntaje y los estados de la API deben estar centralizados y nombrados. Facilita cambios futuros y elimina bugs por inconsistencias de texto.

**El setup inicial debe ser guiado.**  
Un usuario nuevo debe poder tener la app funcionando en menos de 5 minutos. Eso implica documentación de instalación clara y, si es posible, un script o flujo que maneje la primera ejecución: crear el entorno, verificar credenciales, correr migraciones, cargar el catálogo inicial de organismos compradores, etc.

---

## Modelo de Datos (Intención, no esquema)

Cuatro entidades centrales:

**Licitacion** — el registro principal. Tiene texto (título, descripción, listado de productos/ítems), fechas relevantes (publicación, cierre, adjudicación), un puntaje calculado automáticamente, una justificación auditable de ese puntaje (qué reglas aplicaron y cuánto sumaron), y una etapa dentro del pipeline.

**PalabraClave** — las reglas de negocio del usuario. Cada término tiene pesos distintos según dónde aparezca: el título es el filtro rápido de primera capa, la descripción y los productos son el filtro fino. Un mismo término puede sumar en un campo y no en otro.

**Organismo** — los compradores públicos. El usuario puede asignar un puntaje fijo a un organismo (positivo para clientes conocidos o deseables, negativo para organismos con historial problemático, neutral para los sin informacion para no perder oportunidades). Este puntaje se suma al score de cualquier licitación de ese organismo.

**EstadoLicitacion** — los estados que devuelve la API (Publicada, Cerrada, Adjudicada, etc.). Se almacenan para mostrarlos en la UI sin depender de que la API esté disponible al momento de consultar.

---

## Requisitos Funcionales Clave

- Las vistas de listado deben tener paginación. El volumen de licitaciones acumulado puede ser grande y cargar todo en memoria no es viable.
- Las vistas de listado deben tener búsqueda o filtro de texto. Sin esto, el usuario no puede encontrar una licitación específica sin scrollear.
- Debe existir un indicador visible de cuántas licitaciones hay en cada etapa del pipeline (candidatas, seguimiento, ofertadas).
- La ficha técnica de una licitación debe mostrar la justificación del puntaje de forma legible (qué palabras clave coincidieron y cuánto sumó cada una).
- El estado del piloto automático debe persistir entre reinicios de la app. Si el usuario lo configura para las 20:30, debe seguir así la próxima vez que abra la app.
- La exportación debe manejar volúmenes grandes sin consumo de RAM proporcional al tamaño del export (procesamiento por lotes).
- La aplicacion debe ser ligera, no debe consumir RAM ni recursos de manera descomunal para no forzar un desastre en el S.O de maquinas mas "humildes"

---

## Restricciones Reales

- La API de Mercado Público **requiere un ticket de autenticación** que el usuario debe obtener por su cuenta en el portal.
- La API **no tiene modo sandbox**. Los tests del cliente HTTP deben usar mocks, no peticiones reales.
- La app **es de escritorio, monousuario**. No es multi-tenant, no necesita autenticación interna ni expone una API propia.
- Los datos son **de solo lectura desde la API**. La app no crea ni modifica licitaciones en el sistema de Mercado Público, solo las consume, evalúa y clasifica localmente.
- Las credenciales nunca deben estar en el código fuente ni en el repositorio.

---

## Criterio de Éxito

La app funciona si un usuario puede:

1. Configurar sus credenciales y tener la base de datos lista en menos de 5 minutos siguiendo la documentación.
2. Definir sus palabras clave y ejecutar una extracción de una semana con mínima intervención activa.
3. Ver las licitaciones más relevantes ordenadas por puntaje, entender por qué cada una tiene ese puntaje, mover las que le interesan a Seguimiento (u Ofertadas o Candidatas.), y exportar el listado a Excel.
4. Dejar el piloto automático configurado, cerrar la app, volver al día siguiente y encontrar las licitaciones nuevas ya evaluadas y clasificadas.
5. Una interfaz de usuario que sea ordenada visualmente, separando las opciones en distintas pestañas intuitivas (una ventana por ejemplo para configurar palabras claves, otra para hacer las exportaciones, etc) y faciles de entender incluso si no se lee la documentacion.
6. Vamos a ocupar la API de 2 maneras. La primera hace una extraccion normal de las licitaciones publicadas (informacion limitada que muestra la API de muchas licitaciones) y puntua si corresponde. La segunda extraccion es del detalle de la licitacion. Si una licitacion en la primera extraccion su puntaje es mayor a 0, pasa a la segunda extraccion (detalle individual de la licitacion) y si vuelven haber coincidencia que merezcan puntaje en sus detalles se suman, se guardan y se muestran como corresponde.