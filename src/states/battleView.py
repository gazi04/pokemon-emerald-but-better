import arcade
import arcade.gui
from src.entities.pokemon import Pokemon

class BattleView(arcade.View):
    def __init__(self, pokemon_name, pokemon_data, overworld_view):
        super().__init__()
        self.overworld_view = overworld_view
        
        self.pokemon_name = pokemon_name
        self.wild_pokemon = Pokemon(pokemon_name, pokemon_data, is_enemy=True)

        self.title_label = arcade.Text(
            text=f"A wild {self.wild_pokemon.name} appeared!",
            x=400, y=550, color=arcade.color.WHITE,
            font_size=20, anchor_x="center"
        )

        self.manager = arcade.gui.UIManager()
        self.manager.enable()

    def on_draw(self):
        self.clear()
        
        self.wild_pokemon.draw()
        
        self.title_label.draw()
        self.manager.draw()

    def on_show_view(self):
        arcade.set_background_color(arcade.color.AMAZON)

    def on_draw(self):
        self.clear()
        self.manager.draw()
        
        arcade.draw_text(f"Level 5 {self.pokemon_name.capitalize()}", 
                         self.window.width/2, self.window.height - 50, 
                         arcade.color.WHITE, font_size=20, anchor_x="center")

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            self.window.show_view(self.overworld_view)