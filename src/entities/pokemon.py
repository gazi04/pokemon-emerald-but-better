import arcade
from src.util import getAMove, calculateMultiplier
import random

class Pokemon(arcade.Sprite):
    def __init__(self, name, data, moves, level=5, is_enemy=True, deathEvent: function = None, currentHp: int = None):
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
        self.deathEvent = deathEvent
        self.level = level
        
        self.max_hp = self.getStat("hp")
        self.current_hp = currentHp or self.max_hp

        self.modifiers = {"attack": 0, "defence": 0, "special_attack": 0, "special_defence": 0, "speed": 0, "accuracy": 0, "evasion": 0, "crits": 0}

        self.statusEffect = ""
        self.sleepCounter = 0

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
            self.deathEvent()

    def useMove(self, index: int, pokemon: Pokemon):
        move = getAMove(self.moves[index]["name"])
        
        text = []
        
        if self.statusEffect == "paralyzed" and random.random() < 0.25:
            return ["The Pokémon is fully paralyzed!"]

        if self.sleepCounter != 0 and self.statusEffect == "sleep":
            self.sleepCounter -= 1
            return [f"{self.name} was fast asleep."]
        elif self.sleepCounter == 0 and self.statusEffect == "sleep":
            self.statusEffect = ""
            text.append(f"{self.name} woke up!")

        if self.moves[index]["pp"] <= 0:
            return ["But there is no PP left!"]

        self.moves[index]["pp"] -= 1

        if not self.moveAccuracy(move["accuracy"]):
            return ["It missed."]

        self.damageFoePokemon(move, pokemon, text)
        self.executeEffects(move, pokemon, text)

        return text
    
    def moveAccuracy(self, accuracy):
        if not accuracy:
            return True
        
        stage = self.modifiers["accuracy"] - self.modifiers["evasion"]
        stage = max(-6, min(6, stage))
        
        multiplier = 1
        if stage < 0:
            multiplier = 3 / (3 - abs(stage))
        elif stage > 0:
            multiplier = (3 + stage) / 3
        
        finalAccuracy = accuracy * multiplier
        return random.randint(1, 100) <= finalAccuracy
    
    def damageFoePokemon(self, move, pokemon:Pokemon, text:list):
        if not move["power"]:
            return
        
        if move["category"] == "status":
            return
        
        isPhysical = move["category"] == "physical"
        
        d = pokemon.getStat("defence") if isPhysical else pokemon.getStat("special_defence")
        a = self.getStat("attack") if isPhysical else self.getStat("special_attack")
        
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
        if self.isCritical(move):
            d = pokemon.stats["defence"] if isPhysical else pokemon.stats["special_defence"]
            crit = 2
            text.append("A critical hit!")

        damage = (
            (((2 * self.level / 5 + 1) * move["power"] * a / d) / 50 + 2)
            * stab
            * mult
            * crit
        )

        pokemon.takeDamage(round(damage))

    def isCritical(self, move):
        tier = move.get("crit_ratio", 0) + self.modifiers["crits"]
        
        tier = min(tier, 4)
        
        probabilities = {0: 16, 1: 8, 2: 4, 3: 3, 4: 2}
        denominator = probabilities[tier]
    
        return random.randint(1, denominator) == 1

    def executeEffects(self, move, pokemon, text):        
        for effect in move["effects"]:
            destination = self if effect["target"] == "self" else pokemon
            
            if effect["type"] == "stat":
                stat = effect["stat"]
                change = effect["change"]
                
                current_stage = destination.modifiers[stat]

                if change > 0 and current_stage == 6:
                    text.append(f"{destination.name}'s {stat} won't go any higher!")
                    continue
                if change < 0 and current_stage == -6:
                    text.append(f"{destination.name}'s {stat} won't go any lower!")
                    continue

                destination.modifiers[stat] = max(-6, min(6, current_stage + change))
                
                if change > 0:
                    adj = "sharply " if change == 2 else ("drastically " if change >= 3 else "")
                    text.append(f"{destination.name}'s {stat} {adj}rose!")
                elif change < 0:
                    adj = "harshly " if change == -2 else ("severely " if change <= -3 else "")
                    text.append(f"{destination.name}'s {stat} {adj}fell!")
            else:
                chance = effect.get("chance", 100)
                
                if chance >= random.randint(1, 100):
                    destination.statusEffect = effect["condition"]
                    
                    if effect["condition"] == "sleep":
                        destination.sleepCounter = random.randint(2, 5)
   
    def afterATurn(self):
        text = []
        
        if self.statusEffect == "poison":
            damage = self.max_hp / 12.5
            self.takeDamage(damage)
            text.append(f"{self.name} is hurt by poison!")
        
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
            
        if stat == "speed" and self.statusEffect == "paralyzed":
            return round((self.stats[stat] * fraction) * 0.5)

        return round(self.stats[stat] * fraction)