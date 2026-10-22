"""
Módulo de Tienda, Inventario y Buffs para 'Asistente':
- Catálogo oficial SHOP_ITEMS (roles permanentes, pases temporales XP y consumibles como Monster Blanco).
- Compras (/tienda), inventario (/inventario), consumo (/usar) y transferencias (/regalar).
- Watcher y chequeo de expiración de buffs temporales (check_and_expire_buffs).
"""

import os
import sys
import json
import random
import asyncio
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union, Set

import discord

from modulos.economia_core import (
    BASE_DIR,
    ECONOMY_DATA_PATH,
    PORRO_EMOJI,
    ECONOMY_LOCK,
    _bot_log,
    _bs,
    load_economy_data,
    save_economy_data,
    ensure_user,
    get_user_economy,
    get_balance,
    modify_balance,
    user_has_shield,
    is_economy_halted,
    get_economy_halt_reason,
)

# Catálogo Oficial de la Tienda (9 Ítems)
SHOP_ITEMS: Dict[str, Dict[str, Any]] = {
    "cartera_blindada": {
        "id": "cartera_blindada",
        "name": "🛡️ Cartera Blindada",
        "price": 50000,
        "type": "role",
        "role_id": "1549520453926912062",
        "role_name": "🛡️ Cartera Blindada",
        "description": "Otorga inmunidad total contra el comando /robar. Si alguien intenta robarte, el atraco falla al 100% y te paga una multa del 15%.",
        "unique": True,
    },
    "porro_oro": {
        "id": "porro_oro",
        "name": "🚬 Porro de Oro",
        "price": 75000,
        "type": "item",
        "description": "Coleccionable de inventario de máximo prestigio y flexeo. Demuestra quién manda en la economía.",
        "unique": False,
    },
    "camello_barrio": {
        "id": "camello_barrio",
        "name": "🚬 Camello del Barrio",
        "price": 85000,
        "type": "role",
        "role_id": "1549805021153984617",
        "role_name": "🚬 Camello del Barrio",
        "description": "Rol cosmético exclusivo de Discord en verde porro (#2ECC71).",
        "unique": True,
    },
    "ludopata_rehabilitado": {
        "id": "ludopata_rehabilitado",
        "name": "🎰 Ludópata Rehabilitado",
        "price": 40000,
        "type": "role",
        "role_id": "1549805313920864429",
        "role_name": "🎰 Ludópata Rehabilitado",
        "description": "Rol cosmético exclusivo de Discord en rojo casino (#E74C3C).",
        "unique": True,
    },
    "monster_blanco": {
        "id": "monster_blanco",
        "name": "🥤 Monster Blanco",
        "price": 25000,
        "type": "consumable",
        "description": "Bebida energética suprema. Al usarla con /usar resetea al instante tus cooldowns de /trabajar, /crimen y /robar.",
        "unique": False,
    },
    "chute_xp": {
        "id": "chute_xp",
        "name": "⚡ Chute de XP (24h)",
        "price": 15000,
        "type": "role",
        "role_id": "1549880939205623972",
        "role_name": "⚡ Chute de XP (24h)",
        "duration_hours": 24,
        "description": "Pase temporal con boost de +5% de XP en Cakey Bot durante 24 horas (se guarda en /inventario y se activa con /usar).",
        "unique": False,
    },
    "pase_semanal_xp": {
        "id": "pase_semanal_xp",
        "name": "🔥 Pase Semanal de XP",
        "price": 75000,
        "type": "role",
        "role_id": "1549880941466357940",
        "role_name": "🔥 Pase Semanal de XP",
        "duration_hours": 168,
        "description": "Pase temporal con boost de +10% de XP en Cakey Bot durante 7 días (se guarda en /inventario y se activa con /usar).",
        "unique": False,
    },
    "pase_mensual_xp": {
        "id": "pase_mensual_xp",
        "name": "💠 Pase Mensual de XP",
        "price": 250000,
        "type": "role",
        "role_id": "1549880942909329539",
        "role_name": "💠 Pase Mensual de XP",
        "duration_hours": 720,
        "description": "Pase temporal con boost de +15% de XP en Cakey Bot durante 30 días (se guarda en /inventario y se activa con /usar).",
        "unique": False,
    },
    "aura_xp": {
        "id": "aura_xp",
        "name": "👑 Aura de XP Permanente",
        "price": 1000000,
        "type": "role",
        "role_id": "1549880944490582106",
        "role_name": "👑 Aura de XP Permanente",
        "description": "Pase perpetuo de máxima élite con boost de +10% de XP permanente e inmarchitable.",
        "unique": True,
    },
}

# Tabla de Salarios Diarios Base por Rol de Nivel y Podio (UnbelievaBoat Role Income)


# ==========================================
# TIENDA OFICIAL V2 (9 ARTÍCULOS)
# ==========================================

def get_shop_catalog() -> Dict[str, Dict[str, Any]]:
    """Devuelve el catálogo maestro de 9 ítems de la tienda."""
    return SHOP_ITEMS


def buy_shop_item(
    user_id: Any,
    item_key: str,
    member: Optional[Any] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]], Dict[str, int]]:
    """Compra un artículo de la tienda y añade el rol si procede."""
    uid = str(user_id)
    if is_economy_halted():
        r = get_economy_halt_reason()
        reason_str = f" Motivo: {r}" if r else ""
        return False, f"⛔ La tienda está temporalmente pausada por administración.{reason_str}", None, get_balance(uid)

    item_key_clean = item_key.strip().lower()

    # Mapeo flexible de identificadores
    matched_item = None
    for k, it in SHOP_ITEMS.items():
        if k == item_key_clean or it["name"].lower() == item_key_clean or k in item_key_clean:
            matched_item = it
            break

    if not matched_item:
        return False, f"❌ El artículo '{item_key}' no existe en el catálogo de la tienda.", None, get_balance(uid)

    item_id = matched_item["id"]
    item_name = matched_item["name"]
    price = matched_item["price"]

    with ECONOMY_LOCK:
        user_data = ensure_user(uid)
        inv = user_data.setdefault("inventory", [])
        bal = get_balance(uid)

        # Chequeo de posesión única
        if matched_item.get("unique", False):
            if item_name in inv or (matched_item["type"] == "role" and user_has_shield(uid, member) and item_id == "cartera_blindada"):
                return False, f"❌ Ya posees **{item_name}**. Este artículo no es acumulable.", matched_item, bal

        if bal["cash"] < price:
            return (
                False,
                f"❌ No tienes suficientes Porros en efectivo ({PORRO_EMOJI}) para comprar **{item_name}**.\n"
                f"Precio: **{price:,}** Porros | Saldo en efectivo: **{bal['cash']:,}** Porros.\n"
                f"💡 Si tienes saldo en el banco, usa `/retirar`.",
                matched_item,
                bal,
            )

        # Deducir precio y añadir al inventario
        new_bal = modify_balance(uid, cash_delta=-price)
        data = load_economy_data()
        data["users"][uid].setdefault("inventory", []).append(item_name)
        save_economy_data(data)

        _bot_log(f"🛒 [Tienda] {uid} compró '{item_name}' por {price:,} Porros.")
        return True, f"✅ ¡Has adquirido **{item_name}** por {PORRO_EMOJI} **{price:,}** Porros!", matched_item, new_bal


def build_shop_embed(user_id: Any) -> discord.Embed:
    """Construye el embed oficial del catálogo de la tienda categorizado con el saldo del usuario."""
    bal = get_balance(user_id)
    cash_str = f"{bal['cash']:,}"

    embed = discord.Embed(
        title="🏪 Tienda Oficial de Porros — 'Asistente'",
        description=(
            "Bienvenido al mercado oficial del servidor. Adquiere roles de estatus, ventajas e ítems de inventario.\n\n"
            "📌 **Cómo comprar de forma segura:**\n"
            "1. Elige un artículo en el **menú desplegable** de abajo.\n"
            "2. Presiona el botón verde **`[ 🛒 Comprar Artículo ]`** para confirmar tu compra."
        ),
        color=0xF39C12,
        timestamp=datetime.now(timezone.utc),
    )

    # 1. Roles de Estatus y Protección
    embed.add_field(
        name="🎭 Roles de Estatus y Protección",
        value=(
            f"• **🛡️ Cartera Blindada** — {PORRO_EMOJI} **50,000** Porros\n"
            f"  *Inmunidad total contra /robar (falla 100% y multa 15%).*\n"
            f"• **🚬 Camello del Barrio** — {PORRO_EMOJI} **85,000** Porros\n"
            f"  *Rol cosmético exclusivo en verde porro (#2ECC71).*\n"
            f"• **🎰 Ludópata Rehabilitado** — {PORRO_EMOJI} **40,000** Porros\n"
            f"  *Rol cosmético exclusivo en rojo casino (#E74C3C).*"
        ),
        inline=False,
    )

    # 2. Ítems de Inventario y Consumibles
    embed.add_field(
        name="🎒 Ítems de Inventario y Consumibles",
        value=(
            f"• **🚬 Porro de Oro** — {PORRO_EMOJI} **75,000** Porros\n"
            f"  *Coleccionable de inventario de máximo prestigio y flexeo.*\n"
            f"• **🥤 Monster Blanco** — {PORRO_EMOJI} **25,000** Porros\n"
            f"  *Consumible supremo: úsalo con `/usar` para resetear al instante `/trabajar`, `/crimen` y `/robar`.*"
        ),
        inline=False,
    )

    # 3. Pases de Experiencia (XP)
    embed.add_field(
        name="⚡ Pases y Bonos de Experiencia (XP)",
        value=(
            f"• **⚡ Chute de XP (24h)** — {PORRO_EMOJI} **15,000** Porros\n"
            f"  *Boost temporal de +5% de XP en Cakey Bot durante 24h (se guarda en `/inventario` y se activa con `/usar`).*\n"
            f"• **🔥 Pase Semanal de XP** — {PORRO_EMOJI} **75,000** Porros\n"
            f"  *Boost temporal de +10% de XP en Cakey Bot durante 7 días (se guarda en `/inventario` y se activa con `/usar`).*\n"
            f"• **💠 Pase Mensual de XP** — {PORRO_EMOJI} **250,000** Porros\n"
            f"  *Boost temporal de +15% de XP en Cakey Bot durante 30 días (se guarda en `/inventario` y se activa con `/usar`).*\n"
            f"• **👑 Aura de XP Permanente** — {PORRO_EMOJI} **1,000,000** Porros\n"
            f"  *Pase perpetuo élite con boost de +10% de XP permanente (se asigna al instante).*"
        ),
        inline=False,
    )

    embed.set_footer(
        text=f"Tu saldo en efectivo: {cash_str} Porros • Si tienes saldo en el banco usa /retirar"
    )
    return embed


class ShopItemSelect(discord.ui.Select):
    """Menú desplegable con los 9 artículos oficiales de la tienda."""

    def __init__(self):
        options = [
            discord.SelectOption(
                label="🛡️ Cartera Blindada (50k)",
                value="cartera_blindada",
                description="50.000 Porros • Inmunidad a robos",
                emoji="🛡️",
            ),
            discord.SelectOption(
                label="🚬 Porro de Oro (75k)",
                value="porro_oro",
                description="75.000 Porros • Flexeo de inventario",
                emoji="🚬",
            ),
            discord.SelectOption(
                label="🚬 Camello del Barrio (85k)",
                value="camello_barrio",
                description="85.000 Porros • Rol Verde (#2ECC71)",
                emoji="🚬",
            ),
            discord.SelectOption(
                label="🎰 Ludópata Rehabilitado (40k)",
                value="ludopata_rehabilitado",
                description="40.000 Porros • Rol Rojo (#E74C3C)",
                emoji="🎰",
            ),
            discord.SelectOption(
                label="🥤 Monster Blanco (25k)",
                value="monster_blanco",
                description="25.000 Porros • Resetea trabajar, crimen y robar",
                emoji="🥤",
            ),
            discord.SelectOption(
                label="⚡ Chute de XP 24h (15k)",
                value="chute_xp",
                description="15.000 Porros • Boost +5% XP por 24h (activar con /usar)",
                emoji="⚡",
            ),
            discord.SelectOption(
                label="🔥 Pase Semanal de XP (75k)",
                value="pase_semanal_xp",
                description="75.000 Porros • Boost +10% XP por 7d (activar con /usar)",
                emoji="🔥",
            ),
            discord.SelectOption(
                label="💠 Pase Mensual de XP (250k)",
                value="pase_mensual_xp",
                description="250.000 Porros • Boost +15% XP por 30d (activar con /usar)",
                emoji="💠",
            ),
            discord.SelectOption(
                label="👑 Aura de XP Permanente (1M)",
                value="aura_xp",
                description="1.000.000 Porros • Boost +10% XP permanente",
                emoji="👑",
            ),
        ]
        super().__init__(
            placeholder="🛒 Selecciona un artículo de la tienda...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        view: "ShopInteractiveView" = self.view
        if interaction.user.id != view.author_id:
            await interaction.response.send_message(
                "❌ Esta tienda pertenece a otro usuario. Usa `/tienda` para abrir la tuya.",
                ephemeral=True,
            )
            return

        selected_key = self.values[0]
        view.selected_item = selected_key
        item_info = SHOP_ITEMS.get(selected_key)
        item_name = item_info["name"] if item_info else selected_key
        price = item_info["price"] if item_info else 0

        # Actualizar el botón de compra con el nombre y precio del artículo seleccionado
        view.buy_btn.label = f"🛒 Comprar {item_name} ({price:,} Porros)"
        view.buy_btn.disabled = False

        await interaction.response.edit_message(view=view)


class ShopInteractiveView(discord.ui.View):
    """
    Vista interactiva para /tienda con menú desplegable y botón explícito de confirmación de compra.
    Evita compras accidentales asegurando que la transacción solo se ejecute al pulsar el botón.
    """

    def __init__(self, author_id: Any, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.author_id = int(author_id)
        self.selected_item: Optional[str] = None
        self.message: Optional[discord.Message] = None

        # Desplegable de artículos (Fila 0)
        self.select_menu = ShopItemSelect()
        self.add_item(self.select_menu)

        # Botón verde de compra explícita (Fila 1)
        self.buy_btn = discord.ui.Button(
            label="🛒 Comprar Artículo",
            style=discord.ButtonStyle.success,
            row=1,
            disabled=False,
        )
        self.buy_btn.callback = self._on_buy_clicked
        self.add_item(self.buy_btn)

    async def _on_buy_clicked(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Esta tienda pertenece a otro usuario. Usa `/tienda` para abrir la tuya.",
                ephemeral=True,
            )
            return

        if not self.selected_item:
            await interaction.response.send_message(
                "⚠️ Selecciona primero un artículo del menú desplegable antes de presionar el botón de compra.",
                ephemeral=True,
            )
            return

        item_key = self.selected_item
        ok, msg, item_data, new_bal = buy_shop_item(
            interaction.user.id,
            item_key,
            member=interaction.user,
        )

        if not ok:
            await interaction.response.send_message(msg, ephemeral=True)
            return

        # Auto-asignación de rol solo para roles permanentes (sin duration_hours)
        role_added = False
        is_temp_or_consumable = bool(
            item_data and (item_data.get("duration_hours") or item_data.get("type") == "consumable")
        )
        if (
            item_data
            and item_data.get("type") == "role"
            and not item_data.get("duration_hours")
            and hasattr(interaction.user, "add_roles")
        ):
            role_id_str = item_data.get("role_id")
            if role_id_str and interaction.guild:
                role = interaction.guild.get_role(int(role_id_str))
                if role:
                    try:
                        await interaction.user.add_roles(role, reason="Compra interactiva en /tienda")
                        role_added = True
                    except Exception as e:
                        _bot_log(f"Aviso auto-asignando rol {role.name}: {e}")

        confirm_embed = discord.Embed(
            title="🛒 ¡Compra Realizada con Éxito!",
            description=(
                f"{msg}\n\n"
                f"**Saldo restante en efectivo:** {PORRO_EMOJI} **{new_bal['cash']:,}** Porros"
            ),
            color=0x2ECC71,
            timestamp=datetime.now(timezone.utc),
        )
        if role_added:
            confirm_embed.add_field(
                name="🎭 Rol Permanente Asignado",
                value=f"¡El rol `{item_data['name']}` ha sido añadido a tu perfil de Discord!",
                inline=False,
            )
        elif is_temp_or_consumable:
            confirm_embed.add_field(
                name="🎒 Guardado en tu Inventario",
                value=(
                    f"**{item_data['name']}** se ha guardado en tu `/inventario`.\n"
                    f"✨ Cuando quieras activarlo o consumirlo, ejecuta **`/usar`**."
                ),
                inline=False,
            )
        confirm_embed.set_footer(text="Gracias por tu compra • Consulta tus objetos con /inventario")

        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)

        # Actualizar el embed principal de la tienda con el nuevo saldo
        try:
            updated_embed = build_shop_embed(self.author_id)
            if interaction.message:
                await interaction.message.edit(embed=updated_embed, view=self)
        except Exception as e:
            _bot_log(f"Aviso actualizando embed de tienda tras compra: {e}")

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


# ==========================================
# INVENTARIO, /USAR Y EXPIRACIÓN DE BUFFOS
# ==========================================

USABLE_ITEM_KEYS = ("monster_blanco", "chute_xp", "pase_semanal_xp", "pase_mensual_xp")


def use_inventory_item(
    user_id: Any,
    item_key: str,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Consume un artículo activable del inventario del usuario (/usar):
    - 'monster_blanco': elimina 1 unidad y resetea last_work, last_crime y last_rob.
    - Pases temporales de XP ('chute_xp', 'pase_semanal_xp', 'pase_mensual_xp'):
      elimina 1 unidad y registra/extiende su entrada en user['active_buffs'].
    """
    uid = str(user_id)
    key_clean = item_key.strip().lower()

    matched_item = None
    for k in USABLE_ITEM_KEYS:
        it = SHOP_ITEMS.get(k)
        if not it:
            continue
        if k == key_clean or it["name"].lower() == key_clean or k in key_clean:
            matched_item = it
            break

    if not matched_item:
        return (
            False,
            f"❌ El artículo '{item_key}' no es un consumible ni un pase activable con `/usar`.",
            None,
        )

    item_id = matched_item["id"]
    item_name = matched_item["name"]

    with ECONOMY_LOCK:
        user = ensure_user(uid)
        inv = user.setdefault("inventory", [])
        if item_name not in inv:
            return (
                False,
                f"❌ No tienes **{item_name}** en tu `/inventario`. Puedes adquirirlo en `/tienda`.",
                None,
            )

        # Consumir 1 unidad
        inv.remove(item_name)
        now = datetime.now(timezone.utc)

        if item_id == "monster_blanco":
            user["last_work"] = None
            user["last_crime"] = None
            user["last_rob"] = None
            data = load_economy_data()
            save_economy_data(data)
            msg = (
                "🥤 ¡Te has tomado un **Monster Blanco** bien frío!\n"
                "⚡ Tus tiempos de espera de **`/trabajar`**, **`/crimen`** y **`/robar`** han quedado **a cero** al instante."
            )
            _bot_log(f"🥤 [Usar] {uid} consumió Monster Blanco y reseteó sus cooldowns.")
            return True, msg, matched_item

        duration_hours = int(matched_item.get("duration_hours", 0))
        role_id = matched_item.get("role_id")
        active_buffs = user.setdefault("active_buffs", [])

        existing_buff = None
        for b in active_buffs:
            if b.get("item_id") == item_id:
                existing_buff = b
                break

        if existing_buff:
            try:
                curr_exp = datetime.fromisoformat(existing_buff["expires_at"])
                if curr_exp > now:
                    new_exp = curr_exp + timedelta(hours=duration_hours)
                    extended = True
                else:
                    new_exp = now + timedelta(hours=duration_hours)
                    extended = False
            except Exception:
                new_exp = now + timedelta(hours=duration_hours)
                extended = False
            existing_buff["expires_at"] = new_exp.isoformat()
            existing_buff["name"] = item_name
            existing_buff["role_id"] = role_id
        else:
            new_exp = now + timedelta(hours=duration_hours)
            extended = False
            active_buffs.append({
                "item_id": item_id,
                "name": item_name,
                "role_id": role_id,
                "activated_at": now.isoformat(),
                "expires_at": new_exp.isoformat(),
            })

        data = load_economy_data()
        save_economy_data(data)

        total_rem_hours = max(1, int(round((new_exp - now).total_seconds() / 3600)))
        if extended:
            msg = (
                f"⚡ ¡Has extendido tu **{item_name}** por **+{duration_hours}h** adicionales!\n"
                f"⏳ **Duración total restante:** ~**{total_rem_hours} horas**."
            )
        else:
            msg = (
                f"✨ ¡Has activado **{item_name}** desde tu inventario!\n"
                f"⏳ **Duración activa:** **{duration_hours} horas**."
            )
        _bot_log(f"⚡ [Usar] {uid} activó '{item_name}' hasta {new_exp.isoformat()}.")
        return True, msg, matched_item


def check_and_expire_buffs(now_dt: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Recorre los usuarios en datos/economia.json, detecta pases temporales de XP cuya
    fecha expires_at haya vencido (<= now_dt), los elimina de active_buffs y devuelve
    la lista de buffs expirados para retirar sus roles en Discord.
    """
    now = now_dt or datetime.now(timezone.utc)
    expired_list: List[Dict[str, Any]] = []

    with ECONOMY_LOCK:
        data = load_economy_data()
        users = data.get("users", {})
        modified = False

        for uid, udata in users.items():
            buffs = udata.get("active_buffs")
            if not buffs or not isinstance(buffs, list):
                continue

            kept_buffs = []
            for b in buffs:
                exp_str = b.get("expires_at")
                if not exp_str:
                    modified = True
                    continue
                try:
                    exp_dt = datetime.fromisoformat(exp_str)
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    modified = True
                    continue

                if exp_dt <= now:
                    expired_list.append({
                        "user_id": str(uid),
                        "item_id": b.get("item_id"),
                        "role_id": b.get("role_id"),
                        "name": b.get("name"),
                        "expires_at": exp_str,
                    })
                    modified = True
                else:
                    kept_buffs.append(b)

            if len(kept_buffs) != len(buffs):
                udata["active_buffs"] = kept_buffs
                modified = True

        if modified:
            save_economy_data(data)

    return expired_list


# Artículos transferibles mediante /regalar
TRANSFERABLE_ITEM_KEYS = {"porro_oro", "monster_blanco", "chute_xp", "pase_semanal_xp", "pase_mensual_xp"}


def gift_inventory_item(
    from_user_id: Any,
    to_user_id: Any,
    item_key: str,
    quantity: int = 1,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Transfiere una o varias unidades de un artículo de inventario a otro usuario (/regalar):
    - Bloquea auto-regalos (from_user_id == to_user_id).
    - Valida quantity >= 1.
    - Rechaza roles permanentes y artículos no transferibles.
    - Artículos transferibles: porro_oro, monster_blanco, chute_xp, pase_semanal_xp, pase_mensual_xp.
    - Verifica que from_user disponga de suficientes unidades en inventory.
    - Transfiere quantity unidades atómicamente bajo ECONOMY_LOCK.
    """
    f_uid = str(from_user_id)
    t_uid = str(to_user_id)

    if is_economy_halted():
        r = get_economy_halt_reason()
        reason_str = f" Motivo: {r}" if r else ""
        return False, f"⛔ Los regalos e intercambios están temporalmente pausados por administración.{reason_str}", None

    if f_uid == t_uid:
        return False, "❌ No puedes regalarte artículos a ti mismo.", None

    if quantity < 1:
        return False, "❌ La cantidad a regalar debe ser de al menos 1 unidad.", None

    key_clean = str(item_key).strip().lower()
    matched_item = None
    for k, it in SHOP_ITEMS.items():
        if k == key_clean or it["name"].lower() == key_clean or k in key_clean:
            matched_item = it
            break

    if not matched_item:
        return False, f"❌ El artículo '{item_key}' no existe en el catálogo de la tienda.", None

    item_id = matched_item["id"]
    item_name = matched_item["name"]

    # Rechazar roles permanentes únicos
    if matched_item.get("type") == "role" and not matched_item.get("duration_hours"):
        return False, f"❌ El artículo **{item_name}** es un rol permanente personal y no es transferible.", matched_item

    if item_id not in TRANSFERABLE_ITEM_KEYS:
        return False, f"❌ El artículo **{item_name}** no es transferible mediante regalo.", matched_item

    with ECONOMY_LOCK:
        from_user = ensure_user(f_uid)
        to_user = ensure_user(t_uid)

        from_inv = from_user.setdefault("inventory", [])
        to_inv = to_user.setdefault("inventory", [])

        current_count = from_inv.count(item_name)
        if current_count < quantity:
            return (
                False,
                f"❌ No tienes suficientes unidades de **{item_name}** en tu inventario (tienes {current_count}, intentas regalar {quantity}).",
                matched_item,
            )

        for _ in range(quantity):
            from_inv.remove(item_name)

        for _ in range(quantity):
            to_inv.append(item_name)

        data = load_economy_data()
        save_economy_data(data)

        _bot_log(f"🎁 [Regalo] {f_uid} regaló {quantity}x '{item_name}' a {t_uid}.")
        msg = f"🎁 ¡Has regalado con éxito **{quantity}x {item_name}**!"
        return True, msg, matched_item


def _format_remaining_time(expires_at_str: str, now: Optional[datetime] = None) -> str:
    now_dt = now or datetime.now(timezone.utc)
    try:
        exp_dt = datetime.fromisoformat(expires_at_str)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        rem_sec = max(0, int((exp_dt - now_dt).total_seconds()))
        days = rem_sec // 86400
        hours = (rem_sec % 86400) // 3600
        mins = (rem_sec % 3600) // 60
        if days > 0:
            return f"{days}d {hours}h restantes"
        if hours > 0:
            return f"{hours}h {mins}m restantes"
        return f"{mins}m restantes"
    except Exception:
        return "Tiempo desconocido"


def build_inventory_embed(
    user_id: Any,
    display_name: str,
    avatar_url: Optional[str] = None,
) -> discord.Embed:
    """Construye el embed de /inventario detallando objetos agrupados, roles permanentes y pases XP activos."""
    check_and_expire_buffs()
    user = ensure_user(user_id)
    bal = get_balance(user_id)
    inv = user.get("inventory", [])
    active_buffs = user.get("active_buffs", [])

    counts = Counter(inv)
    perm_role_names = {
        it["name"]
        for it in SHOP_ITEMS.values()
        if it.get("type") == "role" and not it.get("duration_hours")
    }
    usable_names = {
        SHOP_ITEMS[k]["name"]
        for k in USABLE_ITEM_KEYS
        if k in SHOP_ITEMS
    }

    perm_owned = []
    usable_owned = []
    collectibles_owned = []

    for item_name, qty in counts.items():
        qty_str = f" **×{qty}**" if qty > 1 else ""
        if item_name in perm_role_names:
            perm_owned.append(f"• {item_name}")
        elif item_name in usable_names:
            usable_owned.append(f"• {item_name}{qty_str} *(usable con `/usar`)*")
        else:
            collectibles_owned.append(f"• {item_name}{qty_str}")

    embed = discord.Embed(
        title=f"🎒 Inventario y Pases de {display_name}",
        description=(
            f"💵 **Efectivo:** {PORRO_EMOJI} **{bal['cash']:,}** | "
            f"🏦 **Banco:** {PORRO_EMOJI} **{bal['bank']:,}** | "
            f"💎 **Total:** {PORRO_EMOJI} **{bal['total']:,}**"
        ),
        color=0x9B59B6,
        timestamp=datetime.now(timezone.utc),
    )
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    embed.add_field(
        name="🎭 Roles Permanentes Adquiridos",
        value="\n".join(perm_owned) if perm_owned else "*Ningún rol permanente en propiedad.*",
        inline=False,
    )
    embed.add_field(
        name="🧪 Consumibles y Pases Listos para `/usar`",
        value="\n".join(usable_owned) if usable_owned else "*No tienes consumibles ni pases pendientes de activar.*",
        inline=False,
    )
    embed.add_field(
        name="🏆 Coleccionables y Trofeos",
        value="\n".join(collectibles_owned) if collectibles_owned else "*Sin coleccionables en la vitrina.*",
        inline=False,
    )

    now = datetime.now(timezone.utc)
    if active_buffs:
        buff_lines = []
        for b in active_buffs:
            b_name = b.get("name", b.get("item_id", "Pase XP"))
            rem_str = _format_remaining_time(b.get("expires_at", ""), now)
            buff_lines.append(f"• **{b_name}** — ⏳ `{rem_str}`")
        buff_val = "\n".join(buff_lines)
    else:
        buff_val = "*Ningún pase temporal de XP activo en este momento.*"

    embed.add_field(
        name="⚡ Pases Temporales de XP Activos",
        value=buff_val,
        inline=False,
    )
    embed.set_footer(text="Usa /tienda para comprar artículos y /usar para activar consumibles o pases XP")
    return embed


class InventoryView(discord.ui.View):
    """Vista interactiva efímera de /inventario con botón para presumir el inventario en público."""

    def __init__(
        self,
        author_id: Any,
        target_id: Any,
        target_display_name: str,
        target_avatar_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        super().__init__(timeout=timeout)
        self.author_id = int(author_id)
        self.target_id = int(target_id)
        self.target_display_name = target_display_name
        self.target_avatar_url = target_avatar_url

    @discord.ui.button(
        label="📢 Mostrar en público",
        style=discord.ButtonStyle.primary,
        custom_id="inventory:show_public",
    )
    async def show_public_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Solo quien consultó este inventario puede publicarlo.",
                ephemeral=True,
            )
            return

        button.disabled = True
        button.label = "✅ Mostrado en público"
        pub_embed = build_inventory_embed(
            self.target_id,
            self.target_display_name,
            self.target_avatar_url,
        )
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            content=f"📢 **{interaction.user.display_name}** ha compartido el inventario de **{self.target_display_name}**:",
            embed=pub_embed,
            ephemeral=False,
        )



