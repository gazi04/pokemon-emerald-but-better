import arcade
import random
from src.util import getEnc
from src.constants import ENCOUNTER_RATE
from src.core.gameContext import dataLoader
from src.model.player import PlayerState

class EncounterSystem:
    """
    Logic layer: Processes game rules (like grass encounters)
    """
    def check_encounter(self, player_state: PlayerState, bush_layer) -> dict:
        """
        Check if the player triggers an encounter on their current tile.
        """
        hit_bush = arcade.get_sprites_at_point(
            (player_state.pixel_x, player_state.pixel_y), bush_layer
        )

        if not hit_bush:
            return None

        if random.random() < ENCOUNTER_RATE:
            pokemon_list = getEnc()[player_state.map_name]["grass"]
            pokemon = random.choices(
                pokemon_list, weights=[p["weight"] for p in pokemon_list]
            )[0]
            
            pokemon_data = dataLoader.getPokemon(pokemon["name"])
            pokemon_lvl = random.randint(pokemon["levels"][0], pokemon["levels"][1])
            
            return {
                "type": "encounter",
                "name": pokemon["name"],
                "data": pokemon_data,
                "level": pokemon_lvl,
            }

        return None
