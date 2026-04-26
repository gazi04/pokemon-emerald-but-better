import arcade
import arcade.gui
import math

class EvolvingView(arcade.View):
    def __init__(self, overworldView, pokemon, evolvedPokemon):
        super().__init__()
        
        self.overworld = overworldView

        tilemap = arcade.load_tilemap("assets/ui/evolvingUiDesign.tmx")
        uiLayer = tilemap.get_tilemap_layer("ui")
        
        self.manager = arcade.gui.UIManager()
        self.manager.enable()
        self.manager._pixelated = True
        
        self.targetText = f"What? {pokemon.capitalize()} is evolving!"
        self.currentText = ""
        self.textDelayTimer = 0
        
        for obj in uiLayer.tiled_objects:
            w = obj.size.width 
            h = obj.size.height
            
            x = obj.coordinates.x
            y = 600 - obj.coordinates.y
            
            if obj.name == "dialogBox":
                self.manager.add(arcade.gui.UIImage(
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    texture=arcade.load_texture("assets/ui/battle/dialogBox.png"),
                ))
            elif obj.name == "background":
                self.manager.add(arcade.gui.UIImage(
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    texture=arcade.load_texture("assets/ui/battle/background.png"),
                ))
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
                    texture=arcade.load_texture(f"assets/sprite/pokemon/front/{pokemon}_front.png"),
                    x=x,
                    y=y,
                    width=200,
                    height=200
                )
                
                self.manager.add(self.pokemon1)
            elif obj.name == "pokemon2":
                self.pokemon2 = arcade.gui.UIImage(
                    texture=arcade.load_texture(f"assets/sprite/pokemon/front/{evolvedPokemon}_front.png"),
                    x=x,
                    y=y,
                    width=200,
                    height=200
                )
                
                self.manager.add(self.pokemon2)
                
        self.anim_timer = 0
        self.pulse_speed = 5  
        self.is_evolving = True
        self.pokemon2.visible = False
        self.whichPokemon = False
    
    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        
        self.manager.draw()
    
    def on_update(self, delta_time):
        self.textDelayTimer += delta_time
        
        if self.is_evolving:
            self.anim_timer += delta_time
            self.pulse_speed += delta_time * 2 
            
            scale = abs(math.sin(self.anim_timer * self.pulse_speed)) + 0.3
            
            if math.sin(self.anim_timer * self.pulse_speed) > 0:
                self.pokemon1.visible = True
                self.pokemon2.visible = False
                self.pokemon1.width = 200 * scale
                self.pokemon1.height = 200 * scale
            else:
                self.pokemon1.visible = False
                self.pokemon2.visible = True
                self.pokemon2.width = 200 * scale
                self.pokemon2.height = 200 * scale

            if self.pulse_speed > 25: 
                self.finish_evolution()
        
        if len(self.currentText) < len(self.targetText):
            if self.textDelayTimer > 0.03:
                self.currentText += self.targetText[len(self.currentText)]
                self.dialogText.text = self.currentText
                self.manager.trigger_render()
                self.textDelayTimer = 0
            
    def finish_evolution(self):
        self.is_evolving = False
        self.pokemon1.visible = False
        self.pokemon2.visible = True
        self.pokemon2.width = 200 
        self.pokemon2.height = 200
        self.targetText = "Congratulations! It evolved!"
        self.currentText = ""
    
if __name__ == "__main__":
    window = arcade.Window(
        width=800,
        height=600,
    )

    start_view = EvolvingView(None, "torchip", "combusken")
    window.show_view(start_view)
    arcade.run()