from blenderproc.utility.SetupUtility import SetupUtility
SetupUtility.setup([])

from blenderproc.utility.MathUtility import MathUtility
from blenderproc.utility.CameraUtility import CameraUtility
from blenderproc.utility.filter.Filter import Filter
from blenderproc.utility.WriterUtility import WriterUtility
from blenderproc.utility.Initializer import Initializer
from blenderproc.utility.loader.ObjectLoader import ObjectLoader
from blenderproc.utility.LightUtility import Light

from blenderproc.utility.RendererUtility import RendererUtility

import numpy as np
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('scene', nargs='?', default="examples/resources/scene.obj", help="Path to the scene.obj file")
parser.add_argument('output_dir', nargs='?', default="examples/basics/entity_manipulation/output", help="Path to where the final files, will be saved")
args = parser.parse_args()

Initializer.init()

# load the objects into the scene
objs = ObjectLoader.load(args.scene)

# define a light and set its location and energy level
light = Light()
light.set_type("POINT")
light.set_location([5, -5, 5])
light.set_energy(1000)

# define the camera intrinsics
CameraUtility.set_intrinsics_from_blender_params(1, 512, 512, lens_unit="FOV")

# Add two camera poses via location + euler angles
CameraUtility.add_camera_pose(MathUtility.build_transformation_mat([0, -13.741, 4.1242], [1.3, 0, 0]))
CameraUtility.add_camera_pose(MathUtility.build_transformation_mat([1.9488, -6.5202, 0.23291], [1.84, 0, 0.5]))

# Find object with name Suzanne
suzanne = Filter.one_by_attr(objs, "name", "Suzanne")
# Set its location and rotation
suzanne.set_location(np.random.uniform([0, 1, 2], [1, 2, 3]))
suzanne.set_rotation_euler([1, 1, 0])

# activate normal and distance rendering
RendererUtility.enable_normals_output()
RendererUtility.enable_distance_output()
# set the amount of samples, which should be used for the color rendering
RendererUtility.set_samples(350)

# render the whole pipeline
data = RendererUtility.render()

# write the data to a .hdf5 container
WriterUtility.save_to_hdf5(args.output_dir, data)
