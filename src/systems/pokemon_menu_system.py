from src.core.player_manager import PlayerManager


class PokemonMenuSystem:
    def __init__(self, player_manager: PlayerManager):
        self.player_manager = player_manager
        self.team = player_manager.player.pokemon

        self.moving_pokemon_index = 0
        self.is_moving_pokemon = False

        self.team_index = 0
        self.tooltip_index = 0

    # ♻️ todo: this method below isn't used in the project
    def start_switching(self, from_index: int):
        self.is_moving_pokemon = True
        self.moving_pokemon_index = from_index

    def confirm_switch(self, to_index: int) -> bool:
        if to_index == 0:
            return False

        if self.team[to_index].is_fainted:
            return False

        team = self.team
        team[0], team[to_index] = team[to_index], team[0]

        return True

    def move_pokemon(self, to: int):
        if to == self.moving_pokemon_index:
            self.cancel_moving()
            return

        self.team[to], self.team[self.moving_pokemon_index] = (
            self.team[self.moving_pokemon_index],
            self.team[to],
        )
        self.cancel_moving()

    def move_team_index(self, direction: int):
        self.team_index = (self.team_index + direction) % len(self.team)

    def move_tooltip_index(self, direction: int, option_count: int):
        self.tooltip_index = (self.tooltip_index + direction) % option_count

    def reset_tooltip(self):
        self.tooltip_index = 0

    def start_moving(self):
        self.is_moving_pokemon = True
        self.moving_pokemon_index = self.team_index

    def cancel_moving(self):
        self.is_moving_pokemon = False
        self.moving_pokemon_index = -1
