"""The SIP probe the VM job uses: its command line must survive a random handset secret that starts with "-"."""
import importlib.util
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sip_probe", HERE.parent / "ci" / "sip_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
BASE = ["--host", "h", "--cafile", "c"]


class Args(unittest.TestCase):
    def test_a_secret_that_starts_with_a_dash_is_taken_in_the_equals_form(self):
        """Handset secrets are `secrets.token_urlsafe` strings, whose alphabet includes "-". Passed as a separate word, one that began
        with it was read as an option and five VM tests failed with "expected one argument" (found on the CI runner, not locally)."""
        args = probe.parser().parse_args(BASE + ["--user=h1", "--secret=-abc_DEF-"])
        self.assertEqual(args.secret, "-abc_DEF-")

    def test_the_separate_word_form_is_the_trap_this_guards_against(self):
        with self.assertRaises(SystemExit):
            probe.parser().parse_args(BASE + ["--user", "h1", "--secret", "-abc_DEF-"])

    def test_the_vm_test_builds_the_command_in_the_equals_form(self):
        text = (HERE.parent / "ci" / "vm_test.py").read_text()
        self.assertIn("f\"--secret={account['secret']}\"", text)
        self.assertNotRegex(text, r'"--secret",\s*account')


if __name__ == "__main__":
    unittest.main()
