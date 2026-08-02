"""Tests for held-item battle hooks on BattlePokemon (Life Orb, type boosters,
Choice items, Rocky Helmet, Leftovers, pinch berries, Lum)."""

from src.model.battle.battle_pokemon import BattlePokemon
from src.model.static.item import ItemSpecies
from src.model.static.pokemon import (
    PokemonMove,
    PokemonSpecies,
    SpritePaths,
    PokemonStat,
)
from src.model.save.player import PlayerPokemon, PlayerPokemonMove
from src.enums.status_effect import StatusEffect
from src.enums.stat import Stat


def _item(**kw):
    raw = {
        "description": "",
        "price": 0,
        "category": "held_item",
        "holdable": True,
        "battle_condition": None,
        "battle_attributes": None,
        "effects": [],
    }
    raw.update({k: v for k, v in kw.items() if k != "name"})
    sp = ItemSpecies(raw)
    sp.name = kw.get("name", "Item")
    return sp


ITEMS = {
    "life orb": _item(
        name="Life Orb",
        battle_condition={"trigger": "on_attack"},
        battle_attributes={"damage_multiplier": 1.3},
        effects=[{"type": "recoil_to_self", "percent": 10}],
    ),
    "charcoal": _item(
        name="Charcoal",
        battle_condition={"trigger": "on_attack", "move_type": "fire"},
        battle_attributes={"damage_multiplier": 1.2},
    ),
    "choice band": _item(
        name="Choice Band",
        battle_attributes={"stat_multiplier": {"stat": "attack", "multiplier": 1.5}},
    ),
    "rocky helmet": _item(
        name="Rocky Helmet",
        battle_condition={"trigger": "on_hit", "contact_only": True},
        effects=[{"type": "recoil_to_attacker", "percent": 17}],
    ),
    "leftovers": _item(
        name="Leftovers",
        battle_condition={"trigger": "on_turn_end"},
        effects=[{"type": "heal", "percent": 6}],
    ),
    "sitrus berry": _item(
        name="Sitrus Berry",
        category="berry",
        battle_condition={"trigger": "hp_threshold", "threshold": 0.5},
        effects=[{"type": "heal", "percent": 25}],
    ),
    "salac berry": _item(
        name="Salac Berry",
        category="berry",
        battle_condition={"trigger": "hp_threshold", "threshold": 0.25},
        effects=[{"type": "stat", "stat": "speed", "change": 1}],
    ),
    "lum berry": _item(
        name="Lum Berry",
        category="berry",
        battle_condition={"trigger": "on_status", "status": "any"},
        effects=[{"type": "cure_status", "status": "all"}],
    ),
}


def _mon(item: str | None = None, frac=1.0, src_item=None):
    sp = PokemonSpecies(
        baseExp=62,
        catch_rate=45,
        abilities=[],
        types=["normal"],
        evolution=None,
        sprites=SpritePaths(back="b", front="f"),
        stats=PokemonStat(
            hp=100,
            attack=100,
            defence=100,
            special_attack=100,
            special_defence=100,
            speed=100,
        ),
        learnset=[],
    )
    pp = PlayerPokemon(
        "mon", 999, 50, 0, "x", [PlayerPokemonMove("tackle", 35)], src_item
    )
    b = BattlePokemon.from_player(
        None, sp, pp, False, held_item=ITEMS.get(item) if item else None
    )
    b.current_hp = int(b.max_hp * frac)
    return b, pp


def _move(type_="normal", category="physical", power=40):
    return PokemonMove("m", category, type_, power, 100, 35, 0, 0, None, None, [])


def test_life_orb_multiplier_and_recoil():
    mon, _ = _mon("life orb")
    assert mon.item_attack_multiplier(_move()) == 1.3
    before = mon.current_hp
    assert mon.item_recoil_self(_move()) and before - mon.current_hp == mon.max_hp // 10


def test_type_booster_only_matching_type():
    mon, _ = _mon("charcoal")
    assert round(mon.item_attack_multiplier(_move("fire")), 3) == 1.2
    assert mon.item_attack_multiplier(_move("water")) == 1.0


def test_choice_band_only_physical():
    mon, _ = _mon("choice band")
    assert mon.item_attack_multiplier(_move(category="physical")) == 1.5
    assert mon.item_attack_multiplier(_move(category="special")) == 1.0


def test_rocky_helmet_hurts_attacker_on_contact():
    defender, _ = _mon("rocky helmet")
    attacker, _ = _mon()
    before = attacker.current_hp
    assert defender.item_on_hit(attacker, _move(category="physical"))
    assert before - attacker.current_hp == int(attacker.max_hp * 17 / 100)
    assert defender.item_on_hit(_mon()[0], _move(category="special")) == []


def test_leftovers_heals_at_turn_end():
    mon, _ = _mon("leftovers", frac=0.5)
    before = mon.current_hp
    assert mon.item_turn_end() and mon.current_hp - before == int(mon.max_hp * 6 / 100)
    # No heal at full HP.
    assert _mon("leftovers")[0].item_turn_end() == []


def test_sitrus_berry_consumed_on_low_hp():
    mon, party = _mon("sitrus berry", frac=0.45, src_item="sitrus berry")
    before = mon.current_hp
    assert mon.consume_berry_on_hp()
    assert mon.current_hp == before + int(mon.max_hp * 25 / 100)
    assert mon.held_item is None and party.held_item is None  # consumed
    # Above threshold: no trigger.
    assert _mon("sitrus berry", frac=0.6)[0].consume_berry_on_hp() == []


def test_salac_berry_raises_speed():
    mon, _ = _mon("salac berry", frac=0.2)
    assert mon.consume_berry_on_hp()
    assert mon.modifiers[Stat.SPEED] == 1


def test_lum_berry_cures_status():
    mon, party = _mon("lum berry", src_item="lum berry")
    mon.status_effect = StatusEffect.SLEEP
    mon.sleep_counter = 3
    assert mon.consume_berry_on_status()
    assert mon.status_effect == StatusEffect.NONE and mon.sleep_counter == 0
    assert party.held_item is None
