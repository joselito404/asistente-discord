---
name: revision-reglas
version: 1.0.0
status: confirmada
updated_at: 2026-10-19
description: >-
  [Confirmada · Jose · 19/10/2026] (Origen: Antigravity-discord / Chat 3)
  Procedimiento estandarizado y triaje técnico para auditar, sanear y mantener las reglas locales
  (reglas.md o .agents/rules/) en cualquier proyecto del ecosistema Antigravity.
  Activar cuando el usuario pida 'revisar reglas', 'auditar normas', 'limpiar reglas.md',
  'sanear .agents/rules/', o al iniciar la auditoría de un proyecto nuevo o hito mayor.
---

# Skill Maestra: Revisión Estandarizada de Reglas (`revision-reglas`)

> **Estado:** `[Confirmada · Jose · 19/10/2026]` (Origen: Antigravity-discord / Chat 3)
> **Versión Oficial:** `1.0.0`
> **Ámbito de Aplicación:** Todos los proyectos del ecosistema (`Antigravity-*`), compatible tanto con arquitectura modular nativa (`.agents/rules/`) como con formato monolítico (`reglas.md`).
> **Propósito:** Estandarizar las sesiones de revisión de reglas, erradicar resúmenes superficiales, forzar criterio técnico riguroso de co-trabajador (§16), blindar presupuestos de tokens/bytes (§7) y garantizar persistencia en caliente (§13).

---

## 🛑 Protocolo Operativo en 6 Pasos

Toda sesión de revisión, auditoría o actualización de reglas locales de un proyecto debe ejecutar obligatoriamente esta secuencia estructurada:

### Paso 1: Triaje y Priorización por Criticidad (Prohibido el Orden Plano)
Queda terminantemente prohibido revisar reglas en orden numérico plano (1, 2, 3...) sin análisis de riesgo. El asistente debe clasificar y presentar las reglas agrupadas en 3 niveles de severidad:
1. **🔴 Nivel 1: Crítico (Seguridad, Integridad y Supervivencia):**
   - Protección de credenciales, secretos y archivos sensibles (ej. `.gitignore`, variables de entorno, claves de API).
   - Veto absoluto a acciones destructivas o irreversibles (ej. purgas masivas de bases de datos, expulsión de usuarios, sobrescrituras sin respaldo).
   - Disponibilidad del sistema y prevención de caídas críticas (ej. procesos persistentes, reconexión de sockets, servidores de health-check, gestión de puertos).
2. **🟡 Nivel 2: Operativo y Costes (Rendimiento, APIs y Negocio):**
   - Control de consumo y costes de APIs externas o LLMs (ej. cuotas gratuitas vs facturación, Circuit Breakers ante errores HTTP 429/503).
   - Lógica central de arquitectura, dependencias y flujos principales de ejecución.
   - Sincronización de estado, control de concurrencia y persistencia transaccional (ej. bloqueos atómicos, integridad de archivos de datos).
3. **🟢 Nivel 3: Higiene y Gobernanza (Mantenimiento y Estándares):**
   - Estructura física de carpetas y blindaje de la raíz (Regla Global §8).
   - Documentación viva y fuentes de verdad del proyecto (ej. esquemas de datos, catálogos de componentes, índices de recursos).

---

### Paso 2: Diagnóstico Técnico Obligatorio con Dictamen
Por cada regla analizada, el asistente tiene el deber (Regla Global §16) de contrastar el texto contra el código real y emitir un dictamen técnico explícito:
- **`[Vigente]`**: Alineada al 100% con la implementación actual, necesaria y funcionalmente activa.
- **`[Desfasada]`**: Cita funciones, rutas, scripts, modelos de IA o dependencias que ya no existen o han cambiado en el código. Obligatorio formular la propuesta exacta de actualización.
- **`[Redundante]`**: Repite o parafrasea lo que ya prescriben las Reglas Globales (§1 a §17 de `AGENTS.md`). Obligatorio proponer su poda inmediata.

---

### Paso 3: Verificación de Presupuestos, Telemetría y Deuda Legacy (Regla Global §7)
1. **Proyectos con Constitución Modular (`.agents/rules/`):**
   - **Límite por Archivo (Tope 24.000 bytes):** Verificar que ningún módulo individual supere los 20 KB (~20.480 bytes) para mantener margen de seguridad frente al truncado estricto del inyector en 24.000 bytes.
   - **Presupuesto Agregado Dedicado (20.000 tokens):** Comprobar que la suma de reglas inyectadas no desborde la barra azul de *Customizations*.
   - **Estrategia de Triggers:** Asignar `trigger: always_on` a módulos críticos (Nivel 1 y Nivel 2 indispensable) y `trigger: model_decision` con descripción precisa a normas situacionales o secundarias para permitir degradación elegante (*graceful demotion*) y consumo bajo demanda.
2. **Proyectos con Monolito Legacy (`reglas.md`):**
   - Si el archivo monolítico `reglas.md` supera los 15-20 KB o abarca más de 3 dominios técnicos disjuntos, el asistente debe prescribir proactivamente a Jose la migración a la Constitución Modular nativa (`.agents/rules/*.md`), evitando el riesgo inminente de truncado silencioso.

---

### Paso 4: Veto a la Redundancia Global (Poda Activa)
- Las reglas de proyecto existen exclusivamente para la operativa local específica del repositorio.
- Todo texto que duplique normas globales de comunicación (§1), rotación de hardware AM4/AM5 (§2-§3), MCPs en la nube (§5), Git y GitHub privado (§11), o persistencia en caliente (§13) debe podarse de las reglas locales. Las reglas globales ya prevalecen por diseño y duplicarlas genera fricción de mantenimiento.

---

### Paso 5: Persistencia en Caliente y Trazabilidad Turno a Turno (Regla Global §13)
- **Veto al Asentimiento Verbal:** Queda terminantemente prohibido que el asistente responda «Aprobado», «Anotado», «Queda fijado» o pase a debatir el siguiente punto si en ese **mismo turno no ha ejecutado físicamente la herramienta de edición** (`replace_file_content` o `write_to_file`).
- Tras cada consenso con Jose, editar físicamente el archivo (`reglas.md` o `.agents/rules/<modulo>.md`) aplicando las etiquetas de autoría:
  - `[Confirmada · Jose · fecha]`
  - `[Propuesta · Proyecto / Chat nº · fecha]` (en ámbito global) o `[Propuesta · Chat nº · fecha]` (en proyectos locales)
  - `[Pendiente de matizar: <fleco>]`
- Aportar obligatoriamente en la respuesta el enlace clicable comprobable al archivo y rango de líneas editadas.

---

### Paso 6: Cierre, Relevo y Commit Semántico (Reglas Globales §4, §11 y §13)
Ninguna sesión de auditoría de reglas se da por concluida sin completar este ciclo:
1. **Actualización de Índices:** Actualizar el `README.md` de la carpeta de reglas (`.agents/rules/README.md`) reflejando el estado y la versión de cada módulo.
2. **Registro de Relevo:** Consolidar el resumen de la auditoría en `.agents/chats/resumen.md` y respaldar la transcripción íntegra en `.agents/chats/raw/`.
3. **Commit y Push Semántico:** Ejecutar commit atómico con mensaje convencional (ej. `docs(rules): auditoría y saneamiento según revision-reglas v1.0.0`) y enviar los cambios a la rama privada en GitHub (`git push`).

---

## 📋 Plantilla Maestra de Informe de Revisión

Al ejecutar esta skill, el asistente presentará los hallazgos siguiendo estrictamente esta estructura:

```markdown
### 🔴 Nivel 1: Crítico (Seguridad, Integridad y Supervivencia)
- **Regla [Nombre / Sección]**: `[Vigente]` / `[Desfasada]` / `[Redundante]`
  - *Diagnóstico:* [Hecho técnico comprobado contra el código]
  - *Acción recomendada:* [Mantener / Actualizar texto / Podar]

### 🟡 Nivel 2: Operativo y Costes (Rendimiento, APIs y Negocio)
- **Regla [Nombre / Sección]**: `[Vigente]` / `[Desfasada]` / `[Redundante]`
  - *Diagnóstico:* [...]
  - *Acción recomendada:* [...]

### 🟢 Nivel 3: Higiene y Gobernanza (Mantenimiento y Estándares)
- **Regla [Nombre / Sección]**: `[Vigente]` / `[Desfasada]` / `[Redundante]`
  - *Diagnóstico:* [...]
  - *Acción recomendada:* [...]

### 📊 Auditoría de Presupuestos y Bytes
- Total archivos en `.agents/rules/`: X módulos.
- Archivo de mayor peso: `<modulo>.md` (X bytes / < 20 KB ✅).
- Consumo estimado de tokens: ~X tokens / 20.000 tokens de presupuesto dedicado.
```
