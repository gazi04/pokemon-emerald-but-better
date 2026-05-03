import arcade
import arcade.gui

class BagView(arcade.View):
    def __init__(self):
        super().__init__()
        
        self.manager = arcade.gui.UIManager()
        self.manager._pixelated = True
        
        tilemap = arcade.load_tilemap("assets/ui/bagUiDesign.tmx")
        uiLayer = tilemap.get_tilemap_layer("ui")
        
        for obj in uiLayer.tiled_objects:
            w = obj.size.width
            h = obj.size.height

            x = obj.coordinates.x
            y = 600 - obj.coordinates.y
            
            if obj.name == "background":
                self.manager.add(
                    arcade.gui.UIImage(
                        texture=arcade.load_texture("assets/ui/sprites/bagUi.png"),
                        width=w,
                        height=h,
                        x=x,
                        y=y
                    )
                )
        
    def on_draw(self):
        self.clear()
        self.window.default_camera.use()

        self.manager.draw()
        
if __name__ == "__main__":
    window = arcade.Window(
        width=800,
        height=600,
    )

    start_view = BagView()
    window.show_view(start_view)
    arcade.run()