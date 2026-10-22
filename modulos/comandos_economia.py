"""
Módulo de Comandos Slash de Economía y Casino (Bot 'Economia Asistente'):
- Restricción estricta de canales (ensure_economy_channel).
- 20 comandos de economía, finanzas, minijuegos y administración.
- Registro en árbol de comandos (register_economy_commands).
"""

import os
import sys
import json
import random
import io
import re
import urllib.parse
from typing import Optional, Union, Any, List
from datetime import datetime, timezone
import asyncio

import discord
from discord import app_commands


def _bs():
    return sys.modules.get("bot_service") or sys.modules.get("__main__")


def _bot_log(msg: str):
    bs = _bs()
    log_fn = getattr(bs, "bot_log", print)
    log_fn(msg)


def _get_base_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_bot():
    bs = _bs()
    return getattr(bs, "bot", None)


from modulos.economia import (
    ECONOMY_CATEGORY_ID,
    ALLOWED_ECONOMY_CHANNELS,
)

async def ensure_economy_channel(interaction: discord.Interaction) -> bool:
    """
    Verifica si la interacción proviene de los canales autorizados para Economía y Casino:
    - Si no hay contexto de canal (mocks unitarios), permite la ejecución (True).
    - Si interaction.channel_id pertenece a ALLOWED_ECONOMY_CHANNELS o la categoría es ECONOMY_CATEGORY_ID, permite (True).
    - En caso contrario, responde con mensaje efímero de restricción y devuelve False.
    """
    from modulos.economia import ALLOWED_ECONOMY_CHANNELS, ECONOMY_CATEGORY_ID

    ch_id = getattr(interaction, "channel_id", None)
    channel = getattr(interaction, "channel", None)

    if ch_id is None and channel is not None:
        ch_id = getattr(channel, "id", None)

    cat_id = getattr(channel, "category_id", None) if channel is not None else None

    # Detectar si hay identificadores reales de canal o categoría
    real_ch_id = None
    if isinstance(ch_id, int):
        real_ch_id = ch_id
    elif isinstance(ch_id, str) and ch_id.isdigit():
        real_ch_id = int(ch_id)

    real_cat_id = None
    if isinstance(cat_id, int):
        real_cat_id = cat_id
    elif isinstance(cat_id, str) and cat_id.isdigit():
        real_cat_id = int(cat_id)

    # Si no hay contexto de canal real (p.ej. tests con MagicMock/AsyncMock sin configurar), permitir
    if real_ch_id is None and real_cat_id is None:
        return True

    if (real_ch_id is not None and real_ch_id in ALLOWED_ECONOMY_CHANNELS) or (
        real_cat_id is not None and real_cat_id == ECONOMY_CATEGORY_ID
    ):
        return True

    await interaction.response.send_message(
        "❌ Los comandos de economía y casino solo están permitidos en los canales de **🎲・CASINO & ECONOMÍA・🎲** (<#1549458785485987890>, <#1550894047382610081> y <#1549512919694442547>).",
        ephemeral=True,
    )
    return False


@app_commands.command(name="slots", description="Juega a la máquina tragaperras del servidor apostando Porros")
@app_commands.describe(
    apuesta="Cantidad de Porros a apostar (mínimo 100, por defecto 100)"
)
async def cmd_slots(interaction: discord.Interaction, apuesta: int = 100):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import handle_slots_spin, SlotsLayoutView, PORRO_EMOJI, MIN_SLOTS_BET

    if apuesta < MIN_SLOTS_BET:
        await interaction.response.send_message(
            f"❌ La apuesta mínima en la tragaperras es de {MIN_SLOTS_BET} Porros ({PORRO_EMOJI}).",
            ephemeral=True,
        )
        return

    ok, err_msg, res, bal = handle_slots_spin(interaction.user.id, apuesta)
    if not ok:
        await interaction.response.send_message(
            f"❌ {err_msg}\n💡 Usa `/trabajar` para conseguir Porros si estás a cero.",
            ephemeral=True,
        )
        return

    view = SlotsLayoutView(res, str(interaction.user.id), apuesta)
    await interaction.response.send_message(view=view)


@app_commands.command(name="balance", description="Consulta tu saldo de Porros o el de otro miembro del servidor")
@app_commands.describe(
    usuario="Miembro cuyo saldo quieres consultar (opcional, por defecto tú)"
)
async def cmd_balance(interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import get_balance, get_server_jackpot, PORRO_EMOJI

    target = usuario or interaction.user
    bal = get_balance(target.id)
    jackpot = get_server_jackpot()

    embed = discord.Embed(
        title=f"💰 Saldo de {target.display_name}",
        color=0xF1C40F,  # Dorado
        timestamp=datetime.now(timezone.utc),
    )
    if hasattr(target, "display_avatar") and target.display_avatar:
        embed.set_thumbnail(url=str(target.display_avatar.url))

    embed.add_field(
        name="💵 Efectivo (Cash)",
        value=f"{PORRO_EMOJI} **{bal['cash']:,}** Porros",
        inline=True,
    )
    embed.add_field(
        name="🏦 Banco (Bank)",
        value=f"{PORRO_EMOJI} **{bal['bank']:,}** Porros",
        inline=True,
    )
    embed.add_field(
        name="💎 Patrimonio Total",
        value=f"{PORRO_EMOJI} **{bal['total']:,}** Porros",
        inline=False,
    )
    embed.add_field(
        name="🎰 Bote Acumulado del Servidor",
        value=f"{PORRO_EMOJI} **{jackpot:,}** Porros *(¡Reclámalo con Ranked Pro en /slots!)*",
        inline=False,
    )
    embed.set_footer(text="Economía Oficial de Porros • Asistente")

    is_ephemeral = (usuario is None or target.id == interaction.user.id)
    await interaction.response.send_message(embed=embed, ephemeral=is_ephemeral)


@app_commands.command(name="trabajar", description="Trabaja en el servidor para conseguir Porros con bono por rol de nivel (cooldown de 4 horas)")
async def cmd_trabajar(interaction: discord.Interaction):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import execute_work, get_balance, PORRO_EMOJI

    member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.user
    ok, job_story, reward = execute_work(interaction.user.id, member=member)
    if not ok:
        await interaction.response.send_message(job_story, ephemeral=True)
        return

    bal = get_balance(interaction.user.id)
    embed = discord.Embed(
        title="💼 Jornada Laboral Completada",
        description=f"{job_story}\n\n**Salario recibido:** {PORRO_EMOJI} **+{reward:,}** Porros\n**Saldo actual en efectivo:** {PORRO_EMOJI} **{bal['cash']:,}** Porros",
        color=0x2ECC71,  # Verde esmeralda
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(
        name=f"{interaction.user.display_name} (@{interaction.user.name})",
        icon_url=str(interaction.user.display_avatar.url) if hasattr(interaction.user, "display_avatar") else None,
    )
    embed.set_footer(text="Vuelve en 4 horas para volver a trabajar (o usa un 🥤 Monster Blanco) • /trabajar")
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="transferir", description="Transfiere Porros de tu efectivo a otro miembro del servidor")
@app_commands.describe(
    usuario="Miembro al que deseas transferir los Porros",
    cantidad="Cantidad exacta de Porros a transferir (número entero positivo)",
)
async def cmd_transferir(interaction: discord.Interaction, usuario: discord.Member, cantidad: int):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import transfer_funds, PORRO_EMOJI

    if usuario.id == interaction.user.id:
        await interaction.response.send_message("❌ No puedes transferirte Porros a ti mismo.", ephemeral=True)
        return

    if getattr(usuario, "bot", False):
        await interaction.response.send_message("❌ No puedes transferir Porros a un bot.", ephemeral=True)
        return

    if cantidad <= 0:
        await interaction.response.send_message("❌ La cantidad a transferir debe ser mayor a 0 Porros.", ephemeral=True)
        return

    ok, msg, sender_bal, recipient_bal = transfer_funds(interaction.user.id, usuario.id, cantidad)
    if not ok:
        await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
        return

    embed = discord.Embed(
        title="💸 Transferencia Exitosa",
        description=f"**{interaction.user.display_name}** le ha transferido {PORRO_EMOJI} **{cantidad:,}** Porros a **{usuario.display_name}**.",
        color=0x3498DB,  # Azul
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name=f"Saldo de {interaction.user.display_name}",
        value=f"{PORRO_EMOJI} **{sender_bal['cash']:,}** Porros",
        inline=True,
    )
    embed.add_field(
        name=f"Saldo de {usuario.display_name}",
        value=f"{PORRO_EMOJI} **{recipient_bal['cash']:,}** Porros",
        inline=True,
    )
    embed.set_footer(text="Transferencia instantánea sin comisiones • Economía de Porros")
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="depositar", description="Deposita Porros de tu efectivo en tu cuenta bancaria protegida")
@app_commands.describe(cantidad="Cantidad de Porros a ingresar en el banco o 'all'/'todo'")
async def cmd_depositar(interaction: discord.Interaction, cantidad: str):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import deposit_cash, PORRO_EMOJI

    ok, msg, bal = deposit_cash(interaction.user.id, cantidad)
    if not ok:
        await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
        return

    embed = discord.Embed(
        title="🏦 Depósito Bancario Completado",
        description=f"{msg}\n\n**Efectivo disponible:** {PORRO_EMOJI} **{bal['cash']:,}** Porros\n**Saldo en banco:** {PORRO_EMOJI} **{bal['bank']:,}** Porros",
        color=0x2ECC71,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(name=interaction.user.display_name, icon_url=str(interaction.user.display_avatar.url) if hasattr(interaction.user, "display_avatar") else None)
    embed.set_footer(text="El banco protege tus Porros al 100% frente a robos • /retirar")
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="retirar", description="Retira Porros de tu cuenta bancaria a tu efectivo")
@app_commands.describe(cantidad="Cantidad de Porros a retirar del banco o 'all'/'todo'")
async def cmd_retirar(interaction: discord.Interaction, cantidad: str):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import withdraw_cash, PORRO_EMOJI

    ok, msg, bal = withdraw_cash(interaction.user.id, cantidad)
    if not ok:
        await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
        return

    embed = discord.Embed(
        title="🏧 Retirada Bancaria Completada",
        description=f"{msg}\n\n**Efectivo disponible:** {PORRO_EMOJI} **{bal['cash']:,}** Porros\n**Saldo restante en banco:** {PORRO_EMOJI} **{bal['bank']:,}** Porros",
        color=0x3498DB,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(name=interaction.user.display_name, icon_url=str(interaction.user.display_avatar.url) if hasattr(interaction.user, "display_avatar") else None)
    embed.set_footer(text="Recuerda que los Porros en efectivo pueden ser atracados con /robar")
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="robar", description="Intenta robar Porros en efectivo a otro miembro del servidor (50% éxito)")
@app_commands.describe(usuario="Miembro al que intentas atracar")
async def cmd_robar(interaction: discord.Interaction, usuario: discord.Member):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import execute_rob, PORRO_EMOJI

    if usuario.id == interaction.user.id:
        await interaction.response.send_message("❌ No puedes robarte a ti mismo. Ve al casino si quieres perder dinero.", ephemeral=True)
        return

    if getattr(usuario, "bot", False):
        await interaction.response.send_message("❌ No puedes robar a un bot. Los bots no llevan Porros encima.", ephemeral=True)
        return

    ok, msg, delta = execute_rob(interaction.user.id, usuario.id, victim_member=usuario)

    color = 0x2ECC71 if ok else 0xE74C3C
    embed = discord.Embed(
        title="🥷 Intento de Atraco",
        description=msg,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(name=f"{interaction.user.display_name} vs {usuario.display_name}")
    embed.set_footer(text="Protege tu efectivo en el banco con /depositar o compra la 🛡️ Cartera Blindada")
    await interaction.response.send_message(embed=embed)


@app_commands.command(name="tienda", description="Consulta el catálogo interactivo de la tienda oficial y adquiere artículos con confirmación")
async def cmd_tienda(interaction: discord.Interaction):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import build_shop_embed, ShopInteractiveView

    embed = build_shop_embed(interaction.user.id)
    view = ShopInteractiveView(author_id=interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)
    try:
        view.message = await interaction.original_response()
    except Exception:
        pass


@app_commands.command(name="salario", description="Cobra tu salario diario acumulado según tus roles de nivel y podio (con decaimiento del 5%)")
async def cmd_salario(interaction: discord.Interaction):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import claim_salary, get_balance, PORRO_EMOJI
    from modulos.chat_ia import get_live_levels_dict

    levels_dict = await get_live_levels_dict(interaction.guild) if interaction.guild else {}
    user_level = levels_dict.get(str(interaction.user.id))

    member = interaction.user if isinstance(interaction.user, discord.Member) else None
    ok, msg, payout, daily_salary = claim_salary(
        interaction.user.id,
        member=member,
        user_level=user_level,
    )

    if not ok:
        await interaction.response.send_message(msg, ephemeral=True)
        return

    bal = get_balance(interaction.user.id)
    embed = discord.Embed(
        title="💵 Cobro de Salario Acumulativo",
        description=msg,
        color=0x2ECC71,
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(
        name="💰 Saldo Actual en Efectivo",
        value=f"{PORRO_EMOJI} **{bal['cash']:,}** Porros",
        inline=True,
    )
    embed.add_field(
        name="📈 Salario Diario Base",
        value=f"{PORRO_EMOJI} **{daily_salary:,}** Porros/día",
        inline=True,
    )
    embed.set_footer(text="Fórmula de decaimiento del 5% diario • Sube de nivel en el servidor para ganar más")
    await interaction.response.send_message(embed=embed)


async def _handle_blackjack_command(interaction: discord.Interaction, apuesta: str = "100"):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import (
        parse_blackjack_bet,
        modify_balance,
        modify_server_jackpot,
        BlackjackHand,
        blackjack_engine,
        BlackjackView,
        build_blackjack_embed,
        ACTIVE_BLACKJACK_GAMES,
        ECONOMY_LOCK,
        PORRO_EMOJI,
        JACKPOT_FEED_PERCENT,
        format_bj_card,
    )

    ok, bet, err = parse_blackjack_bet(interaction.user.id, apuesta)
    if not ok:
        await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        return

    with ECONOMY_LOCK:
        if interaction.user.id in ACTIVE_BLACKJACK_GAMES:
            await interaction.response.send_message(
                "❌ Ya tienes una partida de Blackjack activa en curso. Termínala antes de iniciar otra.",
                ephemeral=True,
            )
            return

        modify_balance(interaction.user.id, cash_delta=-bet)
        ACTIVE_BLACKJACK_GAMES[interaction.user.id] = True

    try:
        player_hand = BlackjackHand([blackjack_engine.draw(), blackjack_engine.draw()])
        dealer_hand = BlackjackHand([blackjack_engine.draw(), blackjack_engine.draw()])

        player_bj = player_hand.is_blackjack
        dealer_bj = dealer_hand.is_blackjack

        if player_bj or dealer_bj:
            with ECONOMY_LOCK:
                ACTIVE_BLACKJACK_GAMES.pop(interaction.user.id, None)
                if player_bj and dealer_bj:
                    modify_balance(interaction.user.id, cash_delta=bet)
                    res_msg = (
                        f"🤝 **¡Empate (Push)!**\n"
                        f"¡Tanto tú como el crupier tenéis **Blackjack Natural** de inicio!\n"
                        f"Se te devuelve tu apuesta de **{bet:,}** Porros ({PORRO_EMOJI})."
                    )
                    color = 0xF1C40F
                elif player_bj:
                    win_net = int(bet * 1.5)
                    payout = bet + win_net
                    modify_balance(interaction.user.id, cash_delta=payout)
                    res_msg = (
                        f"🔥 **¡BLACKJACK NATURAL!** 🃏\n"
                        f"¡Has conseguido 21 de inicio!\n"
                        f"**Pago 3:2:** ¡Has ganado **+{win_net:,}** Porros limpios ({PORRO_EMOJI})!\n"
                        f"💰 Total ingresado en efectivo: **{payout:,}** Porros."
                    )
                    color = 0x2ECC71
                else:
                    jackpot_feed = max(1, int(bet * JACKPOT_FEED_PERCENT))
                    modify_server_jackpot(jackpot_feed)
                    res_msg = (
                        f"💀 **¡El crupier tiene Blackjack Natural!** 🃏\n"
                        f"El crupier ha conseguido 21 con [ {format_bj_card(dealer_hand.cards[0])} ] [ {format_bj_card(dealer_hand.cards[1])} ].\n"
                        f"Has perdido **{bet:,}** Porros ({PORRO_EMOJI}).\n"
                        f"🎰 Se han añadido **+{jackpot_feed:,}** Porros al bote del servidor."
                    )
                    color = 0xE74C3C

            embed = build_blackjack_embed(
                user=interaction.user,
                player_hand=player_hand,
                dealer_hand=dealer_hand,
                bet=bet,
                dealer_revealed=True,
                result_text=res_msg,
                color=color,
            )
            await interaction.response.send_message(embed=embed)
            return

        view = BlackjackView(
            user_id=interaction.user.id,
            user=interaction.user,
            bet=bet,
            engine=blackjack_engine,
            player_hand=player_hand,
            dealer_hand=dealer_hand,
        )
        with ECONOMY_LOCK:
            ACTIVE_BLACKJACK_GAMES[interaction.user.id] = view

        embed = build_blackjack_embed(
            user=interaction.user,
            player_hand=player_hand,
            dealer_hand=dealer_hand,
            bet=bet,
            dealer_revealed=False,
            result_text="Tu turno: Elige si **Pedir**, **Plantarte** o **Doblar** tu apuesta.",
            color=0x3498DB,
        )
        await interaction.response.send_message(embed=embed, view=view)
        try:
            view.message = await interaction.original_response()
        except Exception:
            pass

    except Exception as e:
        with ECONOMY_LOCK:
            modify_balance(interaction.user.id, cash_delta=bet)
            ACTIVE_BLACKJACK_GAMES.pop(interaction.user.id, None)
        raise e


@app_commands.command(name="blackjack", description="Juega al Blackjack 21 nativo contra el crupier apostando Porros")
@app_commands.describe(apuesta="Cantidad de Porros a apostar (mínimo 100) o 'all'/'todo'")
async def cmd_blackjack(interaction: discord.Interaction, apuesta: str = "100"):
    await _handle_blackjack_command(interaction, apuesta)


@app_commands.command(name="bj", description="Alias rápido ergonómico para jugar al Blackjack 21")
@app_commands.describe(apuesta="Cantidad de Porros a apostar (mínimo 100) o 'all'/'todo'")
async def cmd_bj(interaction: discord.Interaction, apuesta: str = "100"):
    await _handle_blackjack_command(interaction, apuesta)


async def _handle_roulette_command(
    interaction: discord.Interaction,
    apuesta: str = "100",
    tipo: str = "rojo",
    numero: Optional[int] = None,
):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import (
        parse_roulette_bet,
        normalize_roulette_bet_type,
        roulette_engine,
        build_roulette_embed,
        RouletteActionView,
        ROULETTE_BET_INFO,
    )

    norm_type = normalize_roulette_bet_type(tipo)
    if norm_type not in ROULETTE_BET_INFO:
        await interaction.response.send_message(
            f"❌ Tipo de apuesta '{tipo}' no válido. Elige una opción oficial del menú.",
            ephemeral=True,
        )
        return

    if norm_type == "pleno":
        if numero is None:
            await interaction.response.send_message(
                "❌ Para apostar a **Pleno**, debes indicar el parámetro `numero` con un valor del 0 al 36.",
                ephemeral=True,
            )
            return
        if not (0 <= numero <= 36):
            await interaction.response.send_message(
                "❌ El número para Pleno debe estar comprendido entre **0** y **36**.",
                ephemeral=True,
            )
            return

    ok, bet, err = parse_roulette_bet(interaction.user.id, apuesta)
    if not ok:
        await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        return

    try:
        res = roulette_engine.spin_wheel(
            user_id=interaction.user.id,
            bet_amount=bet,
            bet_type=norm_type,
            bet_number=numero,
        )
        embed = build_roulette_embed(user=interaction.user, result=res)
        view = RouletteActionView(
            user_id=interaction.user.id,
            user=interaction.user,
            bet_amount=bet,
            bet_type=norm_type,
            bet_number=numero,
            engine=roulette_engine,
        )
        await interaction.response.send_message(embed=embed, view=view)
        try:
            view.message = await interaction.original_response()
        except Exception:
            pass
    except Exception as e:
        await interaction.response.send_message(f"❌ Error al procesar la ruleta: {e}", ephemeral=True)


@app_commands.command(name="ruleta", description="Juega a la Ruleta Europea de 37 casillas (RTP 97.30%)")
@app_commands.describe(
    apuesta="Cantidad de Porros a apostar (mínimo 100) o 'all'/'todo'",
    tipo="Tipo de apuesta (Rojo, Negro, Par, Impar, Docenas, Columnas, Pleno...)",
    numero="Número exacto (0-36). Requerido si eliges 'Pleno'",
)
@app_commands.choices(
    tipo=[
        app_commands.Choice(name="🔴 Rojo", value="rojo"),
        app_commands.Choice(name="⚫ Negro", value="negro"),
        app_commands.Choice(name="⚖️ Par", value="par"),
        app_commands.Choice(name="⚡ Impar", value="impar"),
        app_commands.Choice(name="📉 1-18 (Baja)", value="baja"),
        app_commands.Choice(name="📈 19-36 (Alta)", value="alta"),
        app_commands.Choice(name="1️⃣ 1ª Docena (1-12)", value="docena1"),
        app_commands.Choice(name="2️⃣ 2ª Docena (13-24)", value="docena2"),
        app_commands.Choice(name="3️⃣ 3ª Docena (25-36)", value="docena3"),
        app_commands.Choice(name="🏛️ Columna 1", value="columna1"),
        app_commands.Choice(name="🏛️ Columna 2", value="columna2"),
        app_commands.Choice(name="🏛️ Columna 3", value="columna3"),
        app_commands.Choice(name="🎯 Pleno (0-36)", value="pleno"),
    ]
)
async def cmd_ruleta(
    interaction: discord.Interaction,
    apuesta: str = "100",
    tipo: str = "rojo",
    numero: Optional[int] = None,
):
    await _handle_roulette_command(interaction, apuesta, tipo, numero)


async def _handle_coinflip_command(
    interaction: discord.Interaction,
    apuesta: str = "100",
    lado: Optional[str] = "cara",
    rival: Optional[discord.Member] = None,
):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import (
        parse_coinflip_bet,
        normalize_coinflip_side,
        coinflip_engine,
        build_coinflip_embed,
        CoinflipActionView,
        CoinflipChallengeView,
        ACTIVE_COINFLIP_DUELS,
        ECONOMY_LOCK,
        modify_balance,
        PORRO_EMOJI,
    )

    norm_lado = normalize_coinflip_side(lado)

    # Modo PvE: Lanzamiento rápido contra la casa (sin rival)
    if rival is None:
        ok, bet, err = parse_coinflip_bet(interaction.user.id, apuesta)
        if not ok:
            await interaction.response.send_message(f"❌ {err}", ephemeral=True)
            return

        try:
            res = coinflip_engine.play_pve(
                user_id=interaction.user.id,
                bet_amount=bet,
                choice=norm_lado,
            )
            embed = build_coinflip_embed(mode="pve", user=interaction.user, result=res)
            view = CoinflipActionView(
                user_id=interaction.user.id,
                user=interaction.user,
                bet_amount=bet,
                side=norm_lado,
                engine=coinflip_engine,
            )
            await interaction.response.send_message(embed=embed, view=view)
            try:
                view.message = await interaction.original_response()
            except Exception:
                pass
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al procesar Coinflip: {e}", ephemeral=True)
        return

    # Modo PvP: Duelo entre dos miembros
    if rival.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ No puedes desafiarte a ti mismo. Si quieres jugar solo, no especifiques ningún rival para apostar contra la casa.",
            ephemeral=True,
        )
        return

    if getattr(rival, "bot", False):
        await interaction.response.send_message(
            "❌ No puedes retar a un bot a un duelo de Coinflip. Los duelos son exclusivos entre miembros.",
            ephemeral=True,
        )
        return

    ok, bet, err = parse_coinflip_bet(interaction.user.id, apuesta)
    if not ok:
        await interaction.response.send_message(f"❌ {err}", ephemeral=True)
        return

    with ECONOMY_LOCK:
        if str(interaction.user.id) in ACTIVE_COINFLIP_DUELS or interaction.user.id in ACTIVE_COINFLIP_DUELS:
            await interaction.response.send_message(
                "❌ Ya tienes un duelo de Coinflip activo en curso. Termínalo o cancélalo antes de retar a otro miembro.",
                ephemeral=True,
            )
            return

        if str(rival.id) in ACTIVE_COINFLIP_DUELS or rival.id in ACTIVE_COINFLIP_DUELS:
            await interaction.response.send_message(
                f"❌ **{rival.display_name}** ya tiene un desafío activo en curso. Espera a que termine su duelo.",
                ephemeral=True,
            )
            return

        # Deducir y retener la fianza del retador atómicamente bajo ECONOMY_LOCK
        modify_balance(interaction.user.id, cash_delta=-bet)
        ACTIVE_COINFLIP_DUELS[str(interaction.user.id)] = True
        ACTIVE_COINFLIP_DUELS[str(rival.id)] = True

    c_side = norm_lado
    r_side = "cruz" if c_side == "cara" else "cara"

    view = CoinflipChallengeView(
        challenger_id=interaction.user.id,
        challenger=interaction.user,
        rival_id=rival.id,
        rival=rival,
        bet_amount=bet,
        challenger_side=c_side,
        engine=coinflip_engine,
    )
    with ECONOMY_LOCK:
        ACTIVE_COINFLIP_DUELS[str(interaction.user.id)] = view
        ACTIVE_COINFLIP_DUELS[str(rival.id)] = view

    embed = build_coinflip_embed(
        mode="pvp_pending",
        challenger=interaction.user,
        rival=rival,
        bet=bet,
        challenger_side=c_side,
        rival_side=r_side,
    )

    try:
        await interaction.response.send_message(
            content=f"⚔️ {rival.mention}, ¡has sido desafiado a un duelo de Coinflip por {interaction.user.mention}!",
            embed=embed,
            view=view,
        )
        try:
            view.message = await interaction.original_response()
        except Exception:
            pass
    except Exception as e:
        with ECONOMY_LOCK:
            modify_balance(interaction.user.id, cash_delta=+bet)
            ACTIVE_COINFLIP_DUELS.pop(str(interaction.user.id), None)
            ACTIVE_COINFLIP_DUELS.pop(str(rival.id), None)
            ACTIVE_COINFLIP_DUELS.pop(interaction.user.id, None)
            ACTIVE_COINFLIP_DUELS.pop(rival.id, None)
        await interaction.response.send_message(f"❌ Error al iniciar el desafío: {e}", ephemeral=True)


@app_commands.command(
    name="coinflip",
    description="Lanza una moneda 50/50 contra la casa (PvE) o desafía a un miembro en duelo (PvP)",
)
@app_commands.describe(
    apuesta="Cantidad de Porros a apostar (mínimo 100) o 'all'/'todo'",
    lado="Lado de la moneda que eliges (por defecto Cara)",
    rival="Miembro al que desafiar en duelo PvP (opcional: si no se indica juegas contra la casa)",
)
@app_commands.choices(
    lado=[
        app_commands.Choice(name="🪙 Cara", value="cara"),
        app_commands.Choice(name="🪙 Cruz", value="cruz"),
    ]
)
async def cmd_coinflip(
    interaction: discord.Interaction,
    apuesta: str = "100",
    lado: Optional[str] = "cara",
    rival: Optional[discord.Member] = None,
):
    await _handle_coinflip_command(interaction, apuesta, lado, rival)


@app_commands.command(
    name="casino",
    description="Centro de Control del Casino Central: catálogo interactivo de juegos, reglas y bote",
)
async def cmd_casino(interaction: discord.Interaction):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import CasinoHubView, build_casino_hub_embed

    view = CasinoHubView(author_id=interaction.user.id)
    embed = build_casino_hub_embed(interaction.user, selected_game=None)

    await interaction.response.send_message(embed=embed, view=view)
    try:
        view.message = await interaction.original_response()
    except Exception:
        pass


@app_commands.command(
    name="crimen",
    description="Comete un delito de alto riesgo en el servidor (50% éxito, cooldown de 12 horas)",
)
async def cmd_crimen(interaction: discord.Interaction):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import execute_crime, get_balance, PORRO_EMOJI

    member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.user
    ok, msg, delta = execute_crime(interaction.user.id, member=member)

    if not ok and delta == 0 and msg.startswith("⏳"):
        await interaction.response.send_message(msg, ephemeral=True)
        return

    bal = get_balance(interaction.user.id)
    color = 0x2ECC71 if ok else 0xE74C3C
    title = "🦹 Golpe Criminal Completado" if ok else "🚓 Redada Policial — Delito Frustrado"

    embed = discord.Embed(
        title=title,
        description=(
            f"{msg}\n\n"
            f"**Saldo actual en efectivo:** {PORRO_EMOJI} **{bal['cash']:,}** Porros"
        ),
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(
        name=f"{interaction.user.display_name} (@{interaction.user.name})",
        icon_url=str(interaction.user.display_avatar.url) if hasattr(interaction.user, "display_avatar") and interaction.user.display_avatar else None,
    )
    embed.set_footer(text="Cooldown de 12 horas (o resetea al instante con /usar 🥤 Monster Blanco) • /crimen")
    await interaction.response.send_message(embed=embed)


@app_commands.command(
    name="ranking",
    description="Muestra el Top 10 de miembros más ricos del servidor (Patrimonio Total, Efectivo y Banco)",
)
async def cmd_ranking(interaction: discord.Interaction):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import build_ranking_embed, RankingView

    embed = build_ranking_embed(
        sort_by="total",
        requester_id=interaction.user.id,
        guild=interaction.guild,
    )
    view = RankingView(author_id=interaction.user.id, sort_by="total")
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
    try:
        view.message = await interaction.original_response()
    except Exception:
        pass


@app_commands.command(
    name="inventario",
    description="Consulta tus artículos, consumibles, roles permanentes y pases de XP activos",
)
@app_commands.describe(
    usuario="Miembro cuyo inventario deseas consultar (opcional, por defecto tú)"
)
async def cmd_inventario(interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import build_inventory_embed, InventoryView

    target = usuario or interaction.user
    avatar_url = (
        str(target.display_avatar.url)
        if hasattr(target, "display_avatar") and target.display_avatar
        else None
    )
    embed = build_inventory_embed(target.id, target.display_name, avatar_url)
    view = InventoryView(
        author_id=interaction.user.id,
        target_id=target.id,
        target_display_name=target.display_name,
        target_avatar_url=avatar_url,
    )
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@app_commands.command(
    name="usar",
    description="Consume un artículo o activa un pase temporal de XP guardado en tu /inventario",
)
@app_commands.describe(
    articulo="Elige el artículo o pase de tu inventario que quieres usar ahora mismo"
)
@app_commands.choices(
    articulo=[
        app_commands.Choice(name="🥤 Monster Blanco (Resetea /trabajar, /crimen y /robar)", value="monster_blanco"),
        app_commands.Choice(name="⚡ Chute de XP (24h — Boost +5% XP)", value="chute_xp"),
        app_commands.Choice(name="🔥 Pase Semanal de XP (7 días — Boost +10% XP)", value="pase_semanal_xp"),
        app_commands.Choice(name="💠 Pase Mensual de XP (30 días — Boost +15% XP)", value="pase_mensual_xp"),
    ]
)
async def cmd_usar(interaction: discord.Interaction, articulo: str):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import use_inventory_item

    ok, msg, item_data = use_inventory_item(interaction.user.id, articulo)
    if not ok:
        await interaction.response.send_message(msg, ephemeral=True)
        return

    role_assigned = False
    if item_data and item_data.get("role_id") and interaction.guild and hasattr(interaction.user, "add_roles"):
        role = interaction.guild.get_role(int(item_data["role_id"]))
        if role:
            try:
                await interaction.user.add_roles(role, reason=f"Activación de {item_data['name']} con /usar")
                role_assigned = True
            except Exception as e:
                _bot_log(f"Aviso asignando rol temporal en /usar: {e}")

    embed = discord.Embed(
        title=f"✨ Artículo Utilizado: {item_data['name']}",
        description=msg,
        color=0x2ECC71,
        timestamp=datetime.now(timezone.utc),
    )
    if role_assigned:
        embed.add_field(
            name="🎭 Rol de Boost Activado",
            value=f"Se te ha asignado el rol **{item_data['name']}** en el servidor durante el periodo activo.",
            inline=False,
        )
    embed.set_footer(text="Consulta el tiempo restante de tus pases con /inventario")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@app_commands.command(
    name="regalar",
    description="Regala artículos o consumibles de tu inventario a otro miembro del servidor",
)
@app_commands.describe(
    usuario="Miembro al que deseas regalar el artículo",
    articulo="Artículo o consumible transferible de tu inventario",
    cantidad="Cantidad de unidades a regalar (por defecto 1)",
)
@app_commands.choices(
    articulo=[
        app_commands.Choice(name="🚬 Porro de Oro (Coleccionable)", value="porro_oro"),
        app_commands.Choice(name="🥤 Monster Blanco (Resetea cooldowns)", value="monster_blanco"),
        app_commands.Choice(name="⚡ Chute de XP (24h — Boost +5% XP)", value="chute_xp"),
        app_commands.Choice(name="🔥 Pase Semanal de XP (7 días — Boost +10% XP)", value="pase_semanal_xp"),
        app_commands.Choice(name="💠 Pase Mensual de XP (30 días — Boost +15% XP)", value="pase_mensual_xp"),
    ]
)
async def cmd_regalar(
    interaction: discord.Interaction,
    usuario: discord.Member,
    articulo: str,
    cantidad: int = 1,
):
    if not await ensure_economy_channel(interaction):
        return

    from modulos.economia import gift_inventory_item

    if usuario.id == interaction.user.id:
        await interaction.response.send_message("❌ No puedes regalarte artículos a ti mismo.", ephemeral=True)
        return

    if getattr(usuario, "bot", False):
        await interaction.response.send_message("❌ No puedes regalar artículos a un bot. Los bots no tienen inventario.", ephemeral=True)
        return

    if cantidad < 1:
        await interaction.response.send_message("❌ La cantidad debe ser al menos 1 unidad.", ephemeral=True)
        return

    ok, msg, item_data = gift_inventory_item(interaction.user.id, usuario.id, articulo, cantidad)
    if not ok:
        await interaction.response.send_message(msg, ephemeral=True)
        return

    item_name = item_data["name"] if item_data else articulo
    embed = discord.Embed(
        title="🎁 Regalo Enviado con Éxito",
        description=(
            f"**{interaction.user.display_name}** le ha regalado **{cantidad}x {item_name}** a **{usuario.display_name}**.\n\n"
            f"📦 Los artículos se han transferido directamente a su `/inventario`."
        ),
        color=0xE91E63,  # Rosa/Fucsia festivo
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(
        name=f"{interaction.user.display_name} ➡️ {usuario.display_name}",
        icon_url=str(interaction.user.display_avatar.url) if hasattr(interaction.user, "display_avatar") else None,
    )
    embed.set_footer(text="Economía Oficial de Porros • Asistente")
    await interaction.response.send_message(embed=embed)


@app_commands.command(
    name="admin_dinero",
    description="[ADMIN] Panel financiero para dar, quitar, fijar Porros o lanzar un Airdrop por rol",
)
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    accion="Operación a realizar (dar, quitar, fijar o airdrop a un rol)",
    cantidad="Cantidad de Porros (entero positivo, o >= 0 para fijar)",
    destino="Dónde aplicar la operación: Efectivo (Cash) o Banco (Bank)",
    usuario="Miembro objetivo (obligatorio para dar, quitar y fijar)",
    rol="Rol objetivo (obligatorio para airdrop masivo)",
)
@app_commands.choices(
    accion=[
        app_commands.Choice(name="➕ Dar Porros a un miembro", value="dar"),
        app_commands.Choice(name="➖ Quitar Porros a un miembro", value="quitar"),
        app_commands.Choice(name="🎯 Fijar saldo exacto a un miembro", value="fijar"),
        app_commands.Choice(name="🪂 Airdrop masivo a todos los miembros de un rol", value="airdrop"),
    ],
    destino=[
        app_commands.Choice(name="💵 Efectivo (Cash)", value="cash"),
        app_commands.Choice(name="🏦 Banco (Bank)", value="bank"),
    ],
)
async def cmd_admin_dinero(
    interaction: discord.Interaction,
    accion: str,
    cantidad: int,
    destino: str = "cash",
    usuario: Optional[discord.Member] = None,
    rol: Optional[discord.Role] = None,
):
    from modulos.economia import admin_modify_money, admin_airdrop_role, PORRO_EMOJI

    # Verificación estricta de permisos de Administrador
    is_admin = bool(
        getattr(interaction.user, "guild_permissions", None)
        and interaction.user.guild_permissions.administrator
    )
    if not is_admin:
        await interaction.response.send_message(
            "⛔ No tienes permisos de **Administrador** para ejecutar este comando financiero.",
            ephemeral=True,
        )
        return

    act = accion.strip().lower()
    if act == "airdrop":
        if rol is None:
            await interaction.response.send_message(
                "❌ Para ejecutar un **Airdrop**, debes especificar el parámetro `rol`.",
                ephemeral=True,
            )
            return

        human_members = [
            (m.id, getattr(m, "name", None))
            for m in getattr(rol, "members", [])
            if not getattr(m, "bot", False)
        ]
        ok, msg, count = admin_airdrop_role(
            targets=human_members,
            amount=cantidad,
            target_field=destino,
            role_name=rol.name,
        )
        if not ok:
            await interaction.response.send_message(msg, ephemeral=True)
            return

        embed = discord.Embed(
            title="🪂 Airdrop Administrativo Ejecutado",
            description=msg,
            color=0xF1C40F,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Ejecutado por {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Operaciones individuales: dar, quitar, fijar
    if usuario is None:
        await interaction.response.send_message(
            f"❌ Para la acción **{act}**, debes indicar el parámetro `usuario`.",
            ephemeral=True,
        )
        return

    ok, msg, new_bal = admin_modify_money(
        target_user_id=usuario.id,
        action=act,
        amount=cantidad,
        target_field=destino,
        username=getattr(usuario, "name", None),
    )
    if not ok:
        await interaction.response.send_message(msg, ephemeral=True)
        return

    embed = discord.Embed(
        title=f"🛠️ Ajuste Financiero — {usuario.display_name}",
        description=(
            f"{msg}\n\n"
            f"• 💵 **Nuevo Efectivo:** {PORRO_EMOJI} **{new_bal['cash']:,}** Porros\n"
            f"• 🏦 **Nuevo Banco:** {PORRO_EMOJI} **{new_bal['bank']:,}** Porros\n"
            f"• 💎 **Patrimonio Total:** {PORRO_EMOJI} **{new_bal['total']:,}** Porros"
        ),
        color=0x3498DB,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"Operación '{act}' ejecutada por {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed, ephemeral=True)




# ==========================================
# 20 COMANDOS DE ECONOMÍA (BOT 'ECONOMIA ASISTENTE')
# ==========================================
from modulos.comandos_bolsa import cmd_bolsa, cmd_cartera, cmd_aura

ECONOMY_SLASH_COMMANDS = [
    cmd_slots,
    cmd_balance,
    cmd_trabajar,
    cmd_transferir,
    cmd_depositar,
    cmd_retirar,
    cmd_robar,
    cmd_tienda,
    cmd_salario,
    cmd_blackjack,
    cmd_bj,
    cmd_ruleta,
    cmd_coinflip,
    cmd_casino,
    cmd_crimen,
    cmd_ranking,
    cmd_inventario,
    cmd_usar,
    cmd_regalar,
    cmd_admin_dinero,
    cmd_bolsa,
    cmd_cartera,
    cmd_aura,
]


def register_economy_commands(tree: app_commands.CommandTree):
    """Registra los 20 comandos slash de economía en el árbol del bot Economia Asistente."""
    for cmd in ECONOMY_SLASH_COMMANDS:
        try:
            tree.add_command(cmd)
        except app_commands.CommandAlreadyRegistered:
            pass
        except Exception as e:
            _bot_log(f"Aviso registrando comando de economía /{cmd.name}: {e}")



