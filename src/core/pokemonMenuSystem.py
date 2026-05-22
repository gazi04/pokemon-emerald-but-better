from src.core.gameContext import saveManager

class PokemonMenuSystem:
    def __init__(self):
        self.team = saveManager.player.pokemon
        
        self.movingPokemonIndex = 0
        self.isMovingPokemon = False
        
        self.teamIndex = 0
        self.tooltipIndex = 0
        
    def startSwitching(self, fromIndex: int):
        self.isMovingPokemon = True
        self.movingPokemonIndex = fromIndex  

    def confirmSwitch(self, toIndex: int) -> bool:
        if not self.isMovingPokemon:
            return False
        
        if self.movingPokemonIndex != 0 and toIndex != 0:
            return False
        
        if self.movingPokemonIndex == toIndex:
            return False

        team = self.team
        team[self.movingPokemonIndex], team[toIndex] = team[toIndex], team[self.movingPokemonIndex]
        
        self.cancelMoving()
        return True
        
    def movePokemon(self, to: int):
        self.cancelMoving()
        if to == self.movingPokemonIndex:
            return
        
        self.team[to], self.team[self.movingPokemonIndex] = self.team[self.movingPokemonIndex], self.team[to]
        
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
