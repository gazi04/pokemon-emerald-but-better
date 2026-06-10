from src.core.save_manager import SaveManager


class PokemonMenuSystem:
    def __init__(self, save_manager: SaveManager):
        self.save_manager = save_manager
        self.team = save_manager.player.pokemon

        self.movingPokemonIndex = 0
        self.isMovingPokemon = False

        self.teamIndex = 0
        self.tooltipIndex = 0
        
    def startSwitching(self, fromIndex: int):
        self.isMovingPokemon = True
        self.movingPokemonIndex = fromIndex  

    def confirmSwitch(self, toIndex: int) -> bool:
        if toIndex == 0:
            return False

        team = self.team
        team[0], team[toIndex] = team[toIndex], team[0]
        
        return True
        
    def movePokemon(self, to: int):
        if to == self.movingPokemonIndex:
            self.cancelMoving()
            return
        
        self.team[to], self.team[self.movingPokemonIndex] = self.team[self.movingPokemonIndex], self.team[to]
        self.cancelMoving()
        
    def moveTeamIndex(self, direction: int):
        self.teamIndex = (self.teamIndex + direction) % len(self.team)

    def moveTooltipIndex(self, direction: int, optionCount: int):
        self.tooltipIndex = (self.tooltipIndex + direction) % optionCount

    def resetTooltip(self):
        self.tooltipIndex = 0

    def startMoving(self):
        self.isMovingPokemon = True
        self.movingPokemonIndex = self.teamIndex

    def cancelMoving(self):
        self.isMovingPokemon = False
        self.movingPokemonIndex = -1
