from blenderproc.utility.SetupUtility import SetupUtility
SetupUtility.setup([])

from blenderproc.utility.loader.ShapeNetLoader import ShapeNetLoader
from blenderproc.utility.object.PhysicsSimulation import PhysicsSimulation
from blenderproc.utility.sampler.PartSphere import PartSphere
from blenderproc.utility.LabelIdMapping import LabelIdMapping
from blenderproc.utility.Utility import Utility
from blenderproc.utility.camera.CameraValidation import CameraValidation
from blenderproc.utility.filter.Filter import Filter
from blenderproc.utility.lighting.SurfaceLighting import SurfaceLighting
from blenderproc.utility.object.FloorExtractor import FloorExtractor
from blenderproc.utility.sampler.UpperRegionSampler import UpperRegionSampler
from blenderproc.utility.MathUtility import MathUtility
from blenderproc.utility.CameraUtility import CameraUtility
from blenderproc.utility.MeshObjectUtility import MeshObject
from blenderproc.utility.WriterUtility import WriterUtility
from blenderproc.utility.Initializer import Initializer
from blenderproc.utility.loader.SceneNetLoader import SceneNetLoader
from blenderproc.utility.RendererUtility import RendererUtility

import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('scene_net_obj_path', help="Path to the used scene net `.obj` file, download via scripts/download_scenenet.py")
parser.add_argument('scene_texture_path', help="Path to the downloaded texture files, you can find them at http://tinyurl.com/zpc9ppb")
parser.add_argument('shapenet_path', help="Path to the downloaded shape net core v2 dataset, get it from http://www.shapenet.org/")
parser.add_argument('output_dir', nargs='?', default="examples/datasets/shapenet_with_scenenet/output", help="Path to where the final files, will be saved")
args = parser.parse_args()

Initializer.init()

# Load the scenenet room and label its objects with category ids based on the nyu mapping
label_mapping = LabelIdMapping.from_csv(Utility.resolve_path(os.path.join('resources', 'id_mappings', 'nyu_idset.csv')))
room_objs = SceneNetLoader.load(args.scene_net_obj_path, args.scene_texture_path, label_mapping)

# In some scenes floors, walls and ceilings are one object that needs to be split first
# Collect all walls
walls = Filter.by_cp(room_objs, "category_id", label_mapping.id_from_label("wall"))
# Extract floors from the objects
new_floors = FloorExtractor.extract(walls, new_name_for_object="floor", should_skip_if_object_is_already_there=True)
# Set category id of all new floors
for floor in new_floors:
    floor.set_cp("category_id", label_mapping.id_from_label("floor"))
# Add new floors to our total set of objects
room_objs += new_floors

# Extract ceilings from the objects
new_ceilings = FloorExtractor.extract(walls, new_name_for_object="ceiling", up_vector_upwards=False, should_skip_if_object_is_already_there=True)
# Set category id of all new ceiling
for ceiling in new_ceilings:
    ceiling.set_cp("category_id", label_mapping.id_from_label("ceiling"))
# Add new ceilings to our total set of objects
room_objs += new_ceilings

# Make all lamp objects emit light
lamps = Filter.by_attr(room_objs, "name", ".*[l|L]amp.*", regex=True)
SurfaceLighting.run(lamps, emission_strength=15, keep_using_base_color=True)
# Also let all ceiling objects emit a bit of light, so the whole room gets more bright
ceilings = Filter.by_attr(room_objs, "name", ".*[c|C]eiling.*", regex=True)
SurfaceLighting.run(ceilings, emission_strength=2)

# load the ShapeNet object into the scene
shapenet_obj = ShapeNetLoader.load(args.shapenet_path, used_synset_id="02801938")

# Collect all beds
beds = Filter.by_cp(room_objs, "category_id", label_mapping.id_from_label("bed"))
# Sample the location of the ShapeNet object above a random bed
shapenet_obj.set_location(UpperRegionSampler.sample(beds, min_height=0.3))

# Make sure the ShapeNet object has a minimum thickness (this will increase the stability of the simulator)
shapenet_obj.add_modifier("SOLIDIFY", thickness=0.0025)
# Make the ShapeNet object actively participating in the simulation and increase its mass to stabilize the simulation
shapenet_obj.enable_rigidbody(True, mass_factor=2000, collision_margin=0.00001, collision_shape="MESH")
# Make all other objects passively participating in the simulation as obstacles and increase its mass to stabilize the simulation
for obj in room_objs:
    obj.enable_rigidbody(False, mass_factor=2000, collision_margin=0.00001, collision_shape="MESH")

# Run the simulation to let the ShapeNet object fall onto the bed
PhysicsSimulation.simulate_and_fix_final_poses(
    solver_iters=30,
    substeps_per_frame=40,
    min_simulation_time=0.5,
    max_simulation_time=4,
    check_object_interval=0.25
)

# Init bvh tree containing all mesh objects
bvh_tree = MeshObject.create_bvh_tree_multi_objects(room_objs)
poses = 0
tries = 0
while tries < 10000 and poses < 5:
    # Sample on sphere around ShapeNet object
    location = PartSphere.sample(shapenet_obj.get_location(), radius=2, dist_above_center=0.5, mode="SURFACE")
    # Compute rotation based on vector going from location towards ShapeNet object
    rotation_matrix = CameraUtility.rotation_from_forward_vec(shapenet_obj.get_location() - location)
    cam2world_matrix = MathUtility.build_transformation_mat(location, rotation_matrix)

    # Check that obstacles are at least 0.5 meter away from the camera and that the ShapeNet object is visible
    if shapenet_obj in CameraValidation.visible_objects(cam2world_matrix) and CameraValidation.perform_obstacle_in_view_check(cam2world_matrix, {"min": 0.5}, bvh_tree):
        CameraUtility.add_camera_pose(cam2world_matrix)
        poses += 1
    tries += 1

# activate normal and distance rendering
RendererUtility.enable_normals_output()
RendererUtility.enable_distance_output()
# set the amount of samples, which should be used for the color rendering
RendererUtility.set_samples(150)

# render the whole pipeline
data = RendererUtility.render()

# write the data to a .hdf5 container
WriterUtility.save_to_hdf5(args.output_dir, data)
