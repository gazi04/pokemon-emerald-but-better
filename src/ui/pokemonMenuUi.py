import arcade
import arcade.gui

class PokemonMenuUi:
    def __init__(self):
        self.manager = arcade.gui.UIManager()
        self.manager._pixelated = True
        
        tilemap = arcade.load_tilemap("assets/ui/pokemonMenuUiDesign.tmx")
        uiLayer = tilemap.get_tilemap_layer("ui")
        
        self.pokemonUis = [{} for _ in range(6)]
        
        for obj in uiLayer.tiled_objects:
            w = obj.size.width
            h = obj.size.height
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y
            
            if obj.name == "background":
                self.manager.add(arcade.gui.UIImage(
                    texture=arcade.load_texture("assets/ui/sprites/pokemonMenuBg.png"),
                    x=x, y=y, width=w, height=h
                ))
            elif obj.name == "pokemon1":
                slot = int(obj.name[-1]) - 1
                button = arcade.gui.UIImage(
                    texture=arcade.load_texture("assets/ui/sprites/pokemonLead.png"),
                    x=x, y=y, width=w, height=h
                )
                self.pokemonUis[slot]["profile"] = button
                self.manager.add(button)
            elif "pokemon" in obj.name and "pokemonSprite" not in obj.name:
                slot = int(obj.name[-1]) - 1
                button = arcade.gui.UIImage(
                    texture=arcade.load_texture("assets/ui/sprites/pokemonProfile.png"),
                    x=x, y=y, width=w, height=h
                )
                self.pokemonUis[slot]["profile"] = button
                self.manager.add(button)

            elif "pokeball" in obj.name:
                slot = int(obj.name[-1]) - 1
                image = arcade.gui.UIImage(
                    texture=arcade.load_texture("assets/ui/sprites/pokeballProfile.png"),
                    x=x, y=y, width=w, height=h
                )
                self.pokemonUis[slot]["pokeball"] = image 
                self.manager.add(image)
            elif "pokemonSprite" in obj.name:
                slot = int(obj.name[-1]) - 1
                image = arcade.gui.UIImage(
                    texture=arcade.load_texture("assets/sprite/pokemon/question_mark.png"),
                    x=x, y=y, width=w, height=h
                )
                self.pokemonUis[slot]["pokemon"] = image
                self.manager.add(image)
            elif "hpText" in obj.name:
                slot = int(obj.name[-1]) - 1
                text = arcade.gui.UILabel(
                    text="50/50",
                    text_color=arcade.color.WHITE,
                    font_name="Pokemon Emerald",
                    font_size=15,
                    align="right",
                    x=x, y=y - h, width=w, height=h
                )
                self.pokemonUis[slot]["hpText"] = text
                self.manager.add(text)
            elif "levelText" in obj.name:
                slot = int(obj.name[-1]) - 1
                text = arcade.gui.UILabel(
                    text="Lv99",
                    text_color=arcade.color.WHITE,
                    font_name="Pokemon Emerald",
                    font_size=15,
                    x=x, y=y - h, width=w, height=h
                )
                self.pokemonUis[slot]["levelText"] = text
                self.manager.add(text)
            elif "nameText" in obj.name:
                slot = int(obj.name[-1]) - 1
                text = arcade.gui.UILabel(
                    text="Unknown",  
                    text_color=arcade.color.WHITE,
                    font_name="Pokemon Emerald",
                    font_size=15,
                    x=x, y=y - h, width=w, height=h
                )
                self.pokemonUis[slot]["nameText"] = text
                self.manager.add(text)
            elif obj.name == "box":
                self.manager.add(arcade.gui.UIImage(
                    texture=arcade.load_texture("assets/ui/sprites/box.png"),
                    x=x, y=y, width=w, height=h
                ))
            elif obj.name == "text":
                self.manager.add(arcade.gui.UILabel(
                    text="Choose Pokemon", 
                    text_color=arcade.color.BLACK,
                    font_name="Pokemon Emerald",
                    font_size=25,
                    x=x, y=y - h, width=w, height=h
                ))

    def draw(self):
        self.manager.draw()