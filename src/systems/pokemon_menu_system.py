from src.core.player_manager import PlayerManager


class PokemonMenuSystem:
    def __init__(self, player_manager: PlayerManager):
        self.player_manager = player_manager
        self.team = player_manager.player.pokemon

        self.movingPokemonIndex = 0
        self.isMovingPokemon = False

        self.teamIndex = 0
        self.tooltipIndex = 0

    # ♻️ todo: this method below isn't used in the project
    def start_switching(self, fromIndex: int):
        self.isMovingPokemon = True
        self.movingPokemonIndex = fromIndex

    def confirm_switch(self, toIndex: int) -> bool:
        if toIndex == 0:
            return False

        if self.team[toIndex].is_fainted:
            return False

        team = self.team
        team[0], team[toIndex] = team[toIndex], team[0]

        return True

    def move_pokemon(self, to: int):
        if to == self.movingPokemonIndex:
            self.cancel_moving()
            return

        self.team[to], self.team[self.movingPokemonIndex] = (
            self.team[self.movingPokemonIndex],
            self.team[to],
        )
        self.cancel_moving()

    def move_team_index(self, direction: int):
        self.teamIndex = (self.teamIndex + direction) % len(self.team)

    def move_tooltip_index(self, direction: int, optionCount: int):
        self.tooltipIndex = (self.tooltipIndex + direction) % optionCount

    def reset_tooltip(self):
        self.tooltipIndex = 0

    def start_moving(self):
        self.isMovingPokemon = True
        self.movingPokemonIndex = self.teamIndex

    def cancel_moving(self):
        self.isMovingPokemon = False
        self.movingPokemonIndex = -1
