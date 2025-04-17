import blenderproc as bproc
bproc.init()
import numpy as np
import bpy
from pathlib import Path
import platform
from enum import Enum
import mathutils

print(f"Python Version: {platform.python_version()}")

LDRAW_ADDON_NAME = "io_scene_importldraw"
BRICK = "3001"

class SegmentationCategories(Enum):
    BACKGROUND = 0
    BRICK = 1

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
       
    def load_plugin(self) -> None:
        print(f"installing {self.plugin_installer.resolve()}")
        bpy.ops.preferences.addon_install(filepath=str(self.plugin_installer.resolve()))

    def place_config(self) -> None:
        cfg = """[importldraw]
ldrawdirectory = /home/luca/git/lego_blender/ldraw
useunofficialparts = False
uselogostuds = True
addenvironment = False
realscale = 10.0
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

    def enable_plugin(self) -> None:
        bpy.ops.preferences.addon_enable(module=LDRAW_ADDON_NAME)

    def import_part(self, id: str):
            bpy.ops.import_scene.importldraw(filepath=str(self.get_part_path(id)))
            brick_blender = bpy.data.objects.get(f"00000_{id}.dat")
    
            brick_blender.select_set(True)
            bpy.context.view_layer.objects.active = brick_blender
    
            # Make sure rotation is zeroed
            brick_blender.rotation_euler = (0, 0, 0)
    
            # Make the mesh single-user if it isn't already
            if brick_blender.data.users > 1:
                brick_blender.data = brick_blender.data.copy()
    
            # Convert to BlenderProc object
            brick = bproc.object.convert_to_meshes([brick_blender])[0]
            brick.set_cp("category_id", SegmentationCategories.BRICK.value)
            brick_blender.select_set(False)
            return brick, brick_blender

    def generate_ground(self, reference_object) -> None:
        # Get bounding box of the reference object
        bb = reference_object.bound_box
        size = np.max(bb, axis=0) - np.min(bb, axis=0)
        # Use the maximum horizontal dimension for scaling
        max_dim = max(size[0], size[1])
        # Calculate scale for the plane (default plane is 2x2)
        plane_scale = max_dim * 50 # 100x size / 2 units default size

        # Create a simple plane as ground under the object
        ground = bproc.object.create_primitive('PLANE', scale=[plane_scale, plane_scale, 1])
        # Center the ground plane
        ground.set_location([0, 0, 0])
        ground.set_cp("category_id", SegmentationCategories.BACKGROUND.value)
        # Set a simple diffuse material
        mat = bproc.material.create("ground_mat")
        mat.set_principled_shader_value("Base Color", [1.0, 0.75, 0.8, 1.0])
        ground.replace_materials(mat)
        return ground


settings = Settings()
settings.load_plugin()
settings.place_config()
settings.enable_plugin()

brick, brick_blender = settings.import_part(BRICK)

# move brick up
bb = np.array(brick_blender.bound_box)
min_z = np.min(bb[:, 2])
max_z = np.max(bb[:, 2])
height = max_z - min_z
target_z = 10 * height
brick.set_location([0, 0, target_z])



ground = settings.generate_ground(brick_blender)

if np.random.rand() < 0.8:
    random_rotation = np.random.uniform(0, 2 * np.pi, size=3)
    brick.set_rotation_euler(random_rotation)
    ground.enable_rigidbody(
        active=False,
        friction=0.1,
        angular_damping=0.01,
        linear_damping=0.01
    )
    brick.enable_rigidbody(
        active=True,
        friction=0.1,
        angular_damping=0.01,
        linear_damping=0.01,
        mass=0.5  # or another realistic value
    )
    bproc.object.simulate_physics_and_fix_final_poses(
        min_simulation_time=0.5,
        max_simulation_time=5,
        check_object_interval=1,
    )
else:
    brick.set_rotation_euler([0, 0, 0])

######################

light = bproc.types.Light()
light.set_type("POINT")
light.set_energy(np.random.uniform(5, 80))

# Find point of interest, all cam poses should look towards it
poi = bproc.object.compute_poi([brick])

IMAGE_COUNT = 1
# Add translational random walk on top of the POI
poi_drift = bproc.sampler.random_walk(total_length = IMAGE_COUNT, dims = 3, step_magnitude = 0.005, 
                                      window_size = 5, interval = [-0.03, 0.03], distribution = 'uniform')

# Rotational camera shaking as a random walk: Sample an axis angle representation
camera_shaking_rot_angle = bproc.sampler.random_walk(total_length = IMAGE_COUNT, dims = 1, step_magnitude = np.pi/32, window_size = 5,
                                                     interval = [-np.pi/6, np.pi/6], distribution = 'uniform', order = 2)
camera_shaking_rot_axis = bproc.sampler.random_walk(total_length = IMAGE_COUNT, dims = 3, window_size = 10, distribution = 'normal')
camera_shaking_rot_axis /= np.linalg.norm(camera_shaking_rot_axis, axis=1, keepdims=True)

for i in range(IMAGE_COUNT):
    bb = np.array(brick.get_bound_box())
    brick_center = np.mean(bb, axis=0)
    brick_radius = np.linalg.norm(bb - brick_center, axis=1).max()
    margin = 0.15 * brick_radius
    brick_radius += margin
    fov = np.deg2rad(39.6)
    target_fill = 0.65
    distance = (brick_radius / target_fill) / np.tan(fov / 2)

    # Camera trajectory: full circle, higher Z for bird's-eye
    angle = i / IMAGE_COUNT * 2 * np.pi
    cam_height = np.random.uniform(0.8, 1.6) * distance  # Randomize multiplier for bird's-eye
    location_cam = np.array([
        distance * np.cos(angle),
        distance * np.sin(angle),
        brick_center[2] + cam_height
    ])
    # Move the light to the camera position
    light.set_location(location_cam.tolist())

    # Look at the brick center (or poi + drift)
    look_at = brick_center.copy()
    look_at[:2] += poi_drift[i][:2]  # Optional: add drift in X/Y only
    look_at[2] = brick_center[2]     # Always look at the brick's center in Z

    rotation_matrix = bproc.camera.rotation_from_forward_vec(look_at - location_cam)
    R_rand = np.array(mathutils.Matrix.Rotation(camera_shaking_rot_angle[i], 3, camera_shaking_rot_axis[i]))
    rotation_matrix = R_rand @ rotation_matrix
    cam2world_matrix = bproc.math.build_transformation_mat(location_cam, rotation_matrix)
    bproc.camera.add_camera_pose(cam2world_matrix)


######################
# Render the scene
data = bproc.renderer.render()

# Write the rendering into an hdf5 file
bproc.renderer.enable_depth_output(activate_antialiasing=False)
bproc.renderer.enable_segmentation_output(map_by=["category_id", "instance", "name"])
bproc.camera.set_resolution(settings.render_resolution, settings.render_resolution)
bproc.writer.write_hdf5(f"output/", data, append_to_existing_output=True)
