from src.core.gameContext import saveManager

class PokemonMenuSystem:
    def __init__(self):
        self.team = saveManager.player.pokemon
        
        self.movingPokemonIndex = 0
        self.isMovingPokemon = False
        
        self.teamIndex = 0
        self.tooltipIndex = 0
    
    def movePokemon(self, to: int):
        if to == self.movingPokemonIndex:
            self.isMovingPokemon = False
            return
        
        self.team[to], self.team[self.movingPokemonIndex] = self.team[self.movingPokemonIndex], self.team[to]
        
        self.isMovingPokemon = False
        
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
        self.movingPokemonIndex = None
