"""
Módulo de Persistencia Distribuida de Datos en Discord (Render Cloud 24/7).
Especificación técnica: docs/PERSISTENCIA_DATOS.md
Permite la hidratación automática al iniciar (On-Ready Restore), respaldos cíclicos
cada 5 minutos y respaldos de última hora ante apagado controlado (SIGTERM/SIGINT).
"""

import os
import sys
import json
import time
import signal
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import discord
from discord.ext import tasks

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

GUILD_ID: int = 1446143936891715616
BACKUP_CHANNEL_NAME: str = "🔒backup-datos"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS_DIR = os.path.join(BASE_DIR, "datos")
ECONOMIA_PATH = os.path.join(DATOS_DIR, "economia.json")
USER_MEMORY_PATH = os.path.join(DATOS_DIR, "user_memory.json")
SUGGESTIONS_PATH = os.path.join(DATOS_DIR, "sugerencias.json")
STARBOARD_PATH = os.path.join(DATOS_DIR, "starboard.json")
BOLSA_MERCADO_PATH = os.path.join(DATOS_DIR, "bolsa_mercado.json")
BOLSA_POOL_PATH = os.path.join(DATOS_DIR, "bolsa_pool.json")
CAKEY_HISTORY_PATH = os.path.join(DATOS_DIR, "cakey_history.json")

# Control de cambios para evitar respaldos innecesarios idénticos
_LAST_BACKUP_MTIMES: Dict[str, float] = {}
_PERSISTENCE_LOOP_STARTED = False
_LOCK = asyncio.Lock()


def _log(msg: str):
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{timestamp}] [Persistencia] {msg}")


def safe_write_json(file_path: str, data: Any) -> None:
    """Escribe a un archivo temporal y reemplaza atómicamente con os.replace."""
    dir_name = os.path.dirname(file_path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
    tmp_path = f"{file_path}.tmp.{os.getpid()}_{threading.get_ident()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


async def _get_backup_channel(client: discord.Client, guild_id: int = GUILD_ID) -> Optional[discord.TextChannel]:
    """Localiza o crea el canal de backup privado en la categoría de Staff/Administración."""
    guild = client.get_guild(guild_id)
    if not guild:
        try:
            guild = await client.fetch_guild(guild_id)
        except Exception as e:
            _log(f"Error obteniendo guild {guild_id}: {e}")
            return None

    # 1. Buscar canal existente por nombre
    for ch in guild.text_channels:
        if ch.name in (BACKUP_CHANNEL_NAME, "backup-datos", "🔒backup-datos"):
            return ch

    # 2. Si no existe, intentar crearlo con permisos estrictos
    try:
        # Buscar categoría Staff / Administración
        target_category = None
        for cat in guild.categories:
            name_lower = cat.name.lower()
            if any(k in name_lower for k in ("staff", "admin", "administración", "administracion", "gestión", "gestion")):
                target_category = cat
                break

        # Permisos: oculto para @everyone, accesible solo para el bot y administradores
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False, read_messages=False),
        }
        me = guild.me or guild.get_member(client.user.id if client.user else 0)
        if me:
            overwrites[me] = discord.PermissionOverwrite(
                view_channel=True,
                read_messages=True,
                send_messages=True,
                attach_files=True,
                read_message_history=True,
            )

        new_ch = await guild.create_text_channel(
            BACKUP_CHANNEL_NAME,
            category=target_category,
            overwrites=overwrites,
            reason="Creación de canal de persistencia y backup 24/7 (Render Cloud)",
        )
        _log(f"Canal '{BACKUP_CHANNEL_NAME}' creado con éxito en #{new_ch.id}.")
        return new_ch
    except Exception as e:
        _log(f"Aviso no se pudo crear el canal de backup: {e}")
        return None


async def restore_from_discord(client: discord.Client, guild_id: int = GUILD_ID) -> dict:
    """
    Busca el canal '#🔒backup-datos', lee los últimos mensajes y descarga los archivos
    'economia.json' y/o 'user_memory.json' más recientes. Valida la sintaxis JSON
    y los sobrescribe atómicamente en disco.
    """
    channel = await _get_backup_channel(client, guild_id)
    if not channel:
        _log(f"No se encontró el canal de backup en guild {guild_id}. Se utilizarán los datos locales.")
        return {"restored": False, "files": [], "reason": "Canal no encontrado"}

    restored_files: List[str] = []
    target_files = {
        "economia.json": ECONOMIA_PATH,
        "user_memory.json": USER_MEMORY_PATH,
        "sugerencias.json": SUGGESTIONS_PATH,
        "starboard.json": STARBOARD_PATH,
        "bolsa_mercado.json": BOLSA_MERCADO_PATH,
        "bolsa_pool.json": BOLSA_POOL_PATH,
        "cakey_history.json": CAKEY_HISTORY_PATH,
    }
    found_targets = set()

    try:
        async for message in channel.history(limit=10):
            if not message.attachments:
                continue
            for att in message.attachments:
                fname = att.filename.lower()
                if fname in target_files and fname not in found_targets:
                    dest_path = target_files[fname]
                    try:
                        content_bytes = await att.read()
                        # Validar sintaxis JSON estricta
                        parsed_json = json.loads(content_bytes.decode("utf-8"))
                        # Guardar atómicamente
                        safe_write_json(dest_path, parsed_json)
                        found_targets.add(fname)
                        restored_files.append(fname)
                        _log(f"✅ Archivo '{fname}' restaurado con éxito desde Discord ({len(content_bytes)} bytes).")

                        # Sincronizar en memoria si los módulos correspondientes están cargados
                        if fname == "economia.json":
                            try:
                                import modulos.economia_core as eco_core
                                eco_core.load_economy_data(force_reload=True)
                            except Exception as e_eco:
                                _log(f"Aviso recargando economía en memoria: {e_eco}")
                        elif fname == "user_memory.json":
                            try:
                                import modulos.chat_ia as chat_mod
                                if hasattr(chat_mod, "user_memory") and isinstance(chat_mod.user_memory, dict):
                                    chat_mod.user_memory.clear()
                                    chat_mod.user_memory.update(parsed_json)
                            except Exception as e_mem:
                                _log(f"Aviso recargando user_memory en memoria: {e_mem}")

                    except json.JSONDecodeError as e_json:
                        _log(f"⚠️ Error de sintaxis en backup de '{fname}': {e_json}. Se descarta este adjunto.")
                    except Exception as e_download:
                        _log(f"⚠️ Error descargando/escribiendo '{fname}': {e_download}")

            # Si ya recuperamos ambos archivos, detenemos la búsqueda
            if len(found_targets) >= len(target_files):
                break

    except Exception as e_hist:
        _log(f"Error consultando historial de #{channel.name}: {e_hist}")

    is_restored = len(restored_files) > 0
    if is_restored:
        _log(f"🎉 Restauración completada: {restored_files}.")
    else:
        _log("ℹ️ No se encontraron copias previas de datos en Discord. Se inicia con los datos locales versionados.")

    return {"restored": is_restored, "files": restored_files}


async def backup_to_discord(client: discord.Client, guild_id: int = GUILD_ID, reason: str = "periodico") -> bool:
    """
    Envía 'datos/economia.json' y 'datos/user_memory.json' como discord.File a '#🔒backup-datos'
    con un embed estructurado indicando la razón, timestamp y tamaños.
    """
    async with _LOCK:
        channel = await _get_backup_channel(client, guild_id)
        if not channel:
            _log(f"No se pudo acceder a #{BACKUP_CHANNEL_NAME} para realizar el backup.")
            return False

        # Forzar sincronización de buffers en memoria hacia disco antes del volcado
        try:
            import modulos.economia_core as eco_core
            eco_core.save_economy_data()
        except Exception:
            pass

        try:
            import modulos.chat_ia as chat_mod
            if hasattr(chat_mod, "user_memory") and hasattr(chat_mod, "save_user_memory"):
                chat_mod.save_user_memory(chat_mod.user_memory)
        except Exception:
            pass

        files_to_send: List[discord.File] = []
        files_info: List[str] = []
        now_utc = datetime.now(timezone.utc)

        for fname, fpath in [
            ("economia.json", ECONOMIA_PATH),
            ("user_memory.json", USER_MEMORY_PATH),
            ("sugerencias.json", SUGGESTIONS_PATH),
            ("starboard.json", STARBOARD_PATH),
            ("bolsa_mercado.json", BOLSA_MERCADO_PATH),
            ("bolsa_pool.json", BOLSA_POOL_PATH),
            ("cakey_history.json", CAKEY_HISTORY_PATH),
        ]:
            if os.path.exists(fpath):
                size_bytes = os.path.getsize(fpath)
                mtime = os.path.getmtime(fpath)
                _LAST_BACKUP_MTIMES[fname] = mtime
                files_to_send.append(discord.File(fpath, filename=fname))
                files_info.append(f"• `{fname}`: **{size_bytes:,} bytes** (~{size_bytes / 1024:.1f} KB)")
            else:
                files_info.append(f"• `{fname}`: *(No encontrado en disco)*")

        if not files_to_send:
            _log("Aviso: no hay archivos locales para respaldar.")
            return False

        color = 0x2ECC71 if reason != "cierre_controlado_sigterm" else 0xE74C3C
        title_prefix = "📦 Respaldo Periódico" if reason == "periodico" else f"🛑 Respaldo ({reason})"
        embed = discord.Embed(
            title=f"{title_prefix} • Antigravity 24/7",
            description="Copia de seguridad atómica de persistencia en Discord.",
            color=color,
            timestamp=now_utc,
        )
        embed.add_field(name="Razón", value=f"`{reason}`", inline=True)
        embed.add_field(name="Fecha / Hora (UTC)", value=now_utc.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=True)
        embed.add_field(name="Archivos Incluidos", value="\n".join(files_info), inline=False)
        embed.set_footer(text="Render Cloud Free Tier • Persistencia Garantizada")

        try:
            await channel.send(embed=embed, files=files_to_send)
            _log(f"Backup enviado con éxito a #{channel.name} [Razón: {reason}].")
            return True
        except Exception as e:
            _log(f"Error subiendo backup a #{channel.name}: {e}")
            return False
        finally:
            for f in files_to_send:
                try:
                    f.close()
                except Exception:
                    pass


def _has_data_mutated() -> bool:
    """Comprueba si alguno de los archivos clave fue modificado desde el último backup."""
    for fname, fpath in [
            ("economia.json", ECONOMIA_PATH),
            ("user_memory.json", USER_MEMORY_PATH),
            ("sugerencias.json", SUGGESTIONS_PATH),
            ("starboard.json", STARBOARD_PATH),
            ("bolsa_mercado.json", BOLSA_MERCADO_PATH),
            ("bolsa_pool.json", BOLSA_POOL_PATH),
            ("cakey_history.json", CAKEY_HISTORY_PATH),
        ]:
        if os.path.exists(fpath):
            current_mtime = os.path.getmtime(fpath)
            last_mtime = _LAST_BACKUP_MTIMES.get(fname, 0.0)
            if current_mtime > last_mtime:
                return True
    return False


def setup_persistence(bot: discord.Client, guild_id: int = GUILD_ID):
    """
    Configura el ciclo de persistencia de datos:
    a) Tarea loop cada 5 minutos (discord.ext.tasks).
    b) Interceptores de señales SIGTERM / SIGINT para forzar backup antes del apagado de Render.
    """
    global _PERSISTENCE_LOOP_STARTED
    if _PERSISTENCE_LOOP_STARTED:
        return
    _PERSISTENCE_LOOP_STARTED = True

    # 1. Bucle cíclico de 5 minutos
    @tasks.loop(minutes=5.0)
    async def _persistence_periodic_task():
        # Respaldar si los archivos mutaron o si es la primera comprobación
        if _has_data_mutated() or not _LAST_BACKUP_MTIMES:
            _log("Detectadas modificaciones en datos locales. Iniciando backup cíclico...")
            await backup_to_discord(bot, guild_id=guild_id, reason="periodico_5min")

    @_persistence_periodic_task.before_loop
    async def _before_persistence_loop():
        await bot.wait_until_ready()
        await asyncio.sleep(10.0)  # Breve margen tras on_ready

    try:
        _persistence_periodic_task.start()
        _log("Bucle de persistencia periódico (5 min) configurado y arrancado.")
    except RuntimeError:
        # Si no hay running event loop en este hilo (por ejemplo en tests unitarios o antes de bot.run),
        # se evita la excepción no controlada
        _log("Aviso: no hay event loop en ejecución activa; la tarea periódica arrancará con el bot.")

    # 2. Manejador de señales de apagado (SIGTERM / SIGINT)
    def _shutdown_signal_handler(sig_num, frame):
        sig_name = "SIGTERM" if sig_num == getattr(signal, "SIGTERM", 15) else "SIGINT"
        _log(f"🛑 Señal {sig_name} recibida. Forzando guardado de buffers y backup de cierre...")

        # Forzar volcado síncrono en disco primero
        try:
            import modulos.economia_core as eco_core
            eco_core.save_economy_data()
        except Exception:
            pass
        try:
            import modulos.chat_ia as chat_mod
            if hasattr(chat_mod, "user_memory") and hasattr(chat_mod, "save_user_memory"):
                chat_mod.save_user_memory(chat_mod.user_memory)
        except Exception:
            pass

        # Si el loop de asyncio sigue activo, programar y esperar el backup
        try:
            if bot.loop and bot.loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    backup_to_discord(bot, guild_id=guild_id, reason=f"cierre_controlado_{sig_name.lower()}"),
                    bot.loop,
                )
                try:
                    future.result(timeout=12.0)
                    _log("Backup de cierre completado con éxito antes de salir.")
                except Exception as e_fut:
                    _log(f"Aviso en backup de cierre: {e_fut}")
        except Exception as e_sig:
            _log(f"Error procesando apagado en señal: {e_sig}")

        # Salir limpiamente
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, _shutdown_signal_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _shutdown_signal_handler)
        _log("Manejadores de señales SIGINT y SIGTERM registrados.")
    except Exception as e_sig_reg:
        _log(f"Aviso registrando manejadores de señales: {e_sig_reg}")
