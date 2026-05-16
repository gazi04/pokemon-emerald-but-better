import arcade
import arcade.gui
from src.model.player import PlayerPokemon
from src.core.gameContext import dataLoader


class PokemonMenuUi:
    def __init__(self):
        self.manager = arcade.gui.UIManager()
        self.manager._pixelated = True

        tilemap = arcade.load_tilemap("assets/ui/pokemonMenuUiDesign.tmx")
        uiLayer = tilemap.get_tilemap_layer("ui")

        self._profileTexture = arcade.load_texture(
            "assets/ui/sprites/pokemonProfile.png")
        self._profileSelectedTexture = arcade.load_texture(
            "assets/ui/sprites/pokemonProfileSelected.png")
        self._leadTexture = arcade.load_texture(
            "assets/ui/sprites/pokemonLead.png")
        self._leadSelectedTexture = arcade.load_texture(
            "assets/ui/sprites/pokemonLeadSelected.png")
        self._emptyTexture = arcade.load_texture(
            "assets/ui/sprites/emptyProfile.png")

        self._pokemonUis = [{} for _ in range(6)]
        
        self._tooltip = arcade.gui.UIWidget()
        self._tooltip.visible = False
        self._tooltipButtons = []

        for obj in uiLayer.tiled_objects:
            w = obj.size.width
            h = obj.size.height
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y

            if obj.name == "background":
                self.manager.add(arcade.gui.UIImage(
                    texture=arcade.load_texture(
                        "assets/ui/sprites/pokemonMenuBg.png"),
                    x=x, y=y, width=w, height=h
                ))
            elif obj.name == "tooltip":
                self._tooltip.add(arcade.gui.UIImage(
                    texture=arcade.load_texture("assets/ui/sprites/box2.png"),
                    x=0, y=0,
                    width=w, height=h
                ))
            elif obj.name == "info":
                text = arcade.gui.UILabel(
                    text="Info",
                    text_color=arcade.color.BLACK,
                    font_name="Pokemon Emerald",
                    font_size=15,
                    x=0, y=y - h,
                    width=w, height=h
                )
                self._tooltip.add(text)
                self._tooltipButtons.append(text)
            elif obj.name == "move":
                text = arcade.gui.UILabel(
                    text="Move",
                    text_color=arcade.color.BLACK,
                    font_name="Pokemon Emerald",
                    font_size=15,
                    x=0, y=y - h,
                    width=w, height=h
                )
                self._tooltip.add(text)
                self._tooltipButtons.append(text)
            elif obj.name == "pokemon1":
                slot = int(obj.name[-1]) - 1
                button = arcade.gui.UIImage(
                    texture=self._leadTexture,
                    x=x, y=y, width=w, height=h
                )
                self._pokemonUis[slot]["profile"] = button
                self.manager.add(button)
            elif "pokemon" in obj.name and "pokemonSprite" not in obj.name:
                slot = int(obj.name[-1]) - 1
                button = arcade.gui.UIImage(
                    texture=self._profileTexture,
                    x=x, y=y, width=w, height=h
                )
                self._pokemonUis[slot]["profile"] = button
                self.manager.add(button)

            elif "pokeball" in obj.name:
                slot = int(obj.name[-1]) - 1
                image = arcade.gui.UIImage(
                    texture=arcade.load_texture(
                        "assets/ui/sprites/pokeballProfile.png"),
                    x=x, y=y, width=w, height=h
                )
                self._pokemonUis[slot]["pokeball"] = image
                self.manager.add(image)
            elif "pokemonSprite" in obj.name:
                slot = int(obj.name[-1]) - 1
                image = arcade.gui.UIImage(
                    texture=arcade.load_texture(
                        "assets/sprite/pokemon/question_mark.png"),
                    x=x, y=y, width=w, height=h
                )
                self._pokemonUis[slot]["pokemon"] = image
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
                self._pokemonUis[slot]["hpText"] = text
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
                self._pokemonUis[slot]["levelText"] = text
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
                self._pokemonUis[slot]["nameText"] = text
                self.manager.add(text)
            elif "hpBar" in obj.name:
                slot = int(obj.name[-1]) - 1
                self._pokemonUis[slot]["hpBar"] = {
                    "x": x,
                    "y": y - h,
                    "w": w,
                    "h": h,
                }
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
        
        self.manager.add(self._tooltip)
        
        self.cursorText = arcade.Text(
            "▶",
            0, 0,
            arcade.color.RED,
            font_size=12,
            anchor_y="center",
            font_name="Pokemon Emerald"
        )

    def setValues(self, pokemons: list[PlayerPokemon]):
        SKIP_KEYS = {"hpBar", "profile"}

        for i, slot in enumerate(self._pokemonUis):
            if i < len(pokemons):
                pokemon = pokemons[i]
                pokemonProfile = dataLoader.getPokemon(pokemon.name)
                maxHp = ((2 * pokemonProfile.stats.hp *
                         pokemon.level) // 100) + 5 + pokemon.level

                slot["nameText"].text = pokemon.name.upper()
                slot["levelText"].text = f"Lv{pokemon.level}"
                slot["hpText"].text = f"{pokemon.hp}/{maxHp}"
                slot["pokemon"].texture = arcade.load_texture(
                    pokemonProfile.sprites.front)

                for key, element in slot.items():
                    if key not in SKIP_KEYS:
                        element.visible = True

                if i == 0:
                    slot["profile"].texture = self._leadTexture
                else:
                    slot["profile"].texture = self._profileTexture
            else:
                for key, element in slot.items():
                    if key not in SKIP_KEYS:
                        element.visible = False

                slot["profile"].texture = self._emptyTexture
                
        self.selectPokemon(0)

    def selectPokemon(self, index: int):
        for i, ui in enumerate(self._pokemonUis):
            if ui["profile"].texture == self._emptyTexture:
                continue
            
            if i == index:
                ui["profile"].texture = self._leadSelectedTexture if i == 0 else self._profileSelectedTexture
            else:
                ui["profile"].texture = self._leadTexture if i == 0 else self._profileTexture
                
            for key, element in ui.items():
                if key != "hpBar":
                    self.manager.remove(element)
                    self.manager.add(element)

    def isTooltipShowing(self) -> bool:
        return self._tooltip.visible

    def selectTooltipOption(self, index: int):
        self.cursorText.x = self._tooltipButtons[len(self._tooltipButtons) - 1 - index].rect.left - 10
        self.cursorText.y = self._tooltipButtons[len(self._tooltipButtons) - 1 - index].rect.center_y

    def showTooltip(self, index:int):
        self._tooltip.visible = True
        self.cursorText.visible = True
        
        for i, element in enumerate(self._tooltip.children):
            x = self._pokemonUis[index]["profile"].rect.right if index == 0 else self._pokemonUis[index]["profile"].rect.left
            
            x += (element.width // 2) + 5 + (15 if i > 0 else 0) if index == 0 else -(element.width // 2) - 5 + (5 if i > 0 else 0)
            
            element.center_x = x
            element.center_y = self._pokemonUis[index]["profile"].rect.center_y + (element.height * i) + 5
        
        self.selectTooltipOption(0)

    def hideTooltip(self):
        self._tooltip.visible = False
        self.cursorText.visible = False

    def drawHpBars(self, pokemons: list[PlayerPokemon]):
        for i, pokemon in enumerate(pokemons):
            pokemonProfile = dataLoader.getPokemon(pokemon.name)
            maxHp = ((2 * pokemonProfile.stats.hp * pokemon.level) //
                     100) + 5 + pokemon.level

            self._drawHpBar(pokemon.hp / maxHp, i)

    def _drawHpBar(self, ratio: float, index: int):
        barData = self._pokemonUis[index]["hpBar"]

        fullWidth = barData["w"]
        currentWidth = fullWidth * ratio

        color = arcade.color.GREEN
        if ratio < 0.2:
            color = arcade.color.RED
        elif ratio < 0.5:
            color = arcade.color.GOLD

        arcade.draw_lrbt_rectangle_filled(
            left=barData["x"],
            right=barData["x"] + currentWidth,
            bottom=barData["y"],
            top=barData["y"] + barData["h"],
            color=color,
        )

    def draw(self):
        self.manager.draw()
        self.cursorText.draw()
