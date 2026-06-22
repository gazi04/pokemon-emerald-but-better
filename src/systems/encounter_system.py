import random

from src.util import getEnc
from src.constants import ENCOUNTER_RATE
from src.core.data_loader import DataLoader
from src.model.state.player_motion import PlayerMotion
from src.core.event_bus import global_bus
from src.core.events import PlayerFinishedMoveEvent, BattleEncounterTriggeredEvent


class EncounterSystem:
    def __init__(
        self,
        bush_tiles: set[tuple[int, int]],
        player_state: PlayerMotion,
        data_loader: DataLoader,
    ):
        self._bush_tiles = bush_tiles  # set of (grid_x, grid_y) integer pairs
        self._player_state = player_state
        self.data_loader = data_loader
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
        # Pure logical check — O(1) set lookup, no arcade context needed
        if (event.grid_x, event.grid_y) not in self._bush_tiles:
            return

        if random.random() >= ENCOUNTER_RATE:
            return

        pokemon_list = getEnc()[self._player_state.map_name]["grass"]
        pokemon = random.choices(
            pokemon_list, weights=[p["weight"] for p in pokemon_list]
        )[0]

        pokemon_data = self.data_loader.get_pokemon(pokemon["name"])
        pokemon_lvl = random.randint(pokemon["levels"][0], pokemon["levels"][1])

        global_bus.publish(
            BattleEncounterTriggeredEvent(
                pokemon_name=pokemon["name"],
                pokemon_data=pokemon_data,
                pokemon_level=pokemon_lvl,
            )
        )
