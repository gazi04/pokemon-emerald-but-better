import arcade
from src.util import getAMove, calculateMultiplier
import random

class Pokemon(arcade.Sprite):
    def __init__(self, name, data, moves, level=5, is_enemy=True, run: function = None):
        sprite_path = data["sprites"]["front"] if is_enemy else data["sprites"]["back"]

        super().__init__(sprite_path.strip(), scale=3.0)

        self.name = name.capitalize()
        
        self.stats = data["stats"].copy()
        
        for key, value in data["stats"].items():
            if key != "hp":
                self.stats[key] = ((2 * value * level) // 100) + 5
            else:
                self.stats[key] = ((2 * value * level) // 100) + 5 + level

        self.types = data["types"]
        self.moves = moves
        self.run = run

        self.modifiers = {"attack": 0, "defense": 0, "special_attack": 0, "special_defense": 0, "speed": 0, "accuracy": 0}

        if is_enemy:
            self.center_x = 580
            self.center_y = 400
        else:
            self.center_x = 210
            self.center_y = 230

    def draw(self):
        arcade.draw_sprite(self, pixelated=True)

    def takeDamage(self, damage: int):
        self.current_hp -= damage
        if self.current_hp < 0:
            self.current_hp = 0
            self.run()

    def useMove(self, index: int, pokemon: Pokemon):
        move = getAMove(self.moves[index]["name"])

        roll = random.randint(1, 100)

        if self.moves[index]["pp"] <= 0:
            return ["But there is no PP left!"]

        self.moves[index]["pp"] -= 1

        if move["accuracy"] < roll:
            return ["It missed."]

        text = []

        d = pokemon.getStat("defence")
        a = self.getStat("attack")
        if not move["isPhysical"]:
            d = pokemon.getStat("special_defence")
            a = self.getStat("special_attack")

        stab = 1

        if move["type"] in self.types:
            stab = 1.5

        mult = calculateMultiplier(move["type"], pokemon.types)

        if mult >= 2:
            text.append("Its super effective.")
        elif mult < 1:
            text.append("Its not very effective.")
        elif mult == 0:
            text.append("No effect.")

        crit = 1
        if random.random() < 17 / 256:
            crit = 2
            text.append("A critical hit!")

        damage = (
            (((2 * self.level / 5 + 1) * move["power"] * a / d) / 50 + 2)
            * stab
            * mult
            * crit
        )

        pokemon.takeDamage(round(damage))

        return text

    def getHpRatio(self):
        return self.current_hp / self.max_hp

    def getStat(self, stat):
        if stat == "hp":
            return self.stats[stat]

        fraction = 1

        if self.modifiers[stat] > 0:
            fraction = (2 + self.modifiers[stat]) / 2
        elif self.modifiers[stat] < 0:
            fraction = 2 / (2 + abs(self.modifiers[stat]))

        return round(self.stats[stat] * fraction)

