import csv
import json
import shutil
import os
import bpy

from src.utility.CocoUtility import CocoUtility
from src.main.Module import Module


class CocoAnnotationsWriter(Module):
    """ Writes Coco Annotations in to a file.

    **Configuration**:

    .. csv-table::
       :header: "Parameter", "Description"
       "delete_temporary_files_afterwards", "True, if all temporary files should be deleted after merging."
       "rgb_output_key", "The output key with which the rgb images were registered. Should be the same as the output_key of the RgbRenderer module."
       "segmap_output_key", "The output key with which the segmentation images were registered. Should be the same as the output_key of the SegMapRenderer module."
       "segcolormap_output_key", "The output key with which the csv file for object name/class correspondences was registered. Should be the same as the colormap_output_key of the SegMapRenderer module."
    """

    def __init__(self, config):
        Module.__init__(self, config)

        self.rgb_output_key = self.config.get_string("rgb_output_key", "colors")
        self.segmap_output_key = self.config.get_string("segmap_output_key", "segmap")
        self.segcolormap_output_key = self.config.get_string("segcolormap_output_key", "segcolormap")
        self._coco_data_dir = os.path.join(self._determine_output_dir(False), 'coco_data')
        if not os.path.exists(self._coco_data_dir):
            os.makedirs(self._coco_data_dir)

    def run(self):

        # Find path pattern of segmentation images
        segmentation_map_output = self._find_registered_output_by_key(self.segmap_output_key)
        if segmentation_map_output is None:
            raise Exception("There is no output registered with key " + self.segmap_output_key + ". Are you sure you ran the SegMapRenderer module before?")
        
        # Find path pattern of rgb images
        rgb_output = self._find_registered_output_by_key(self.rgb_output_key)
        if rgb_output is None:
            raise Exception("There is no output registered with key " + self.rgb_output_key + ". Are you sure you ran the RgbRenderer module before?")
    
        # collect all segmaps
        segmentation_map_paths = []
        # collect all RGB paths
        image_paths = []
        # for each rendered frame
        for frame in range(bpy.context.scene.frame_start, bpy.context.scene.frame_end):
            segmentation_map_paths.append(segmentation_map_output["path"] % frame)
            image_paths.append(rgb_output["path"] % frame)

        # Find path of name class mapping csv file
        segcolormap_output = self._find_registered_output_by_key(self.segcolormap_output_key)
        if segcolormap_output is None:
            raise Exception("There is no output registered with key " + self.segcolormap_output_key + ". Are you sure you ran the SegMapRenderer module with 'map_by' set to 'instance' before?")

        # read colormappings, which include object name/class to integer mapping
        color_map = []
        with open(segcolormap_output["path"], 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for mapping in reader:
                color_map.append(mapping)
        
        new_coco_image_paths = []
        # copy images from temporary dir to output_dir/coco_data
        for image_path in image_paths:
            target_path = os.path.join(self._coco_data_dir, os.path.basename(image_path))
            shutil.copyfile(image_path, target_path)   
            new_coco_image_paths.append(os.path.basename(image_path))

        coco_output = CocoUtility.generate_coco_annotations(segmentation_map_paths, new_coco_image_paths, color_map, "coco_annotations")
        fname = os.path.join(self._coco_data_dir, "coco_annotations.json")
        print("Writing coco annotations to " + fname)
        with open(fname, 'w') as fp:
            json.dump(coco_output, fp)

        # Remove temp data
        if self.config.get_bool("delete_temporary_files_afterwards", True):
            shutil.rmtree(self._temp_dir)
