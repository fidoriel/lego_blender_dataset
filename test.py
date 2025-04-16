import bpy
from pathlib import Path
import platform
import io_scene_importldraw.loadldraw.loadldraw as ldload

print(f"Python Version: {platform.python_version()}")

LDRAW_ADDON_NAME = "io_scene_importldraw"
BRICK = "3001"

class Settings:
    ldraw_path: Path = Path("./ldraw/")
    plugin_installer: Path = Path("./importldraw1.2.1.zip")
    render_resolution: int = 128
    output_path: Path = Path("./render.png")

    @property
    def plugin_dir(self) -> Path:
        return Path(bpy.utils.user_resource('SCRIPTS')) / "addons" / LDRAW_ADDON_NAME

    @property
    def plugin_ini(self) -> Path:
        return self.plugin_dir / "ImportLDrawPreferences.ini"

    def get_part_path(self, id: str) -> Path:
        return self.ldraw_path / "parts" / f"{id}.dat"
    
    def load_plugin_settings(self) -> None:
        ldload.Options.ldrawDirectory = "/home/luca/git/lego_blender/ldraw"
        ldload.Options.useLogoStuds = True
        ldload.Options.addGroundPlane = False
        ldload.Options.realScale = 200
    
    def load_plugin(self) -> None:
        print(f"installing {self.plugin_installer.resolve()}")
        bpy.ops.preferences.addon_install(filepath=str(self.plugin_installer.resolve()))

    def place_config(self) -> None:
        cfg = """[importldraw]
ldrawdirectory = /home/luca/git/lego_blender/ldraw
useunofficialparts = False
uselogostuds = True
addenvironment = True
realscale = 200.0
resolution = Standard
smoothshading = True
beveledges = True
bevelwidth = 0.5
uselook = normal
usecolourscheme = lgeo
gaps = False
realgapwidth = 0.00020000000298023223
curvedwalls = True
importcameras = True
linkparts = True
numbernodes = True
positionobjectongroundatorigin = True
flattenhierarchy = False
minifighierarchy = True
instancestuds = False
resolvenormals = guess
positioncamera = True
cameraborderpercentage = 5.0
"""
        self.plugin_ini.parent.mkdir(parents=True, exist_ok=True)
        print("place ", self.plugin_ini)
        with open(self.plugin_ini, "w") as f:
            f.write(cfg)      


def render():
    scene = bpy.context.scene
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = str(settings.output_path.resolve())
    scene.render.resolution_x = settings.render_resolution
    scene.render.resolution_y = settings.render_resolution
    scene.render.resolution_percentage = 100

    bpy.ops.render.render(write_still=True)

settings = Settings()
settings.load_plugin()
settings.place_config()


# === Clear existing scene ===
bpy.ops.preferences.addon_enable(module=LDRAW_ADDON_NAME)

world = bpy.data.worlds.new("World")
bpy.context.scene.world = world
world.use_nodes = True

# === Import the LDraw brick ===
bpy.ops.import_scene.importldraw(filepath=str(settings.get_part_path("3001")))

# === Find ground plane and place objects ===
ground_plane = bpy.data.objects.get("LegoGroundPlane")
if ground_plane is None:
    raise ValueError("no groundplane")

# Get ground plane height
ground_height = ground_plane.location.z

# Move all mesh objects to sit on ground plane
brick = bpy.data.objects.get(f"00000_{BRICK}.dat")

# Update mesh to ensure bounds are correct
brick.select_set(True)
bpy.context.view_layer.objects.active = brick

# Make sure rotation is zeroed
brick.rotation_euler = (0, 0, 0)

# Make the mesh single-user if it isn't already
if brick.data.users > 1:
    brick.data = brick.data.copy()

# Apply transformations
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Get the object's bounds
lowest_point = brick.bound_box[0][2]  # z-coordinate of lowest point

# Calculate and apply offset
offset = ground_height - lowest_point
brick.location.z += offset

brick.select_set(False)

render()
