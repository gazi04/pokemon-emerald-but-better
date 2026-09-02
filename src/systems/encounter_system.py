import random

from src.constants import ENCOUNTER_RATE
from src.core.data_loader import DataLoader
from src.core.event_bus import global_bus
from src.core.events import PlayerFinishedMoveEvent, BattleEncounterTriggeredEvent


class EncounterSystem:
    def __init__(
        self,
        bush_tiles: set[tuple[int, int]],
        data_loader: DataLoader,
    ):
        self._bush_tiles = bush_tiles  # set of (grid_x, grid_y) integer pairs
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

        # The event carries the map the player just landed on — use it rather
        # than re-reading the cached PlayerMotion. They agree today (Movement
        # System publishes from the same object), but two sources for one fact
        # meant the event's payload was dead input.
        table = self.data_loader.encounters.get(event.map_name)
        if not table:
            return

        if random.random() >= table.get("encounter_rate", ENCOUNTER_RATE):
            return

        # A water/fishing-only table, or an empty grass list, is a legitimate
        # authoring outcome — bail like the missing-table guard above rather than
        # raising KeyError here or IndexError inside random.choices.
        pokemon_list = table.get("grass")
        if not pokemon_list:
            return

        pokemon = random.choices(
            pokemon_list, weights=[p["weight"] for p in pokemon_list]
        )[0]

        pokemon_data = self.data_loader.require_pokemon(pokemon["name"])
        pokemon_lvl = random.randint(pokemon["levels"][0], pokemon["levels"][1])

        global_bus.publish(
            BattleEncounterTriggeredEvent(
                pokemon_name=pokemon["name"],
                pokemon_data=pokemon_data,
                pokemon_level=pokemon_lvl,
            )
        )
