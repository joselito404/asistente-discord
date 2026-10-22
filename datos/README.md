# 💾 Persistencia de Datos Versionada (`datos/`)

> **Propósito de la carpeta**: Almacén central de archivos JSON de datos estructurados versionados del bot. Contiene el estado persistente de subsistemas comunitarios, juegos y memorias de usuarios.
> **Quién puede escribir**: El bot en tiempo de ejecución (funciones de guardado automático en `modulos/`) y los agentes durante migraciones o calibraciones de catálogo.
> **Regla de origen**: Cumple con la Regla Global §8 (README por carpeta).

---

## 🗃️ Catálogo de Archivos JSON

| Archivo | Subsistema Responsable | Contenido y Esquema |
| :--- | :--- | :--- |
| `tribunal_data.json` | `modulos/juegos.py` | Catálogo de casos, argumentos de acusación/defensa y sentencias del minijuego `/tribunal`. |
| `trivia_data.json` | `modulos/juegos.py` | Banco estructurado de preguntas, opciones y respuestas por categorías (Gaming, Lore, Manhwas, etc.) para `/trivial`. |
| `user_memory.json` | `modulos/chat_ia.py` | Memoria a largo plazo por ID de usuario: obras favoritas, notas de contexto personal y puntos de trivial acumulados. |
| `economia.json` | `modulos/economia.py` | Estado financiero persistente: cuentas de usuarios (cash, bank, last_work, inventory, portfolio), bote acumulado del servidor (jackpot) y metadatos de moneda (Porro). |
| `sugerencias.json` | `modulos/sugerencias.py` | Historial de sugerencias de `#💡sugerencias💡`, IDs de mensaje, recuento de votos a favor/en contra y estado (aprobada/descartada). |
| `starboard.json` | `modulos/starboard.py` | Historial de portadas publicadas en `#⭐muro-de-la-fama⭐` (The Sanvi Daily). |
| `bolsa_mercado.json` | `modulos/bolsa_sanvi.py` | Estado de tickers cotizados (`$JOSE`, `$TERRE`, `$OMEN`, `$RACER`): total supply, amm_shares, holdings por usuario, libro de órdenes y timestamps. |
| `bolsa_pool.json` | `modulos/bolsa_sanvi.py` | Yield Pool semanal de dividendos (`accumulated_pool`, `total_distributed` y registro histórico de distribuciones). |
| `cakey_history.json` | `modulos/bolsa_sanvi.py` | Historial de snapshots diarios de actividad en Cakey Bot para el cómputo de Book Value y Earnings 30d (50/50). |

---

## 🚀 Archivos Planificados para Nuevos Sistemas

| Archivo Futuro | Sistema | Contenido Previsto |
| :--- | :--- | :--- |
| `bolsa_data.json` | Mercado de Valores ("Bolsa Sanvi") | Tickers de miembros (`$JOSE`, `$IVAN`), precios actuales, histórico de velas, carteras de acciones y saldo invertido. |
| `sugerencias_data.json` | Sugerencias 2.0 | Historial de sugerencias de `#💡sugerencias💡`, IDs de mensaje, recuento de votos a favor/en contra y estado (aprobada/descartada). |

---

## ⚠️ Reglas de Integridad
1. **Codificación UTF-8 Obligatoria**: Todo guardado o lectura debe usar explícitamente `encoding="utf-8"` e `indent=2`.
2. **Escritura Atómica / Segura**: Al guardar datos desde el bot, asegurar que no se produzcan bloqueos entre hilos (`threading.Lock` si aplica).
