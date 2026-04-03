import arcade

class Pokemon(arcade.Sprite):
    def __init__(self, name, data, is_enemy=True):
        sprite_path = data["sprites"]["front"]
        if is_enemy:
            sprite_path = data["sprites"]["back"]
    
        super().__init__(sprite_path, scale=3.0)
        
        self.name = name.capitalize()
        self.data = data
        
        self.max_hp = data["stats"]["hp"]
        self.current_hp = self.max_hp
        self.level = 5  

        if is_enemy:
            self.center_x = 600 
            self.center_y = 400
        else:
            self.center_x = 200 
            self.center_y = 200

    def take_damage(self, amount):
        self.current_hp -= amount
        if self.current_hp < 0:
            self.current_hp = 0
            
    def is_fainted(self):
        return self.current_hp <= 0