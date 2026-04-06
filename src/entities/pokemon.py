import arcade

class Pokemon(arcade.Sprite):
    def __init__(self, name, data, moves, level=5, is_enemy=True):
        sprite_path = data["sprites"]["back"] if is_enemy else data["sprites"]["front"]
        
        super().__init__(sprite_path.strip(), scale=3.0)
        
        self.name = name.capitalize()
        self.data = data
        self.moves = moves
        
        self.max_hp = data["stats"]["hp"]
        self.current_hp = self.max_hp
        self.level = level

        if is_enemy:
            self.center_x = 235 
            self.center_y = 235
        else:
            self.center_x = 470 
            self.center_y = 400

    def draw(self):
        arcade.draw_sprite(self, pixelated=True)
    
    def get_hp_ratio(self):
        return self.current_hp / self.max_hp