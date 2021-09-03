
import unittest
import os.path

from blenderproc.utility.loader.ObjectLoader import ObjectLoader
from blenderproc.utility.Utility import Utility
from blenderproc.utility.Initializer import Initializer
from blenderproc.utility.tests.SilentMode import SilentMode
from blenderproc.utility.tests.TestsPathManager import test_path_manager

class UnitTestCheckUtility(unittest.TestCase):

    def test_blender_reference_after_undo(self):
        """ Test if the blender_data objects are still valid after an undo execution is done. 
        """
        with SilentMode():
            Initializer.init()
            objs = ObjectLoader.load(os.path.join(test_path_manager.example_resources, "scene.obj"))

            for obj in objs:
                obj.set_cp("test", 0)

            with Utility.UndoAfterExecution():
                for obj in objs:
                    obj.set_cp("test", 1)

        for obj in objs:
            self.assertEqual(obj.get_cp("test"), 0)
