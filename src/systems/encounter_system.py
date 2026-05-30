import arcade
import random

from src.core.dataLoader import DataLoader
from src.util import getEnc
from src.constants import ENCOUNTER_RATE
from src.model.player import PlayerState
from src.core.event_bus import global_bus
from src.core.events import PlayerFinishedMoveEvent, BattleEncounterTriggeredEvent


class EncounterSystem:
    """
    Logic layer: Subscribes to PlayerFinishedMoveEvent and publishes
    BattleEncounterTriggeredEvent when a wild encounter is rolled.
    """

    def __init__(self, bush_layer, player_state: PlayerState, data_loader: DataLoader):
        self.data_loader = data_loader
        self._bush_layer = bush_layer
        self._player_state = player_state
        self._subscribed = False
        self.resubscribe()

    def resubscribe(self):
        if not self._subscribed:
            global_bus.subscribe(PlayerFinishedMoveEvent, self._on_player_moved)
            self._subscribed = True

    def cleanup(self):
        if self._subscribed:
            global_bus.unsubscribe(PlayerFinishedMoveEvent, self._on_player_moved)
            self._subscribed = False

    def _on_player_moved(self, event: PlayerFinishedMoveEvent):
        hit_bush = arcade.get_sprites_at_point(
            (self._player_state.pixel_x, self._player_state.pixel_y),
            self._bush_layer,
        )

        if not hit_bush:
            return

        if random.random() >= ENCOUNTER_RATE:
            return

        pokemon_list = getEnc()[self._player_state.map_name]["grass"]
        pokemon = random.choices(
            pokemon_list, weights=[p["weight"] for p in pokemon_list]
        )[0]

        pokemon_data = self.data_loader.getPokemon(pokemon["name"])
        pokemon_lvl = random.randint(pokemon["levels"][0], pokemon["levels"][1])

        global_bus.publish(
            BattleEncounterTriggeredEvent(
                pokemon_name=pokemon["name"],
                pokemon_data=pokemon_data,
                pokemon_level=pokemon_lvl,
            )
        )
