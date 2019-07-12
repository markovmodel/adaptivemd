

import unittest

import os
import sys
sys.dont_compile_bytecode = True

import shlex
import shutil
import tempfile
import subprocess

from time import sleep

class TestMongodLauncher(unittest.TestCase):

    _correct_filestructure = ["db.log", "db.cfg", "db/", "socket/"]

    @classmethod
    def setUpClass(cls):

        # Quit if this isn't in ENV
        #assert os.getenv("ADMD_PROFILE", False)

        check_if_mongod = subprocess.check_output(
            shlex.split("which mongod"),
        ).decode("utf-8")

        print("Path found for mongod: %s" % check_if_mongod)

        if not check_if_mongod:
            unittest.SkipTest("Skipping test, can't find `mongod` command in PATH")

        # launch the database using AdaptiveMDs runtime utilities

        cls.shared_path = tempfile.mkdtemp(prefix="mongo")

        cls.mpid = subprocess.check_output(
            shlex.split("launch_amongod %s" % cls.shared_path)
        ).decode("utf-8")

        count = 0
        while not os.listdir(os.path.join(cls.shared_path, "socket")):
            sleep(1)
            count += 1
            if count > 10:
                unittest.SkipTest("Skipping test, mongod did not start in a timely manner")

    def test(self):
        print("Running check of file structure")
        for f in TestMongodLauncher._correct_filestructure:
            fpath = os.path.join(self.shared_path, f)
            print("Checking that this file exists: %s" % fpath)
            self.assertTrue(os.path.exists(fpath))

    @classmethod
    def tearDownClass(cls):
        print("Test complete, tearing down")
        subprocess.call(shlex.split("kill %s" % cls.mpid))
        shutil.rmtree(cls.shared_path)


if __name__ == "__main__":
    unittest.main()
    sys.exit()
