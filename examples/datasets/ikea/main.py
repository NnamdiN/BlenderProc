from blenderproc.utility.SetupUtility import SetupUtility
SetupUtility.setup([])

from blenderproc.utility.loader.IKEALoader import IKEALoader
from blenderproc.utility.sampler.PartSphere import PartSphere
from blenderproc.utility.MathUtility import MathUtility
from blenderproc.utility.CameraUtility import CameraUtility
from blenderproc.utility.MeshObjectUtility import MeshObject
from blenderproc.utility.WriterUtility import WriterUtility
from blenderproc.utility.Initializer import Initializer
from blenderproc.utility.LightUtility import Light
from blenderproc.utility.RendererUtility import RendererUtility

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('ikea_path', help="Path to the downloaded IKEA dataset, see the [scripts folder](../../scripts) for the download script")
parser.add_argument('output_dir', nargs='?', default="examples/datasets/ikea/output", help="Path to the output directory")
args = parser.parse_args()

Initializer.init()

# Load IKEA objects from type table into the scene
objs = IKEALoader.load(args.ikea_path, obj_categories="table")

# define a light and set its location and energy level
light = Light()
light.set_type("POINT")
light.set_location([5, -5, 5])
light.set_energy(1000)

# Find point of interest, all cam poses should look towards it
poi = MeshObject.compute_poi(objs)
# Sample five camera poses
for i in range(5):
    # Sample random camera location around the object
    location = PartSphere.sample([0, 0, 0], radius=2.5, part_sphere_dir_vector=[1, 0, 0], mode="SURFACE")
    # Compute rotation based on vector going from location towards poi
    rotation_matrix = CameraUtility.rotation_from_forward_vec(poi - location)
    # Add homog cam pose based on location an rotation
    cam2world_matrix = MathUtility.build_transformation_mat(location, rotation_matrix)
    CameraUtility.add_camera_pose(cam2world_matrix)

# activate normal and distance rendering
RendererUtility.enable_normals_output()
RendererUtility.enable_distance_output()
# set the amount of samples, which should be used for the color rendering
RendererUtility.set_samples(350)

# render the whole pipeline
data = RendererUtility.render()

# write the data to a .hdf5 container
WriterUtility.save_to_hdf5(args.output_dir, data)
