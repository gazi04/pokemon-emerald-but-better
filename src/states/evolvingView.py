import arcade
import arcade.gui
import math
from src.constants import EVOLVING_UI, EVOLVE_IMAGE_SIZE, TEXT_DELAY
from src.core.event_bus import global_bus
from src.core.events import CloseViewEvent


class EvolvingView(arcade.View):
    def __init__(self, overworldView, pokemon, evolvedPokemon):
        super().__init__()

        # overworldView kept only for Director cache compatibility —
        # navigation is now done via CloseViewEvent.
        self.overworld = overworldView

        tilemap = arcade.load_tilemap(EVOLVING_UI)
        uiLayer = tilemap.get_tilemap_layer("ui")

        self.manager = arcade.gui.UIManager()
        self.manager.enable()
        self.manager._pixelated = True

        self.targetText = ""
        self.currentText = ""
        self.textDelayTimer = 0

        for obj in uiLayer.tiled_objects:
            w = obj.size.width
            h = obj.size.height
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y

            if obj.name == "dialogBox":
                self.manager.add(
                    arcade.gui.UIImage(
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                        texture=arcade.load_texture("assets/ui/sprites/dialogBox.png"),
                    )
                )
            elif obj.name == "background":
                self.background = arcade.gui.UIImage(
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    texture=arcade.load_texture("assets/ui/sprites/background.png"),
                )
                self.manager.add(self.background)
            elif obj.name == "text":
                self.dialogText = arcade.gui.UILabel(
                    text="TEST",
                    x=x,
                    y=y - h,
                    width=w,
                    height=h,
                    text_color=arcade.color.WHITE,
                    font_name="Pokemon Emerald",
                    font_size=25,
                )
                self.manager.add(self.dialogText)
            elif obj.name == "pokemon1":
                self.pokemon1 = arcade.gui.UIImage(
                    texture=arcade.load_texture(
                        f"assets/sprite/pokemon/front/{pokemon}_front.png"
                    ),
                    x=x,
                    y=y,
                    width=EVOLVE_IMAGE_SIZE,
                    height=EVOLVE_IMAGE_SIZE,
                )
                self.manager.add(self.pokemon1)
            elif obj.name == "pokemon2":
                self.pokemon2 = arcade.gui.UIImage(
                    texture=arcade.load_texture(
                        f"assets/sprite/pokemon/front/{evolvedPokemon}_front.png"
                    ),
                    x=x,
                    y=y,
                    width=EVOLVE_IMAGE_SIZE,
                    height=EVOLVE_IMAGE_SIZE,
                )
                self.manager.add(self.pokemon2)

        self.anim_timer = 0
        self.pulse_speed = 5
        self.is_evolving = False
        self.pokemon2.visible = False
        self.whichPokemon = False

        self.fadeTime = 2
        self.duration = 1
        self.fadeOutBackground = False
        self.fadeInBackground = False

        self.transition(pokemon.capitalize())

    def transition(self, pokemonName):
        self.targetText = f"What? {pokemonName} is evolving!"
        self.currentText = ""
        arcade.schedule_once(lambda dt: setattr(self, "fadeOutBackground", True), 0.7)
        arcade.schedule_once(lambda dt: setattr(self, "is_evolving", True), 2.7)

    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        self.manager.draw()

    def on_update(self, delta_time):
        self.textDelayTimer += delta_time

        if self.fadeOutBackground:
            self.fadeTime -= delta_time
            self.fadeTime = max(0, self.fadeTime)
            t = 1 - (self.fadeTime / self.duration)
            fade = 1 - (1 - (1 - t) * (1 - t))
            self.background.alpha = 255 * fade

        if self.fadeInBackground:
            self.fadeTime -= delta_time
            self.fadeTime = max(0, self.fadeTime)
            t = 1 - (self.fadeTime / self.duration)
            fade = 1 - (1 - t) * (1 - t)
            self.background.alpha = 255 * fade

        if self.is_evolving:
            self.anim_timer += delta_time
            self.pulse_speed += delta_time * 2

            scale = abs(math.sin(self.anim_timer * self.pulse_speed)) + 0.3
            size = EVOLVE_IMAGE_SIZE * scale

            if math.sin(self.anim_timer * self.pulse_speed) > 0:
                self.pokemon1.visible = True
                self.pokemon2.visible = False
                self.pokemon1.width = size
                self.pokemon1.height = size
            else:
                self.pokemon1.visible = False
                self.pokemon2.visible = True
                self.pokemon2.width = size
                self.pokemon2.height = size

            if self.pulse_speed > 25:
                self.finish_evolution()

        if len(self.currentText) < len(self.targetText):
            if self.textDelayTimer > TEXT_DELAY:
                self.currentText += self.targetText[len(self.currentText)]
                self.dialogText.text = self.currentText
                self.manager.trigger_render()
                self.textDelayTimer = 0

    def finish_evolution(self):
        self.is_evolving = False
        self.fadeInBackground = True
        self.fadeTime = 2

        self.pokemon1.visible = False
        self.pokemon2.visible = True
        self.pokemon2.width = EVOLVE_IMAGE_SIZE
        self.pokemon2.height = EVOLVE_IMAGE_SIZE
        self.targetText = "Congratulations! It evolved!"
        self.currentText = ""

        arcade.schedule_once(self.end, 1.5)

    def end(self, dt):
        # Tell the Director we are done — it returns to the Overworld
        global_bus.publish(CloseViewEvent())
