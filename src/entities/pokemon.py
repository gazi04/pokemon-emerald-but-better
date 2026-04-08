import arcade
from src.util import getAMove, calculateMultiplier
import random


class Pokemon(arcade.Sprite):
    def __init__(self, name, data, moves, level=5, is_enemy=True, run: function = None):
        sprite_path = data["sprites"]["front"] if is_enemy else data["sprites"]["back"]

        super().__init__(sprite_path.strip(), scale=3.0)

        self.name = name.capitalize()
        self.data = data
        self.moves = moves
        self.run = run

        self.max_hp = data["stats"]["hp"]
        self.current_hp = self.max_hp
        self.level = level

        if is_enemy:
            self.center_x = 470
            self.center_y = 400
        else:
            self.center_x = 235
            self.center_y = 235

    def draw(self):
        arcade.draw_sprite(self, pixelated=True)

    def takeDamage(self, damage: int):
        self.current_hp -= damage
        if self.current_hp < 0:
            self.current_hp = 0
            self.run()

    def useMove(self, index: int, pokemon: Pokemon):
        move = getAMove(self.moves[index]["name"])
        if self.moves[index]["pp"] > 0:
            text = []
            
            d = pokemon.data["stats"]["defence"]
            a = self.data["stats"]["attack"]
            if not move["isPhysical"]:
                d = pokemon.data["stats"]["special_defence"]
                a = self.data["stats"]["special_attack"]

            stab = 1

            if move["type"] in self.data["types"]:
                stab = 1.5

            mult = calculateMultiplier(move["type"], pokemon.data["types"])

            damage = (
                (((2 * self.level / 5 + 1) * move["power"] * a / d) / 50 + 2)
                * stab
                * mult
            )
            pokemon.takeDamage(damage)
            self.moves[index]["pp"] -= 1

    def getHpRatio(self):
        return self.current_hp / self.max_hp
