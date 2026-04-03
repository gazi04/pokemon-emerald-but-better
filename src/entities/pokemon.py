import arcade

class Pokemon(arcade.Sprite):
    def __init__(self, name, data, level=5, is_enemy=True):
        sprite_path = data["sprites"]["back"] if is_enemy else data["sprites"]["front"]
    
        super().__init__(sprite_path.strip(), scale=3.0)
        
        self.name = name.capitalize()
        self.data = data
        
        self.max_hp = data["stats"]["hp"]
        self.current_hp = self.max_hp
        self.level = level

        if is_enemy:
            self.center_x = 400 
            self.center_y = 400
        else:
            self.center_x = 900 
            self.center_y = 600

    def draw(self):
        arcade.draw_sprite(self)
        
        ui_x = self.center_x
        ui_y = self.top + 20 
        
        arcade.draw_text(f"{self.name} Lv{self.level}", 
                         ui_x, ui_y + 15, 
                         arcade.color.BLACK, 14, 
                         anchor_x="center")

        bar_width = 100
        arcade.draw_lbwh_rectangle_filled(ui_x, ui_y, bar_width, 10, arcade.color.GRAY)

        health_ratio = self.current_hp / self.max_hp
        current_bar_width = bar_width * health_ratio
        
        x_offset = (bar_width - current_bar_width) / 2
        
        arcade.draw_lbwh_rectangle_filled(ui_x - x_offset, ui_y, 
                                     current_bar_width, 10, 
                                     arcade.color.GREEN)