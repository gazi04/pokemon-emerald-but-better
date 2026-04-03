import arcade
import arcade.gui
from src.entities.pokemon import Pokemon

class BattleView(arcade.View):
    def __init__(self, pokemon_name, pokemon_data, overworld_view):
        super().__init__()
        self.overworld_view = overworld_view
        
        self.pokemon_name = pokemon_name
        self.your_pokemon = Pokemon(pokemon_name, pokemon_data, is_enemy=False)
        self.enemy_pokemon = Pokemon(pokemon_name, pokemon_data, is_enemy=True)

        self.manager = arcade.gui.UIManager()
        self.manager.enable()

    def on_draw(self):
        self.clear()
        
        self.enemy_pokemon.draw()
        self.your_pokemon.draw()
        
        self.manager.draw()

    def on_show_view(self):
        arcade.set_background_color(arcade.color.AMAZON)
        
    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            self.window.show_view(self.overworld_view)