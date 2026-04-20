"""Build normalized monster family/combat groups for classifier planning.

This script consumes the d2data monster seed CSV and produces grouped outputs
that can be used for OCR/image classification work and combat-risk planning.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


# mon_type -> (family_group, broad_archetype)
RAW_MON_TYPE_MAP: Dict[str, Tuple[str, str]] = {
    "arach": ("arachnid_insectoid", "insectoid"),
    "baboon": ("simian_beast", "beast"),
    "batdemon": ("imp_pack", "demon"),
    "bighead": ("fallen_clan", "demon"),
    "bloodlord": ("demon_legion", "demon"),
    "blunderbore": ("brute_beast", "beast"),
    "bovine": ("bovine_beast", "beast"),
    "brute": ("brute_beast", "beast"),
    "clawviper": ("viper_reptile", "reptile"),
    "construct": ("construct_siege", "construct"),
    "corruptrogue": ("corrupt_rogue", "humanoid"),
    "councilmember": ("zakarum_cult", "humanoid"),
    "deathmauler": ("brute_beast", "beast"),
    "demon": ("demon_legion", "demon"),
    "doomknight": ("demon_legion", "demon"),
    "fallen": ("fallen_clan", "demon"),
    "fetish": ("fetish_tribe", "demon"),
    "fingermage": ("caster_demon", "demon"),
    "foulcrow": ("avian_pack", "avian"),
    "frogdemon": ("beast_demon", "demon"),
    "frozenhorror": ("brute_beast", "beast"),
    "goatman": ("goatman_clan", "humanoid"),
    "golem": ("golem_construct", "summon"),
    "human": ("human", "humanoid"),
    "imp": ("imp_pack", "demon"),
    "megademon": ("demon_legion", "demon"),
    "minion": ("demon_legion", "demon"),
    "mosquito": ("flying_insectoid", "insectoid"),
    "mummy": ("mummy_undead", "undead"),
    "overseer": ("demonic_humanoid", "humanoid"),
    "pantherwoman": ("cat_warrior", "humanoid"),
    "putriddefiler": ("insectoid_aberration", "insectoid"),
    "quillrat": ("quill_beast", "beast"),
    "regurgitator": ("beast_demon", "demon"),
    "sandleaper": ("leaper_reptile", "reptile"),
    "sandmaggot": ("maggot_insectoid", "insectoid"),
    "sandraider": ("goatman_clan", "humanoid"),
    "scarab": ("beetle_insectoid", "insectoid"),
    "siegebeast": ("construct_siege", "construct"),
    "skeleton": ("skeleton_undead", "undead"),
    "snowyeti": ("brute_beast", "beast"),
    "succubus": ("succubus_coven", "demon"),
    "swarm": ("flying_insectoid", "insectoid"),
    "tentacle": ("tentacle_aberration", "construct"),
    "thornhulk": ("plant_aberration", "construct"),
    "undead": ("zombie_undead", "undead"),
    "undeadfetish": ("fetish_tribe", "undead"),
    "unraveler": ("mummy_undead", "undead"),
    "vampire": ("vampire_demon", "demon"),
    "vilekind": ("fallen_clan", "demon"),
    "vulture": ("avian_pack", "avian"),
    "willowisp": ("arcane_spirit", "spirit"),
    "wraith": ("spirit_undead", "spirit"),
    "zakarum": ("zakarum_cult", "humanoid"),
    "zombie": ("zombie_undead", "undead"),
}

OBJECT_KEYWORDS = {
    "barricade",
    "door",
    "wall",
    "window",
    "catapult",
    "statue",
    "nest",
    "egg",
    "spawner",
    "portal",
    "hole",
    "trap",
    "effect",
    "prison",
    "tombs",
    "hut",
}
CRITTER_KEYWORDS = {
    "bat",
    "bird",
    "bunny",
    "camel",
    "chicken",
    "cow",
    "eagle",
    "fish",
    "horse",
    "parrot",
    "pig",
    "rat",
    "scorpion",
    "seagull",
    "snake",
    "wolf",
    "bear",
}
INSECT_KEYWORDS = {"spider", "maggot", "larva", "mosquito", "bug", "sucker", "vine"}
SPIRIT_KEYWORDS = {"spirit", "soul", "ghost", "wolverine", "sage", "valkyrie"}
NPC_KEYWORDS = {"tyrael", "izual", "wanderer", "kaelan", "ancient"}

SUMMON_AI = {
    "cycleoflife",
    "druidbear",
    "druidwolf",
    "elementalbeast",
    "hydra",
    "invisopet",
    "invisospawner",
    "necropet",
    "raven",
    "shadowmaster",
    "shadowwarrior",
    "totem",
    "vines",
}
NPC_AI = {"jarjar", "npcstationary", "towner"}

KNOWN_TOWN_NPCS = {
    "akara",
    "alkor",
    "anya",
    "asheara",
    "atma",
    "cain",
    "deckard cain",
    "charsi",
    "drognan",
    "elzix",
    "fara",
    "geglash",
    "gheed",
    "greiz",
    "halbu",
    "jamella",
    "jerhyn",
    "kashya",
    "larzuk",
    "lysander",
    "malah",
    "meshif",
    "natalya",
    "nihlathak",
    "ormus",
    "qual-kehk",
    "rathe",
    "tyrael",
    "warriv",
}

# Base danger prior to row-level adjustments. 0 means non-combat defaults.
FAMILY_BASE_DANGER: Dict[str, int] = {
    "arcane_spirit": 5,
    "succubus_coven": 4,
    "demon_legion": 4,
    "zakarum_cult": 3,
    "caster_demon": 4,
    "vampire_demon": 4,
    "mummy_undead": 4,
    "demonic_humanoid": 4,
    "beast_demon": 4,
    "demon_variant_untyped": 4,
    "spirit_undead": 4,
    "viper_reptile": 4,
    "imp_pack": 3,
    "fetish_tribe": 3,
    "goatman_clan": 3,
    "corrupt_rogue": 3,
    "cat_warrior": 3,
    "construct_siege": 3,
    "tentacle_aberration": 3,
    "maggot_insectoid": 3,
    "insectoid_aberration": 3,
    "beetle_insectoid": 3,
    "arachnid_insectoid": 3,
    "brute_beast": 3,
    "leaper_reptile": 3,
    "zombie_undead": 2,
    "skeleton_undead": 2,
    "fallen_clan": 2,
    "quill_beast": 2,
    "avian_pack": 2,
    "simian_beast": 2,
    "bovine_beast": 2,
    "human": 1,
    "environment_object": 0,
    "npc_or_story": 0,
    "wildlife_critter": 0,
    "summon_or_pet": 0,
    "unknown_untyped": 1,
}

NON_COMBAT_GROUPS = {"environment_object", "npc_or_story", "wildlife_critter", "summon_or_pet"}

RANGED_FAMILY_GROUPS = {
    "corrupt_rogue",
    "succubus_coven",
    "arcane_spirit",
    "spirit_undead",
    "vampire_demon",
    "caster_demon",
    "zakarum_cult",
    "quill_beast",
    "avian_pack",
    "flying_insectoid",
    "tentacle_aberration",
    "construct_siege",
}
MELEE_FAMILY_GROUPS = {
    "demon_legion",
    "fallen_clan",
    "goatman_clan",
    "cat_warrior",
    "brute_beast",
    "zombie_undead",
    "skeleton_undead",
    "viper_reptile",
    "leaper_reptile",
    "simian_beast",
    "bovine_beast",
    "maggot_insectoid",
    "beetle_insectoid",
    "arachnid_insectoid",
    "insectoid_aberration",
}
LIFE_DRAIN_FAMILY_GROUPS = {"vampire_demon", "spirit_undead", "arcane_spirit"}
MANA_DRAIN_FAMILY_GROUPS = {"spirit_undead", "arcane_spirit", "beetle_insectoid"}
ELEMENTAL_FIRE_FAMILY_GROUPS = {"succubus_coven", "demon_legion"}
ELEMENTAL_COLD_FAMILY_GROUPS = {"brute_beast", "mummy_undead"}
ELEMENTAL_LIGHTNING_FAMILY_GROUPS = {"arcane_spirit", "beetle_insectoid"}
ELEMENTAL_POISON_FAMILY_GROUPS = {"arachnid_insectoid", "maggot_insectoid", "insectoid_aberration", "viper_reptile"}

ACT_BOSS_NAMES = {"andariel", "duriel", "mephisto", "diablo", "baal", "the smith", "radament", "blood raven"}

RANGED_KEYWORDS = {
    "archer",
    "slinger",
    "quill",
    "mage",
    "witch",
    "caster",
    "sorcer",
    "warlock",
    "hierophant",
    "temptress",
    "harlot",
    "fury",
    "soul",
    "gloam",
    "ghost",
    "specter",
    "vampire",
    "catapult",
    "sentry",
    "spitter",
}
RANGED_PHYSICAL_KEYWORDS = {"archer", "slinger", "quill", "throw", "spit", "spitter", "spear cat"}
RANGED_MAGIC_KEYWORDS = {
    "mage",
    "witch",
    "caster",
    "soul",
    "gloam",
    "vampire",
    "succubus",
    "hierophant",
    "shaman",
    "hydra",
    "storm",
}
MELEE_KEYWORDS = {"knight", "brute", "mauler", "crusher", "beast", "warrior", "fiend", "lord", "claw", "fang"}
LIGHT_MOVER_KEYWORDS = {"fetish", "stygian", "soul killer", "carver", "devilkin", "imp", "leaper", "wraith", "ghost"}
HEAVY_MELEE_KEYWORDS = {"brute", "mauler", "crusher", "beast", "urdar", "minion of destruction", "blood lord"}
SUMMONER_KEYWORDS = {"shaman", "unraveler", "hollow one", "spawner", "nest", "egg", "portal"}
CURSE_KEYWORDS = {"witch", "harlot", "temptress", "vampire", "council member", "hierophant", "succubus"}
CROWD_CONTROL_KEYWORDS = {"viper", "watcher", "stalker", "mauler", "overseer", "sentry", "trap"}
LEECH_LIFE_KEYWORDS = {"vampire", "wraith", "specter", "ghost", "soul", "leech", "blood"}
LEECH_MANA_KEYWORDS = {"gloam", "burning soul", "black soul", "wraith", "ghost", "mana"}
FIRE_KEYWORDS = {"fire", "flame", "burn", "inferno", "hell"}
COLD_KEYWORDS = {"cold", "frozen", "chill", "ice", "snow"}
LIGHTNING_KEYWORDS = {"lightning", "spark", "storm", "soul", "gloam", "arc"}
POISON_KEYWORDS = {"poison", "venom", "plague", "toxic", "defiler", "maggot", "spider", "viper"}

# Consensus-driven threat overrides from community + patch-note context.
# Super-critical focuses on monsters broadly cited as run-ending/one-shot risks.
DOLL_KEYWORDS = {"stygian doll", "undead stygian doll", "soul killer", "undead soul killer"}
SOUL_LIGHTNING_KEYWORDS = {"burning soul", "black soul", "gloam"}
VIPER_KEYWORDS = {"tomb viper", "serpent magus", "claw viper", "pit viper", "salamander"}
FRENZYTAUR_KEYWORDS = {"death lord", "moon lord", "minion of destruction", "frenzytaur"}
OBLIVION_KNIGHT_KEYWORDS = {"oblivion knight", "doom knight"}
AURA_SCALING_KEYWORDS = {
    "archer",
    "stygian doll",
    "soul killer",
    "burning soul",
    "black soul",
    "gloam",
    "death lord",
    "moon lord",
    "minion of destruction",
}
SUPER_CRITICAL_EXACT_NAMES = {
    "stygian doll",
    "undead stygian doll",
    "soul killer",
    "undead soul killer",
    "burning soul",
    "black soul",
    "gloam",
}
CRITICAL_NAME_KEYWORDS = {
    "tomb viper",
    "serpent magus",
    "claw viper",
    "pit viper",
    "salamander",
    "death lord",
    "moon lord",
    "minion of destruction",
    "oblivion knight",
    "doom knight",
}

# Human-opinion consensus buckets (board/reddit weighted priors).
CONSENSUS_RUN_ENDING_KEYWORDS = {
    "stygian doll",
    "undead stygian doll",
    "soul killer",
    "undead soul killer",
    "burning soul",
    "black soul",
    "gloam",
}
CONSENSUS_FEARED_KEYWORDS = {
    "tomb viper",
    "serpent magus",
    "claw viper",
    "pit viper",
    "salamander",
    "death lord",
    "moon lord",
    "minion of destruction",
    "oblivion knight",
    "doom knight",
    "council member",
    "blood lord",
}
CONSENSUS_DANGEROUS_KEYWORDS = {
    "archer",
    "spear cat",
    "quill rat",
    "hierophant",
    "succubus",
    "harlot",
    "witch",
    "vampire",
    "wraith",
    "ghost",
    "specter",
    "scarab",
}


def parse_args() -> argparse.Namespace:
    """Parse args.

    Parameters:
        None.

    Local Variables:
        parser: Local variable for parser used in this routine.
        script_root: Local variable for script root used in this routine.

    Returns:
        A value matching the annotated return type `argparse.Namespace`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    script_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Build monster family grouping outputs")
    parser.add_argument(
        "--repo-root",
        default=str(script_root),
        help="Repo root path (default: parent of scripts directory)",
    )
    parser.add_argument(
        "--input-csv",
        default="data/web_seed_pack/processed/monsters/d2data_monstats.web_seed.csv",
        help="Input monstats CSV path",
    )
    parser.add_argument(
        "--output-dir",
        default="data/web_seed_pack/processed/monsters",
        help="Output directory for grouped files",
    )
    return parser.parse_args()


def resolve_path(repo_root: Path, path_value: str) -> Path:
    """Resolve path.

    Parameters:
        repo_root: Parameter for repo root used in this routine.
        path_value: Parameter for path value used in this routine.

    Local Variables:
        candidate: Local variable for candidate used in this routine.

    Returns:
        A value matching the annotated return type `Path`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


def normalize(value: str) -> str:
    """Normalize.

    Parameters:
        value: Parameter for value used in this routine.

    Local Variables:
        None declared inside the function body.

    Returns:
        A value matching the annotated return type `str`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    return (value or "").strip().lower()


def contains_any(text: str, words: Iterable[str]) -> bool:
    """Contains any.

    Parameters:
        text: Parameter for text used in this routine.
        words: Parameter for words used in this routine.

    Local Variables:
        word: Local variable for word used in this routine.

    Returns:
        A value matching the annotated return type `bool`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    return any(word in text for word in words)


def parse_int(value: str) -> int:
    """Parse int.

    Parameters:
        value: Parameter for value used in this routine.

    Local Variables:
        raw: Local variable for raw used in this routine.

    Returns:
        A value matching the annotated return type `int`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    raw = normalize(value)
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def danger_label(priority: int) -> str:
    """Danger label.

    Parameters:
        priority: Parameter for priority used in this routine.

    Local Variables:
        None declared inside the function body.

    Returns:
        A value matching the annotated return type `str`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    if priority <= 0:
        return "non_combat"
    if priority == 1:
        return "minimal"
    if priority == 2:
        return "low"
    if priority == 3:
        return "medium"
    if priority == 4:
        return "high"
    if priority == 5:
        return "critical"
    return "super_critical"


def classify_monster(row: Dict[str, str]) -> Dict[str, str]:
    """Classify monster.

    Parameters:
        row: Parameter for row used in this routine.

    Local Variables:
        ai: Local variable for ai used in this routine.
        base_id: Local variable for base id used in this routine.
        broad_archetype: Local variable for broad archetype used in this routine.
        display_name: Local variable for display name used in this routine.
        family_group: Local variable for family group used in this routine.
        joined: Local variable for joined used in this routine.
        monstats_id: Local variable for monstats id used in this routine.
        name_str: Local variable for name str used in this routine.
        raw_family: Local variable for raw family used in this routine.

    Returns:
        A value matching the annotated return type `Dict[str, str]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    raw_family = normalize(row.get("mon_type", ""))
    monstats_id = normalize(row.get("monstats_id", ""))
    display_name = normalize(row.get("display_name", ""))
    name_str = normalize(row.get("name_str", ""))
    base_id = normalize(row.get("base_id", ""))
    ai = normalize(row.get("ai", ""))

    if raw_family:
        if raw_family in RAW_MON_TYPE_MAP:
            family_group, broad_archetype = RAW_MON_TYPE_MAP[raw_family]
            return {
                "raw_family": raw_family,
                "family_group": family_group,
                "broad_archetype": broad_archetype,
                "family_source": "mon_type",
                "classification_confidence": "high",
            }
        return {
            "raw_family": raw_family,
            "family_group": f"raw_{raw_family}",
            "broad_archetype": "unknown",
            "family_source": "mon_type_unmapped",
            "classification_confidence": "medium",
        }

    joined = " ".join([monstats_id, display_name, name_str, base_id, ai])

    # Re-map known combat rows that otherwise look like summons due keywords.
    if "wolfrider" in joined:
        return {
            "raw_family": "",
            "family_group": "fallen_clan",
            "broad_archetype": "demon",
            "family_source": "heuristic_wolfrider",
            "classification_confidence": "high",
        }
    if "familiar" in joined and "invisopet" not in joined:
        return {
            "raw_family": "",
            "family_group": "imp_pack",
            "broad_archetype": "demon",
            "family_source": "heuristic_familiar",
            "classification_confidence": "medium",
        }

    if contains_any(joined, OBJECT_KEYWORDS) or ai.startswith("trap-"):
        return {
            "raw_family": "",
            "family_group": "environment_object",
            "broad_archetype": "object",
            "family_source": "heuristic_object",
            "classification_confidence": "high",
        }
    if ai in SUMMON_AI or contains_any(joined, {"decoy", "pet", "valkyrie", "wolf", "bear", "hydra"}):
        return {
            "raw_family": "",
            "family_group": "summon_or_pet",
            "broad_archetype": "summon",
            "family_source": "heuristic_summon",
            "classification_confidence": "high",
        }
    if ai in NPC_AI or contains_any(joined, NPC_KEYWORDS):
        return {
            "raw_family": "",
            "family_group": "npc_or_story",
            "broad_archetype": "npc",
            "family_source": "heuristic_npc",
            "classification_confidence": "high",
        }
    if contains_any(joined, SPIRIT_KEYWORDS):
        return {
            "raw_family": "",
            "family_group": "spirit_entity",
            "broad_archetype": "spirit",
            "family_source": "heuristic_spirit",
            "classification_confidence": "medium",
        }
    if contains_any(joined, INSECT_KEYWORDS):
        return {
            "raw_family": "",
            "family_group": "insectoid_other",
            "broad_archetype": "insectoid",
            "family_source": "heuristic_insectoid",
            "classification_confidence": "medium",
        }
    if contains_any(joined, CRITTER_KEYWORDS):
        return {
            "raw_family": "",
            "family_group": "wildlife_critter",
            "broad_archetype": "critter",
            "family_source": "heuristic_critter",
            "classification_confidence": "medium",
        }
    if contains_any(joined, {"bloodmage", "chaoshorde", "darkguard", "gorgon"}):
        return {
            "raw_family": "",
            "family_group": "demon_variant_untyped",
            "broad_archetype": "demon",
            "family_source": "heuristic_demon_variant",
            "classification_confidence": "medium",
        }
    if "hellmeteor" in joined:
        return {
            "raw_family": "",
            "family_group": "environment_object",
            "broad_archetype": "object",
            "family_source": "heuristic_object",
            "classification_confidence": "medium",
        }

    return {
        "raw_family": "",
        "family_group": "unknown_untyped",
        "broad_archetype": "unknown",
        "family_source": "unclassified",
        "classification_confidence": "low",
    }


def clamp(value: int, lower: int, upper: int) -> int:
    """Clamp.

    Parameters:
        value: Parameter for value used in this routine.
        lower: Parameter for lower used in this routine.
        upper: Parameter for upper used in this routine.

    Local Variables:
        None declared inside the function body.

    Returns:
        A value matching the annotated return type `int`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    return max(lower, min(upper, value))


def pick_threat_vectors(tags: Set[str]) -> Tuple[str, str]:
    """Pick threat vectors.

    Parameters:
        tags: Parameter for tags used in this routine.

    Local Variables:
        primary: Local variable for primary used in this routine.
        ranked: Local variable for ranked used in this routine.
        scores: Local variable for scores used in this routine.
        secondary: Local variable for secondary used in this routine.

    Returns:
        A value matching the annotated return type `Tuple[str, str]`.

    Side Effects:
        - May mutate mutable containers or objects in place.
    """
    scores: Dict[str, int] = {}

    def bump(vector: str, amount: int) -> None:
        """Bump.

        Parameters:
            vector: Parameter for vector used in this routine.
            amount: Parameter for amount used in this routine.

        Local Variables:
            None declared inside the function body.

        Returns:
            None.

        Side Effects:
            - May mutate mutable containers or objects in place.
        """
        scores[vector] = scores.get(vector, 0) + amount

    if "on_death_hazard" in tags:
        bump("on_death_burst", 8)
    if "lightning_sniper" in tags or "projectile_burst" in tags:
        bump("ranged_burst", 7)
    if "viper_cloud" in tags:
        bump("area_denial", 7)
    if "frenzy_melee" in tags or "burst_melee" in tags:
        bump("melee_burst", 6)
    if "debuff_source" in tags or "crowd_control" in tags:
        bump("debuff_control", 5)
    if "summoner" in tags or "resurrector" in tags or "corpse_or_spawn_pressure" in tags:
        bump("spawn_pressure", 5)
    if "life_drain" in tags or "mana_drain" in tags:
        bump("attrition_drain", 4)
    if "turret" in tags:
        bump("turret_lane", 4)
    if "ranged_attacker" in tags:
        bump("ranged_pressure", 3)
    if "melee_attacker" in tags or "heavy_melee" in tags:
        bump("melee_pressure", 3)

    if not scores:
        return ("general_pressure", "none")

    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    primary = ranked[0][0]
    secondary = ranked[1][0] if len(ranked) > 1 else "none"
    return (primary, secondary)


def compute_mobility_class(tags: Set[str]) -> str:
    """Compute mobility class.

    Parameters:
        tags: Parameter for tags used in this routine.

    Local Variables:
        None declared inside the function body.

    Returns:
        A value matching the annotated return type `str`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    if "turret" in tags:
        return "stationary"
    if "leaper" in tags or "light_mover" in tags:
        return "fast"
    if "heavy_melee" in tags and "ranged_attacker" not in tags:
        return "slow_heavy"
    if "ranged_attacker" in tags:
        return "kiting"
    return "standard"


def compute_engagement_profile(tags: Set[str]) -> str:
    """Compute engagement profile.

    Parameters:
        tags: Parameter for tags used in this routine.

    Local Variables:
        None declared inside the function body.

    Returns:
        A value matching the annotated return type `str`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    if "on_death_hazard" in tags:
        return "suicide_rusher"
    if "lightning_sniper" in tags:
        return "sniper"
    if "turret" in tags:
        return "turret_zone"
    if "summoner" in tags or "resurrector" in tags:
        return "support_spawner"
    if "frenzy_melee" in tags or "heavy_melee" in tags:
        return "rushdown_melee"
    if "ranged_attacker" in tags and "debuff_source" in tags:
        return "debuff_caster"
    if "ranged_attacker" in tags:
        return "ranged_pressure"
    if "melee_attacker" in tags:
        return "frontline_melee"
    return "mixed"


def compute_pressure_ratings(tags: Set[str], threat: int, danger_priority: int) -> Dict[str, int]:
    """Compute pressure ratings.

    Parameters:
        tags: Parameter for tags used in this routine.
        threat: Parameter for threat used in this routine.
        danger_priority: Parameter for danger priority used in this routine.

    Local Variables:
        attrition: Local variable for attrition used in this routine.
        burst: Local variable for burst used in this routine.
        control: Local variable for control used in this routine.
        spawn: Local variable for spawn used in this routine.

    Returns:
        A value matching the annotated return type `Dict[str, int]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    burst = 0
    if "on_death_hazard" in tags:
        burst += 2
    if "projectile_burst" in tags or "lightning_sniper" in tags:
        burst += 2
    if "frenzy_melee" in tags or "burst_melee" in tags:
        burst += 2
    if "heavy_melee" in tags:
        burst += 1
    if "high_threat" in tags:
        burst += 1
    if danger_priority >= 5:
        burst += 1

    control = 0
    if "debuff_source" in tags or "curse" in tags:
        control += 2
    if "crowd_control" in tags:
        control += 2
    if "viper_cloud" in tags:
        control += 2
    if "turret" in tags:
        control += 1

    attrition = 0
    if "life_drain" in tags or "mana_drain" in tags:
        attrition += 2
    if "elemental_poison" in tags:
        attrition += 1
    if "ranged_attacker" in tags:
        attrition += 1
    if "high_threat" in tags:
        attrition += 1

    spawn = 0
    if "summoner" in tags:
        spawn += 2
    if "resurrector" in tags:
        spawn += 2
    if "corpse_or_spawn_pressure" in tags:
        spawn += 1

    return {
        "burst_pressure_rating": clamp(burst, 0, 5),
        "control_pressure_rating": clamp(control, 0, 5),
        "attrition_pressure_rating": clamp(attrition, 0, 5),
        "spawn_pressure_rating": clamp(spawn, 0, 5),
        "threat_rollup_rating": clamp(int(round((burst + control + attrition + spawn) / 2.0)), 0, 5),
        "threat_intensity_rating": clamp(int(round((danger_priority + max(0, threat // 2)) / 2.0)), 0, 6),
    }


def compute_consensus_metadata(joined: str, tags: Set[str], danger_priority: int, threat: int) -> Dict[str, object]:
    """Compute consensus metadata.

    Parameters:
        joined: Parameter for joined used in this routine.
        tags: Parameter for tags used in this routine.
        danger_priority: Parameter for danger priority used in this routine.
        threat: Parameter for threat used in this routine.

    Local Variables:
        band: Local variable for band used in this routine.
        has_danger_keyword: Local variable representing a boolean condition.
        has_feared_keyword: Local variable representing a boolean condition.
        has_run_ending_keyword: Local variable representing a boolean condition.
        score: Local variable for score used in this routine.
        source_bucket: Local variable for source bucket used in this routine.

    Returns:
        A value matching the annotated return type `Dict[str, object]`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    has_run_ending_keyword = contains_any(joined, CONSENSUS_RUN_ENDING_KEYWORDS)
    has_feared_keyword = contains_any(joined, CONSENSUS_FEARED_KEYWORDS)
    has_danger_keyword = contains_any(joined, CONSENSUS_DANGEROUS_KEYWORDS)

    score = danger_priority * 10
    if has_run_ending_keyword:
        score += 36
    if has_feared_keyword:
        score += 22
    if has_danger_keyword:
        score += 10

    if "super_critical_threat" in tags:
        score += 25
    elif "critical_threat" in tags:
        score += 14

    if "on_death_hazard" in tags:
        score += 15
    if "lightning_sniper" in tags:
        score += 15
    if "viper_cloud" in tags:
        score += 14
    if "frenzy_melee" in tags:
        score += 10
    if "debuff_source" in tags:
        score += 8
    if "archer" in tags:
        score += 7
    if "high_threat" in tags:
        score += 5
    if "act_boss" in tags:
        score += 8
    if threat >= 11:
        score += 3

    score = clamp(int(score), 0, 100)

    if "super_critical_threat" in tags or has_run_ending_keyword:
        band = "run_ending"
    elif score >= 80:
        band = "feared"
    elif score >= 55:
        band = "dangerous"
    elif score >= 30:
        band = "caution"
    else:
        band = "routine"

    if has_run_ending_keyword or "super_critical_threat" in tags:
        source_bucket = "community_run_ending"
    elif has_feared_keyword or "critical_threat" in tags:
        source_bucket = "community_feared"
    elif has_danger_keyword:
        source_bucket = "community_dangerous"
    else:
        source_bucket = "mechanics_inferred"

    return {
        "human_consensus_score": score,
        "human_consensus_band": band,
        "consensus_source_bucket": source_bucket,
    }


def compute_target_priority_score(
    combat_relevant: bool,
    danger_priority: int,
    consensus_score: int,
    ratings: Dict[str, int],
    tags: Set[str],
) -> int:
    """Compute target priority score.

    Parameters:
        combat_relevant: Parameter for combat relevant used in this routine.
        danger_priority: Parameter for danger priority used in this routine.
        consensus_score: Parameter for consensus score used in this routine.
        ratings: Parameter for ratings used in this routine.
        tags: Parameter for tags used in this routine.

    Local Variables:
        score: Local variable for score used in this routine.

    Returns:
        A value matching the annotated return type `int`.

    Side Effects:
        - No direct side effects beyond returning computed values.
    """
    if not combat_relevant:
        return 0

    score = (
        danger_priority * 12
        + int(round(consensus_score * 0.45))
        + ratings["burst_pressure_rating"] * 6
        + ratings["control_pressure_rating"] * 5
        + ratings["attrition_pressure_rating"] * 4
        + ratings["spawn_pressure_rating"] * 4
    )

    if "super_critical_threat" in tags:
        score += 15
    elif "critical_threat" in tags:
        score += 8
    if "act_boss" in tags:
        score += 6
    if "elite_unique" in tags:
        score += 4

    return clamp(int(score), 1, 100)


def classify_combat_profile(row: Dict[str, str], family_group: str, broad_archetype: str) -> Dict[str, object]:
    """Classify combat profile.

    Parameters:
        row: Parameter for row used in this routine.
        family_group: Parameter for family group used in this routine.
        broad_archetype: Parameter for broad archetype used in this routine.

    Local Variables:
        ai: Local variable for ai used in this routine.
        auto_critical_candidate: Local variable for auto critical candidate used in this routine.
        avoidance_priority: Local variable for avoidance priority used in this routine.
        base_id: Local variable for base id used in this routine.
        base_priority: Local variable for base priority used in this routine.
        boss_name: Local variable for boss name used in this routine.
        combat_relevant: Local variable for combat relevant used in this routine.
        consensus: Local variable for consensus used in this routine.
        critical_candidate: Local variable for critical candidate used in this routine.
        display_name: Local variable for display name used in this routine.
        enabled: Local variable for enabled used in this routine.
        engagement_profile: Local variable for engagement profile used in this routine.
        is_doll_family: Local variable representing a boolean condition.
        is_enabled: Local variable representing a boolean condition.
        is_frenzytaur_family: Local variable representing a boolean condition.
        is_named_doll_threat: Local variable representing a boolean condition.
        is_oblivion_knight_family: Local variable representing a boolean condition.
        is_ranged: Local variable representing a boolean condition.
        is_soul_lightning_family: Local variable representing a boolean condition.
        is_viper_cloud_family: Local variable representing a boolean condition.
        joined: Local variable for joined used in this routine.
        mobility_class: Local variable for mobility class used in this routine.
        monstats_id: Local variable for monstats id used in this routine.
        name_str: Local variable for name str used in this routine.
        needs_corpse_control: Local variable for needs corpse control used in this routine.
        needs_debuff_response: Local variable for needs debuff response used in this routine.
        needs_line_of_sight_break: Local variable for needs line of sight break used in this routine.
        pressure_ratings: Local variable for pressure ratings used in this routine.
        priority: Local variable for priority used in this routine.
        raw_family: Local variable for raw family used in this routine.
        super_critical_candidate: Local variable for super critical candidate used in this routine.
        super_critical_name_match: Local variable for super critical name match used in this routine.
        superunique_refs: Local variable for superunique refs used in this routine.
        tags: Local variable for tags used in this routine.
        target_priority_score: Local variable for target priority score used in this routine.
        threat: Local variable for threat used in this routine.
        threat_vector_primary: Local variable for threat vector primary used in this routine.
        threat_vector_secondary: Local variable for threat vector secondary used in this routine.

    Returns:
        A value matching the annotated return type `Dict[str, object]`.

    Side Effects:
        - May mutate mutable containers or objects in place.
    """
    monstats_id = normalize(row.get("monstats_id", ""))
    display_name = normalize(row.get("display_name", ""))
    name_str = normalize(row.get("name_str", ""))
    base_id = normalize(row.get("base_id", ""))
    ai = normalize(row.get("ai", ""))
    enabled = normalize(row.get("enabled", ""))
    threat = parse_int(row.get("threat", ""))
    superunique_refs = normalize(row.get("superunique_refs", ""))
    raw_family = normalize(row.get("mon_type", ""))

    joined = " ".join([monstats_id, display_name, name_str, base_id, ai, family_group])

    tags: Set[str] = set()

    if broad_archetype:
        tags.add(f"archetype_{broad_archetype}")

    is_ranged = False
    if family_group in RANGED_FAMILY_GROUPS or contains_any(joined, RANGED_KEYWORDS):
        is_ranged = True
    if contains_any(joined, {"catapult", "sentry", "trap", "turret"}):
        is_ranged = True

    if is_ranged:
        tags.add("ranged_attacker")
        # Backward-compatible alias requested by user: treat archer as all ranged attackers.
        tags.add("archer")

    if contains_any(joined, RANGED_PHYSICAL_KEYWORDS):
        tags.add("ranged_physical")
    if contains_any(joined, RANGED_MAGIC_KEYWORDS) or family_group in {"succubus_coven", "arcane_spirit", "vampire_demon", "caster_demon"}:
        tags.add("ranged_magic")

    if not is_ranged and (family_group in MELEE_FAMILY_GROUPS or contains_any(joined, MELEE_KEYWORDS)):
        tags.add("melee_attacker")

    if contains_any(joined, {"leaper", "jump", "lunger"}) or family_group == "leaper_reptile":
        tags.add("leaper")
    if family_group in {"fallen_clan", "fetish_tribe", "imp_pack", "flying_insectoid", "leaper_reptile", "spirit_undead", "avian_pack"}:
        tags.add("light_mover")
    if contains_any(joined, LIGHT_MOVER_KEYWORDS):
        tags.add("light_mover")

    if family_group in {"brute_beast", "demon_legion", "goatman_clan", "viper_reptile"} or contains_any(joined, HEAVY_MELEE_KEYWORDS):
        tags.add("heavy_melee")

    if raw_family == "undeadfetish" or contains_any(joined, {"stygian doll", "soul killer", "undead stygian", "bonefetish"}):
        tags.add("explode")

    if contains_any(joined, SUMMONER_KEYWORDS):
        tags.add("summoner")
    if contains_any(joined, {"shaman", "unraveler", "hollow one"}):
        tags.add("resurrector")
    if contains_any(joined, CURSE_KEYWORDS):
        tags.add("curse")
    if contains_any(joined, CROWD_CONTROL_KEYWORDS):
        tags.add("crowd_control")

    if contains_any(joined, {"catapult", "sentry", "trap", "turret"}) or family_group == "construct_siege":
        tags.add("turret")

    if family_group in LIFE_DRAIN_FAMILY_GROUPS or contains_any(joined, LEECH_LIFE_KEYWORDS):
        tags.add("life_drain")
    if family_group in MANA_DRAIN_FAMILY_GROUPS or contains_any(joined, LEECH_MANA_KEYWORDS):
        tags.add("mana_drain")

    if family_group in ELEMENTAL_FIRE_FAMILY_GROUPS or contains_any(joined, FIRE_KEYWORDS):
        tags.add("elemental_fire")
    if family_group in ELEMENTAL_COLD_FAMILY_GROUPS or contains_any(joined, COLD_KEYWORDS):
        tags.add("elemental_cold")
    if family_group in ELEMENTAL_LIGHTNING_FAMILY_GROUPS or contains_any(joined, LIGHTNING_KEYWORDS):
        tags.add("elemental_lightning")
    if family_group in ELEMENTAL_POISON_FAMILY_GROUPS or contains_any(joined, POISON_KEYWORDS):
        tags.add("elemental_poison")

    if superunique_refs:
        tags.add("elite_unique")
        tags.add("superunique")
    if any(boss_name in joined for boss_name in ACT_BOSS_NAMES):
        tags.add("act_boss")
    if threat >= 11:
        tags.add("high_threat")

    if (
        "ranged_attacker" not in tags
        and "melee_attacker" not in tags
        and "turret" not in tags
        and family_group not in NON_COMBAT_GROUPS
        and broad_archetype not in {"object", "npc", "critter"}
    ):
        tags.add("melee_attacker")

    is_named_doll_threat = contains_any(joined, DOLL_KEYWORDS)
    is_doll_family = raw_family == "undeadfetish" or is_named_doll_threat
    is_soul_lightning_family = contains_any(joined, SOUL_LIGHTNING_KEYWORDS)
    is_viper_cloud_family = family_group == "viper_reptile" or contains_any(joined, VIPER_KEYWORDS)
    is_frenzytaur_family = contains_any(joined, FRENZYTAUR_KEYWORDS)
    is_oblivion_knight_family = contains_any(joined, OBLIVION_KNIGHT_KEYWORDS)

    if is_doll_family and "explode" in tags:
        tags.add("on_death_hazard")
        tags.add("doll_exploder")
    if is_soul_lightning_family and "ranged_magic" in tags:
        tags.add("lightning_sniper")
        tags.add("projectile_burst")
    if is_viper_cloud_family:
        tags.add("viper_cloud")
    if is_frenzytaur_family:
        tags.add("frenzy_melee")
        tags.add("burst_melee")
    if is_oblivion_knight_family or "curse" in tags:
        tags.add("debuff_source")
    if contains_any(joined, AURA_SCALING_KEYWORDS) or "ranged_attacker" in tags or "heavy_melee" in tags:
        tags.add("aura_scaling")
    if "summoner" in tags or "resurrector" in tags:
        tags.add("corpse_or_spawn_pressure")

    is_enabled = enabled == "1"

    combat_relevant = True
    if family_group in NON_COMBAT_GROUPS or broad_archetype in {"object", "npc", "critter"}:
        combat_relevant = False
    if not is_enabled and not superunique_refs:
        combat_relevant = False
    if family_group == "human":
        # Human rows include many town NPCs; only keep clearly hostile humans.
        if display_name in KNOWN_TOWN_NPCS or ai in NPC_AI:
            combat_relevant = False
        elif threat < 8 and not superunique_refs:
            combat_relevant = False

    super_critical_name_match = (
        display_name in SUPER_CRITICAL_EXACT_NAMES
        or name_str in SUPER_CRITICAL_EXACT_NAMES
    )
    super_critical_candidate = combat_relevant and (
        super_critical_name_match
        or (
            is_named_doll_threat
            and "explode" in tags
            and "shaman" not in joined
            and "resurrector" not in tags
        )
        or (
            is_soul_lightning_family
            and "ranged_magic" in tags
            and "elemental_lightning" in tags
            and ("mana_drain" in tags or threat >= 11)
        )
    )

    critical_candidate = combat_relevant and (
        contains_any(joined, CRITICAL_NAME_KEYWORDS)
        or (
            is_viper_cloud_family
            and "crowd_control" in tags
            and "elemental_poison" in tags
        )
        or (
            is_frenzytaur_family
            and "heavy_melee" in tags
        )
        or is_oblivion_knight_family
        or "act_boss" in tags
    )

    auto_critical_candidate = combat_relevant and (
        (
            "elite_unique" in tags
            and threat >= 11
            and (
                "heavy_melee" in tags
                or ("curse" in tags and ("ranged_attacker" in tags or "ranged_magic" in tags))
                or ("ranged_magic" in tags and "elemental_lightning" in tags)
                or "doll_exploder" in tags
            )
        )
        or (
            "ranged_magic" in tags
            and "elemental_lightning" in tags
            and threat >= 12
        )
    )

    base_priority = FAMILY_BASE_DANGER.get(family_group, 2)
    priority = base_priority

    if combat_relevant:
        if "explode" in tags:
            priority += 1
        if "ranged_magic" in tags:
            priority += 1
        elif "ranged_physical" in tags and threat >= 11:
            priority += 1
        if "life_drain" in tags or "mana_drain" in tags:
            priority += 1
        if "resurrector" in tags or "summoner" in tags:
            priority += 1
        if "elite_unique" in tags or "act_boss" in tags:
            priority += 1
        if threat >= 11:
            priority += 1
        if 0 < threat <= 2:
            priority -= 1
        if family_group == "human" and threat <= 6 and "elite_unique" not in tags:
            priority = min(priority, 2)

        if super_critical_candidate:
            tags.add("super_critical_threat")
            tags.add("critical_threat")
            priority = max(priority, 6)
        else:
            priority = min(priority, 5)
            if critical_candidate or auto_critical_candidate:
                tags.add("critical_threat")
                priority = max(priority, 5)
            else:
                # Keep critical tightly scoped for practical target-priority use.
                priority = min(priority, 4)

        priority = max(1, min(6, priority))
    else:
        priority = 0

    threat_vector_primary, threat_vector_secondary = pick_threat_vectors(tags)
    mobility_class = compute_mobility_class(tags)
    engagement_profile = compute_engagement_profile(tags)
    pressure_ratings = compute_pressure_ratings(tags, threat, priority)

    needs_line_of_sight_break = (
        "lightning_sniper" in tags
        or ("ranged_magic" in tags and "elemental_lightning" in tags)
    )
    needs_corpse_control = (
        "on_death_hazard" in tags
        or "resurrector" in tags
        or "corpse_or_spawn_pressure" in tags
    )
    needs_debuff_response = "debuff_source" in tags or "curse" in tags

    avoidance_priority = (
        "super_critical_threat" in tags
        or "on_death_hazard" in tags
        or ("lightning_sniper" in tags and "elemental_lightning" in tags)
    )

    consensus = compute_consensus_metadata(joined, tags, priority, threat)
    target_priority_score = compute_target_priority_score(
        combat_relevant,
        priority,
        int(consensus["human_consensus_score"]),
        pressure_ratings,
        tags,
    )

    return {
        "combat_relevant": combat_relevant,
        "danger_priority": priority,
        "danger_label": danger_label(priority),
        "combat_tags": "|".join(sorted(tags)),
        "threat_vector_primary": threat_vector_primary,
        "threat_vector_secondary": threat_vector_secondary,
        "engagement_profile": engagement_profile,
        "mobility_class": mobility_class,
        "burst_pressure_rating": pressure_ratings["burst_pressure_rating"],
        "control_pressure_rating": pressure_ratings["control_pressure_rating"],
        "attrition_pressure_rating": pressure_ratings["attrition_pressure_rating"],
        "spawn_pressure_rating": pressure_ratings["spawn_pressure_rating"],
        "threat_rollup_rating": pressure_ratings["threat_rollup_rating"],
        "threat_intensity_rating": pressure_ratings["threat_intensity_rating"],
        "human_consensus_score": consensus["human_consensus_score"],
        "human_consensus_band": consensus["human_consensus_band"],
        "consensus_source_bucket": consensus["consensus_source_bucket"],
        "target_priority_score": target_priority_score,
        "avoidance_priority": avoidance_priority,
        "needs_line_of_sight_break": needs_line_of_sight_break,
        "needs_corpse_control": needs_corpse_control,
        "needs_debuff_response": needs_debuff_response,
        "is_light_mover": "light_mover" in tags,
        "is_exploder": "explode" in tags,
        "is_archer": "ranged_attacker" in tags,
        "is_ranged_attacker": "ranged_attacker" in tags,
        "is_life_drain": "life_drain" in tags,
        "is_mana_drain": "mana_drain" in tags,
        "is_viper_cloud": "viper_cloud" in tags,
        "is_frenzy_melee": "frenzy_melee" in tags,
        "is_projectile_burst": "projectile_burst" in tags,
        "is_debuff_source": "debuff_source" in tags,
        "is_critical_threat": "critical_threat" in tags,
        "is_super_critical_threat": "super_critical_threat" in tags,
    }

def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    """Write csv.

    Parameters:
        path: Parameter for path used in this routine.
        rows: Parameter for rows used in this routine.
        fieldnames: Parameter for fieldnames used in this routine.

    Local Variables:
        handle: Local variable for handle used in this routine.
        row: Local variable for row used in this routine.
        writer: Local variable for writer used in this routine.

    Returns:
        None.

    Side Effects:
        - May perform I/O or logging through called dependencies.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_summary(rows: List[Dict[str, object]], source_csv: Path) -> Dict[str, object]:
    """Build summary.

    Parameters:
        rows: Parameter for rows used in this routine.
        source_csv: Parameter for source csv used in this routine.

    Local Variables:
        avg_priority: Local variable for avg priority used in this routine.
        broad: Local variable for broad used in this routine.
        broad_archetype: Local variable for broad archetype used in this routine.
        broad_counts: Local variable tracking how many items are present or processed.
        combat_count: Local variable tracking how many items are present or processed.
        combat_counts: Local variable tracking how many items are present or processed.
        consensus_band: Local variable for consensus band used in this routine.
        consensus_band_counts: Local variable tracking how many items are present or processed.
        count: Local variable tracking how many items are present or processed.
        danger_counts: Local variable tracking how many items are present or processed.
        display_name: Local variable for display name used in this routine.
        engagement_profile: Local variable for engagement profile used in this routine.
        engagement_profile_counts: Local variable tracking how many items are present or processed.
        examples: Local variable for examples used in this routine.
        families: Local variable for families used in this routine.
        family_group: Local variable for family group used in this routine.
        group_combat_counts: Local variable tracking how many items are present or processed.
        group_counts: Local variable tracking how many items are present or processed.
        group_examples: Local variable for group examples used in this routine.
        group_key: Local variable for group key used in this routine.
        group_priority_max: Local variable for group priority max used in this routine.
        group_priority_totals: Local variable for group priority totals used in this routine.
        group_raw_families: Local variable for group raw families used in this routine.
        group_rows: Local variable for group rows used in this routine.
        mobility_class: Local variable for mobility class used in this routine.
        mobility_class_counts: Local variable tracking how many items are present or processed.
        priority: Local variable for priority used in this routine.
        priority_key: Local variable for priority key used in this routine.
        raw_counts: Local variable tracking how many items are present or processed.
        raw_family: Local variable for raw family used in this routine.
        raw_rows: Local variable for raw rows used in this routine.
        row: Local variable for row used in this routine.
        tag: Local variable for tag used in this routine.
        tags_value: Local variable for tags value used in this routine.
        threat_vector_primary_counts: Local variable tracking how many items are present or processed.
        trait_counts: Local variable tracking how many items are present or processed.
        unknown_rows: Local variable for unknown rows used in this routine.
        vector_primary: Local variable for vector primary used in this routine.

    Returns:
        A value matching the annotated return type `Dict[str, object]`.

    Side Effects:
        - May mutate mutable containers or objects in place.
    """
    broad_counts: Dict[str, int] = {}
    raw_counts: Dict[str, int] = {}
    group_counts: Dict[Tuple[str, str], int] = {}
    group_raw_families: Dict[Tuple[str, str], Set[str]] = {}
    group_examples: Dict[Tuple[str, str], List[str]] = {}

    combat_counts = {"combat_relevant": 0, "non_combat": 0}
    danger_counts: Dict[str, int] = {}
    trait_counts: Dict[str, int] = {}
    consensus_band_counts: Dict[str, int] = {}
    threat_vector_primary_counts: Dict[str, int] = {}
    engagement_profile_counts: Dict[str, int] = {}
    mobility_class_counts: Dict[str, int] = {}
    group_combat_counts: Dict[Tuple[str, str], int] = {}
    group_priority_totals: Dict[Tuple[str, str], int] = {}
    group_priority_max: Dict[Tuple[str, str], int] = {}

    unknown_rows: List[str] = []

    for row in rows:
        broad = str(row["broad_archetype"])
        raw_family = str(row["raw_family"] or "__blank__")
        group_key = (str(row["family_group"]), str(row["broad_archetype"]))

        broad_counts[broad] = broad_counts.get(broad, 0) + 1
        raw_counts[raw_family] = raw_counts.get(raw_family, 0) + 1
        group_counts[group_key] = group_counts.get(group_key, 0) + 1

        families = group_raw_families.setdefault(group_key, set())
        families.add(raw_family)

        examples = group_examples.setdefault(group_key, [])
        display_name = str(row.get("display_name", ""))
        if display_name and display_name not in examples and len(examples) < 8:
            examples.append(display_name)

        if row["family_group"] == "unknown_untyped":
            unknown_rows.append(str(row.get("monstats_id", "")))

        if bool(row.get("combat_relevant", False)):
            combat_counts["combat_relevant"] += 1
            priority = int(row.get("danger_priority", 0))
            priority_key = str(priority)
            danger_counts[priority_key] = danger_counts.get(priority_key, 0) + 1

            consensus_band = str(row.get("human_consensus_band", "")).strip()
            if consensus_band:
                consensus_band_counts[consensus_band] = consensus_band_counts.get(consensus_band, 0) + 1

            vector_primary = str(row.get("threat_vector_primary", "")).strip()
            if vector_primary:
                threat_vector_primary_counts[vector_primary] = threat_vector_primary_counts.get(vector_primary, 0) + 1

            engagement_profile = str(row.get("engagement_profile", "")).strip()
            if engagement_profile:
                engagement_profile_counts[engagement_profile] = engagement_profile_counts.get(engagement_profile, 0) + 1

            mobility_class = str(row.get("mobility_class", "")).strip()
            if mobility_class:
                mobility_class_counts[mobility_class] = mobility_class_counts.get(mobility_class, 0) + 1

            group_combat_counts[group_key] = group_combat_counts.get(group_key, 0) + 1
            group_priority_totals[group_key] = group_priority_totals.get(group_key, 0) + priority
            group_priority_max[group_key] = max(group_priority_max.get(group_key, 0), priority)
        else:
            combat_counts["non_combat"] += 1

        tags_value = str(row.get("combat_tags", "")).strip()
        if tags_value:
            for tag in tags_value.split("|"):
                tag = tag.strip()
                if not tag:
                    continue
                trait_counts[tag] = trait_counts.get(tag, 0) + 1

    group_rows = []
    for (family_group, broad_archetype), count in sorted(
        group_counts.items(), key=lambda item: (-item[1], item[0][0])
    ):
        combat_count = group_combat_counts.get((family_group, broad_archetype), 0)
        avg_priority = 0.0
        if combat_count > 0:
            avg_priority = group_priority_totals[(family_group, broad_archetype)] / combat_count

        group_rows.append(
            {
                "family_group": family_group,
                "broad_archetype": broad_archetype,
                "count": count,
                "combat_relevant_count": combat_count,
                "avg_danger_priority_combat": round(avg_priority, 2),
                "max_danger_priority_combat": group_priority_max.get((family_group, broad_archetype), 0),
                "raw_families": sorted(group_raw_families[(family_group, broad_archetype)]),
                "examples": group_examples[(family_group, broad_archetype)],
            }
        )

    raw_rows = [
        {"raw_family": raw_family, "count": count}
        for raw_family, count in sorted(raw_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_csv": source_csv.as_posix(),
        "row_count": len(rows),
        "distinct_raw_families": len(raw_counts),
        "distinct_family_groups": len(group_rows),
        "broad_archetype_counts": dict(
            sorted(broad_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "combat_counts": combat_counts,
        "danger_priority_counts": dict(
            sorted(danger_counts.items(), key=lambda item: int(item[0]))
        ),
        "human_consensus_band_counts": dict(
            sorted(consensus_band_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "threat_vector_primary_counts": dict(
            sorted(threat_vector_primary_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "engagement_profile_counts": dict(
            sorted(engagement_profile_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "mobility_class_counts": dict(
            sorted(mobility_class_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "trait_counts": dict(sorted(trait_counts.items(), key=lambda item: (-item[1], item[0]))),
        "family_group_counts": group_rows,
        "raw_family_counts": raw_rows,
        "unknown_untyped_rows": unknown_rows,
    }


def main() -> int:
    """Main.

    Parameters:
        None.

    Local Variables:
        args: Local variable for args used in this routine.
        combat_class: Local variable for combat class used in this routine.
        combat_output_csv: Local variable for combat output csv used in this routine.
        combat_rows: Local variable for combat rows used in this routine.
        compact_csv: Local variable for compact csv used in this routine.
        compact_rows: Local variable for compact rows used in this routine.
        family_class: Local variable for family class used in this routine.
        handle: Local variable for handle used in this routine.
        input_csv: Local variable for input csv used in this routine.
        item: Local variable for item used in this routine.
        output_dir: Local variable containing a filesystem location.
        raw_row: Local variable for raw row used in this routine.
        reader: Local variable for reader used in this routine.
        repo_root: Local variable for repo root used in this routine.
        row: Local variable for row used in this routine.
        row_fieldnames: Local variable for row fieldnames used in this routine.
        row_output_csv: Local variable for row output csv used in this routine.
        rows: Local variable for rows used in this routine.
        summary: Local variable for summary used in this routine.
        summary_json: Local variable for summary json used in this routine.

    Returns:
        A value matching the annotated return type `int`.

    Side Effects:
        - May mutate mutable containers or objects in place.
        - May perform I/O or logging through called dependencies.
    """
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    input_csv = resolve_path(repo_root, args.input_csv)
    output_dir = resolve_path(repo_root, args.output_dir)

    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    rows: List[Dict[str, object]] = []
    with input_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            family_class = classify_monster(raw_row)
            combat_class = classify_combat_profile(
                raw_row,
                family_group=family_class["family_group"],
                broad_archetype=family_class["broad_archetype"],
            )

            rows.append(
                {
                    "monstats_id": (raw_row.get("monstats_id") or "").strip(),
                    "display_name": (raw_row.get("display_name") or "").strip(),
                    "name_str": (raw_row.get("name_str") or "").strip(),
                    "base_id": (raw_row.get("base_id") or "").strip(),
                    "ai": (raw_row.get("ai") or "").strip(),
                    "enabled": (raw_row.get("enabled") or "").strip(),
                    "threat": (raw_row.get("threat") or "").strip(),
                    "superunique_refs": (raw_row.get("superunique_refs") or "").strip(),
                    "raw_family": family_class["raw_family"],
                    "family_group": family_class["family_group"],
                    "broad_archetype": family_class["broad_archetype"],
                    "family_source": family_class["family_source"],
                    "classification_confidence": family_class["classification_confidence"],
                    "combat_relevant": combat_class["combat_relevant"],
                    "danger_priority": combat_class["danger_priority"],
                    "danger_label": combat_class["danger_label"],
                    "combat_tags": combat_class["combat_tags"],
                    "threat_vector_primary": combat_class["threat_vector_primary"],
                    "threat_vector_secondary": combat_class["threat_vector_secondary"],
                    "engagement_profile": combat_class["engagement_profile"],
                    "mobility_class": combat_class["mobility_class"],
                    "burst_pressure_rating": combat_class["burst_pressure_rating"],
                    "control_pressure_rating": combat_class["control_pressure_rating"],
                    "attrition_pressure_rating": combat_class["attrition_pressure_rating"],
                    "spawn_pressure_rating": combat_class["spawn_pressure_rating"],
                    "threat_rollup_rating": combat_class["threat_rollup_rating"],
                    "threat_intensity_rating": combat_class["threat_intensity_rating"],
                    "human_consensus_score": combat_class["human_consensus_score"],
                    "human_consensus_band": combat_class["human_consensus_band"],
                    "consensus_source_bucket": combat_class["consensus_source_bucket"],
                    "target_priority_score": combat_class["target_priority_score"],
                    "avoidance_priority": combat_class["avoidance_priority"],
                    "needs_line_of_sight_break": combat_class["needs_line_of_sight_break"],
                    "needs_corpse_control": combat_class["needs_corpse_control"],
                    "needs_debuff_response": combat_class["needs_debuff_response"],
                    "is_light_mover": combat_class["is_light_mover"],
                    "is_exploder": combat_class["is_exploder"],
                    "is_archer": combat_class["is_archer"],
                    "is_ranged_attacker": combat_class["is_ranged_attacker"],
                    "is_life_drain": combat_class["is_life_drain"],
                    "is_mana_drain": combat_class["is_mana_drain"],
                    "is_viper_cloud": combat_class["is_viper_cloud"],
                    "is_frenzy_melee": combat_class["is_frenzy_melee"],
                    "is_projectile_burst": combat_class["is_projectile_burst"],
                    "is_debuff_source": combat_class["is_debuff_source"],
                    "is_critical_threat": combat_class["is_critical_threat"],
                    "is_super_critical_threat": combat_class["is_super_critical_threat"],
                }
            )

    rows.sort(
        key=lambda row: (
            int(row["danger_priority"]),
            str(row["family_group"]),
            str(row["display_name"]),
            str(row["monstats_id"]),
        ),
        reverse=True,
    )

    row_output_csv = output_dir / "monster_family_groups.csv"
    row_fieldnames = [
        "monstats_id",
        "display_name",
        "name_str",
        "base_id",
        "ai",
        "enabled",
        "threat",
        "superunique_refs",
        "raw_family",
        "family_group",
        "broad_archetype",
        "family_source",
        "classification_confidence",
        "combat_relevant",
        "danger_priority",
        "danger_label",
        "combat_tags",
        "threat_vector_primary",
        "threat_vector_secondary",
        "engagement_profile",
        "mobility_class",
        "burst_pressure_rating",
        "control_pressure_rating",
        "attrition_pressure_rating",
        "spawn_pressure_rating",
        "threat_rollup_rating",
        "threat_intensity_rating",
        "human_consensus_score",
        "human_consensus_band",
        "consensus_source_bucket",
        "target_priority_score",
        "avoidance_priority",
        "needs_line_of_sight_break",
        "needs_corpse_control",
        "needs_debuff_response",
        "is_light_mover",
        "is_exploder",
        "is_archer",
        "is_ranged_attacker",
        "is_life_drain",
        "is_mana_drain",
        "is_viper_cloud",
        "is_frenzy_melee",
        "is_projectile_burst",
        "is_debuff_source",
        "is_critical_threat",
        "is_super_critical_threat",
    ]
    write_csv(row_output_csv, rows, row_fieldnames)

    combat_rows = [row for row in rows if bool(row["combat_relevant"])]
    combat_output_csv = output_dir / "monster_combat_profiles.csv"
    write_csv(combat_output_csv, combat_rows, row_fieldnames)

    summary = build_summary(rows, input_csv)
    summary_json = output_dir / "monster_family_summary.json"
    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    compact_rows = []
    for item in summary["family_group_counts"]:
        compact_rows.append(
            {
                "family_group": item["family_group"],
                "broad_archetype": item["broad_archetype"],
                "monster_count": item["count"],
                "combat_relevant_count": item["combat_relevant_count"],
                "avg_danger_priority_combat": item["avg_danger_priority_combat"],
                "max_danger_priority_combat": item["max_danger_priority_combat"],
                "raw_families": "|".join(item["raw_families"]),
                "examples": "|".join(item["examples"]),
            }
        )

    compact_csv = output_dir / "monster_family_groups_by_family.csv"
    write_csv(
        compact_csv,
        compact_rows,
        [
            "family_group",
            "broad_archetype",
            "monster_count",
            "combat_relevant_count",
            "avg_danger_priority_combat",
            "max_danger_priority_combat",
            "raw_families",
            "examples",
        ],
    )

    print(f"Input rows: {len(rows)}")
    print(f"Combat-relevant rows: {len(combat_rows)}")
    print(f"Wrote: {row_output_csv}")
    print(f"Wrote: {combat_output_csv}")
    print(f"Wrote: {summary_json}")
    print(f"Wrote: {compact_csv}")
    print(f"Unknown rows: {len(summary['unknown_untyped_rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())