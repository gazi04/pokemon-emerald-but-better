import arcade
import arcade.gui

class EvolvingView(arcade.View):
    def __init__(self, overworldView, pokemonSprite, evolvedPokemonSprite):
        super().__init__()
        
        self.overworld = overworldView

        tilemap = arcade.load_tilemap("assets/ui/evolvingUiDesign.tmx")
        uiLayer = tilemap.get_tilemap_layer("ui")
        
        self.manager = arcade.gui.UIManager()
        self.manager.enable()
        self.manager._pixelated = True
        
        self.targetText = ""
        self.currentText = ""
        self.textDelayTimer = 0
        self.messageQueue = ["TEST", "TESTEST", "TESTESTEST"]
        self.isProcessingText = False
        
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
    
        self.nextMessage()
    
    def on_draw(self):
        self.clear()
        self.window.default_camera.use()
        
        self.manager.draw()
        
    def nextMessage(self):
        if self.messageQueue:
            self.targetText = self.messageQueue.pop(0)
            self.currentText = ""
            self.isProcessingText = True
        else:
            self.isProcessingText = False
    
    def on_update(self, delta_time):
        self.textDelayTimer += delta_time
        
        if len(self.currentText) < len(self.targetText):
            if self.textDelayTimer > 0.03:
                self.currentText += self.targetText[len(self.currentText)]
                self.dialogText.text = self.currentText
                self.manager.trigger_render()
                self.textDelayTimer = 0
        elif self.isProcessingText:
            if self.textDelayTimer > 1.5:
                self.nextMessage()
                self.textDelayTimer = 0
            
if __name__ == "__main__":
    window = arcade.Window(
        width=800,
        height=600,
    )

    start_view = EvolvingView(None, None, None)
    window.show_view(start_view)
    arcade.run()