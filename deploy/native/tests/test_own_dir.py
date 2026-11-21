"""deploy/native/own-dir.py: install.sh's way to own folders that Asterisk (not root) can write in, without following a link (R10-5)."""
import grp
import importlib.util
import os
import pathlib
import pwd
import shutil
import stat
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("own_dir", HERE.parent / "own-dir.py")
own = importlib.util.module_from_spec(spec)
spec.loader.exec_module(own)
ME = pwd.getpwuid(os.getuid()).pw_name
MY_GROUP = grp.getgrgid(os.getgid()).gr_name


class OwnDir(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        self.victim = self.d / "victim"                       # what a root-run script must never touch
        self.victim.mkdir(mode=0o755)
        (self.victim / "secret").write_text("x")
        (self.d / "state").mkdir()

    def run_main(self, mode, *paths):
        return own.main([mode, ME, MY_GROUP, *map(str, paths)])

    def test_it_makes_the_folder_with_the_mode(self):
        self.assertEqual(self.run_main("0750", self.d / "state" / "cache"), 0)
        self.assertEqual(stat.S_IMODE(os.stat(self.d / "state" / "cache").st_mode), 0o750)

    def test_an_existing_folder_gets_the_mode_and_keeps_its_files(self):
        (self.d / "state" / "cache").mkdir(mode=0o777)
        (self.d / "state" / "cache" / "f").write_text("keep")
        self.run_main("0750", self.d / "state" / "cache")
        self.assertEqual(stat.S_IMODE(os.stat(self.d / "state" / "cache").st_mode), 0o750)
        self.assertEqual((self.d / "state" / "cache" / "f").read_text(), "keep")

    def test_a_link_in_place_of_the_folder_is_replaced_and_its_target_is_left_alone(self):
        os.symlink(self.victim, self.d / "state" / "cache")
        self.run_main("0700", self.d / "state" / "cache")
        self.assertFalse(os.path.islink(self.d / "state" / "cache"))
        self.assertTrue((self.d / "state" / "cache").is_dir())
        self.assertEqual(stat.S_IMODE(os.stat(self.victim).st_mode), 0o755, "the target was not re-moded")
        self.assertEqual((self.victim / "secret").read_text(), "x")

    def test_a_file_in_place_of_the_folder_is_replaced(self):
        (self.d / "state" / "cache").write_text("not a folder")
        self.run_main("0750", self.d / "state" / "cache")
        self.assertTrue((self.d / "state" / "cache").is_dir())

    def test_a_link_as_the_parent_is_refused_not_followed(self):
        os.symlink(self.victim, self.d / "linked")
        with self.assertRaises(OSError):
            self.run_main("0750", self.d / "linked" / "cache")
        self.assertEqual(os.listdir(self.victim), ["secret"])

    def test_bad_arguments(self):
        self.assertEqual(own.main(["0750", ME]), 2)
        with self.assertRaises(ValueError):
            own.own_dir("/", 0o750, os.getuid(), os.getgid())


class InstallUsesIt(unittest.TestCase):
    def test_install_sh_no_longer_hands_asterisks_folders_to_install_d(self):
        text = (HERE.parent / "install.sh").read_text()
        body = text[text.index("own_asterisk_state() {"):text.index("own_asterisk_state\n")]
        self.assertIn("own-dir.py", body)
        self.assertNotRegex(body, r"install -d [^\n]*-o asterisk", "a folder Asterisk owns must not be re-owned through a path it can redirect")


if __name__ == "__main__":
    unittest.main()
