"""
Módulo de Memoria Social Dinámica y Grafo de Relaciones:
- Persistencia thread-safe y atómica en datos/social_graph.json.
- Registro de afinidades entre miembros de la comunidad (tiempo conjunto en voz, duelos/juegos, menciones).
- Generador de contexto social (get_social_dynamics_ctx) para enriquecer el System Prompt de Gemini.
"""

import os
import sys
import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
import discord


def _bs():
    return sys.modules.get("bot_service") or sys.modules.get("__main__")


def _get_base_dir():
    bs = _bs()
    return getattr(bs, "BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


SOCIAL_GRAPH_PATH = os.path.join(_get_base_dir(), "datos", "social_graph.json")
_SOCIAL_LOCK = threading.Lock()

# Miembros clave canónicos del servidor (lore y roles consolidados)
CANONICAL_PEERS = {
    857923274771136522: {"name": "Joselito", "role": "Fundador / Admin Principal", "close_friends": [999304511464149104]},
    999304511464149104: {"name": "Iván", "alias": "mpx56", "role": "Co-Fundador / Admin", "close_friends": [857923274771136522]},
}


def _make_pair_key(id1: Union[int, str], id2: Union[int, str]) -> str:
    """Genera una clave canónica ordenada y única para un par de usuarios (id_menor:id_mayor)."""
    s1, s2 = str(id1), str(id2)
    return f"{s1}:{s2}" if s1 <= s2 else f"{s2}:{s1}"


def load_social_graph() -> Dict[str, Any]:
    """Carga de forma segura el grafo social desde datos/social_graph.json."""
    with _SOCIAL_LOCK:
        if os.path.exists(SOCIAL_GRAPH_PATH):
            try:
                with open(SOCIAL_GRAPH_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Aviso lectura social_graph.json: {e}")
        return {"version": 1, "relationships": {}}


def save_social_graph(data: Dict[str, Any]) -> None:
    """Guarda de forma atómica y thread-safe el grafo social en disco."""
    with _SOCIAL_LOCK:
        os.makedirs(os.path.dirname(SOCIAL_GRAPH_PATH), exist_ok=True)
        tmp_path = f"{SOCIAL_GRAPH_PATH}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, SOCIAL_GRAPH_PATH)
        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            print(f"Error guardando social_graph.json: {e}")


def get_affinity(user1_id: Union[int, str], user2_id: Union[int, str]) -> Dict[str, Any]:
    """Obtiene el registro de interacción y afinidad entre dos usuarios."""
    if str(user1_id) == str(user2_id):
        return {"voice_minutes_together": 0, "duels_count": 0, "affinity_score": 100, "last_interaction": ""}

    data = load_social_graph()
    key = _make_pair_key(user1_id, user2_id)
    return data.get("relationships", {}).get(key, {
        "voice_minutes_together": 0,
        "duels_count": 0,
        "affinity_score": 0,
        "last_interaction": "",
    })


def record_voice_duo(user1_id: Union[int, str], user2_id: Union[int, str], minutes: float = 1.0) -> None:
    """Registra minutos compartidos en el mismo canal de voz y actualiza la afinidad."""
    if str(user1_id) == str(user2_id):
        return

    data = load_social_graph()
    rels = data.setdefault("relationships", {})
    key = _make_pair_key(user1_id, user2_id)

    rel = rels.setdefault(key, {
        "voice_minutes_together": 0.0,
        "duels_count": 0,
        "affinity_score": 0,
        "last_interaction": "",
    })

    rel["voice_minutes_together"] = round(rel.get("voice_minutes_together", 0.0) + minutes, 2)
    # 1 punto de afinidad cada 15 minutos en llamada conjunta
    voice_bonus = int(rel["voice_minutes_together"] // 15)
    rel["affinity_score"] = rel.get("duels_count", 0) * 2 + voice_bonus
    rel["last_interaction"] = datetime.now(timezone.utc).isoformat()

    save_social_graph(data)


def record_duel_interaction(user1_id: Union[int, str], user2_id: Union[int, str], interaction_type: str = "duel") -> None:
    """Registra una interacción de juego/duelo (Tres en Raya, Conecta 4, Ajedrez, Tribunal, etc.)."""
    if str(user1_id) == str(user2_id):
        return

    data = load_social_graph()
    rels = data.setdefault("relationships", {})
    key = _make_pair_key(user1_id, user2_id)

    rel = rels.setdefault(key, {
        "voice_minutes_together": 0.0,
        "duels_count": 0,
        "affinity_score": 0,
        "last_interaction": "",
    })

    rel["duels_count"] = rel.get("duels_count", 0) + 1
    voice_bonus = int(rel.get("voice_minutes_together", 0.0) // 15)
    rel["affinity_score"] = rel["duels_count"] * 2 + voice_bonus
    rel["last_interaction"] = datetime.now(timezone.utc).isoformat()

    save_social_graph(data)


def get_social_dynamics_ctx(
    author: Optional[Union[discord.Member, discord.User]],
    guild: Optional[discord.Guild] = None,
    raw_msgs: Optional[List[discord.Message]] = None,
) -> str:
    """
    Analiza a los miembros activos en la conversación reciente y genera una píldora concisa
    de dinámica social y afinidades mutuas para el System Prompt.
    """
    if not author or not guild:
        return ""

    # Identificar IDs de participantes activos en el canal (excluyendo bots)
    active_members_dict = {}
    if hasattr(author, "id") and not getattr(author, "bot", False):
        active_members_dict[author.id] = getattr(author, "display_name", str(author))

    if raw_msgs:
        for msg in raw_msgs[-8:]:
            m_author = getattr(msg, "author", None)
            if m_author and not getattr(m_author, "bot", False):
                active_members_dict[m_author.id] = getattr(m_author, "display_name", str(m_author))
            for m in getattr(msg, "mentions", []):
                if not getattr(m, "bot", False):
                    active_members_dict[m.id] = getattr(m, "display_name", str(m))

    if len(active_members_dict) < 2:
        # Si solo hay 1 miembro activo, verificar si es uno de los líderes canónicos
        if author.id in CANONICAL_PEERS:
            peer_info = CANONICAL_PEERS[author.id]
            return f"\n[DINÁMICA SOCIAL DETECTADA]: {peer_info['name']} es {peer_info['role']} del servidor."
        return ""

    lines = []
    analyzed_pairs = set()
    active_ids = list(active_members_dict.keys())
    data = load_social_graph()
    rels = data.get("relationships", {})

    for i in range(len(active_ids)):
        for j in range(i + 1, len(active_ids)):
            u1, u2 = active_ids[i], active_ids[j]
            pair_key = _make_pair_key(u1, u2)
            if pair_key in analyzed_pairs:
                continue
            analyzed_pairs.add(pair_key)

            name1 = active_members_dict[u1]
            name2 = active_members_dict[u2]

            # 1. Chequeo canónico de lore (Joselito e Iván)
            if (u1 in CANONICAL_PEERS and u2 in CANONICAL_PEERS) or (
                u1 in CANONICAL_PEERS and u2 in CANONICAL_PEERS.get(u1, {}).get("close_friends", [])
            ):
                lines.append(f"- {name1} y {name2} son colegas habituales y co-fundadores/admins del servidor (alta confianza y complicidad).")
                continue

            # 2. Chequeo en grafo social persistido
            rel = rels.get(pair_key)
            if rel:
                score = rel.get("affinity_score", 0)
                v_mins = rel.get("voice_minutes_together", 0)
                duels = rel.get("duels_count", 0)

                if score >= 10 or v_mins >= 30 or duels >= 3:
                    detail = []
                    if v_mins >= 30:
                        detail.append(f"{int(v_mins)} min en llamada")
                    if duels >= 2:
                        detail.append(f"{duels} duelos/partidas")
                    det_str = f" ({', '.join(detail)})" if detail else ""
                    lines.append(f"- {name1} y {name2} tienen alta afinidad social{det_str}.")
                elif duels >= 1:
                    lines.append(f"- {name1} y {name2} han disputado duelos/juegos recientemente.")

    if not lines:
        return ""

    return "\n[DINÁMICA SOCIAL Y GRAFO DE RELACIONES]:\n" + "\n".join(lines[:4])
