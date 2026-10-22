import tempfile
import unittest
import zipfile
from pathlib import Path

from filemanager.errors import FMError
from filemanager.operations import FileManager
from filemanager.users import UserStore


class FileManagerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "root"
        self.fm = FileManager(self.root, quota_bytes=1024)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dirs_and_navigation(self):
        self.fm.make_dir("docs")
        self.assertEqual(self.fm.enter("docs"), "/docs")
        self.fm.make_dir("inner")
        self.assertEqual(self.fm.leave(), "/")
        self.fm.remove_dir("docs")
        self.assertFalse((self.root / "docs").exists())

    def test_cannot_leave_workspace(self):
        for bad in ("..", "../..", "/../etc", "docs/../../x"):
            with self.assertRaises(FMError):
                self.fm.make_dir(bad)
        with self.assertRaises(FMError):
            self.fm.leave()
        with self.assertRaises(FMError):
            self.fm.enter("..")

    def test_files(self):
        self.fm.make_dir("a")
        self.fm.make_dir("b")
        self.fm.make_file("note.txt")
        self.fm.write_file("note.txt", "привет\n")
        self.fm.write_file("note.txt", "мир\n", append=True)
        self.assertEqual(self.fm.read_file("note.txt"), "привет\nмир\n")
        self.fm.copy_file("note.txt", "a")
        self.fm.move_file("note.txt", "b")
        self.fm.rename_file("b/note.txt", "renamed.txt")
        self.assertTrue((self.root / "a" / "note.txt").is_file())
        self.assertTrue((self.root / "b" / "renamed.txt").is_file())
        self.fm.remove_file("a/note.txt")
        self.assertFalse((self.root / "a" / "note.txt").exists())

    def test_rename_rejects_path(self):
        self.fm.make_file("x.txt")
        with self.assertRaises(FMError):
            self.fm.rename_file("x.txt", "../y.txt")

    def test_quota(self):
        self.fm.make_file("big.txt")
        with self.assertRaises(FMError):
            self.fm.write_file("big.txt", "x" * 2000)

    def test_pack_unpack(self):
        self.fm.make_dir("src")
        self.fm.make_file("src/a.txt")
        self.fm.write_file("src/a.txt", "data")
        self.fm.pack("src", "src.zip")
        self.fm.make_dir("out")
        self.fm.unpack("src.zip", "out")
        self.assertEqual((self.root / "out" / "src" / "a.txt").read_text(), "data")

    def test_unpack_blocks_zip_slip(self):
        evil = self.root / "evil.zip"
        with zipfile.ZipFile(evil, "w") as zf:
            zf.writestr("../../escape.txt", "x")
        with self.assertRaises(FMError):
            self.fm.unpack("evil.zip")


class UsersTest(unittest.TestCase):
    def test_register_and_login(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = UserStore(Path(tmp) / "users.json", tmp)
            home = store.register("sasha", "secret")
            self.assertTrue(home.is_dir())
            self.assertEqual(store.login("sasha", "secret"), home)
            with self.assertRaises(FMError):
                store.login("sasha", "wrong")
            with self.assertRaises(FMError):
                store.register("sasha", "other")
            self.assertNotIn("secret", (Path(tmp) / "users.json").read_text())


if __name__ == "__main__":
    unittest.main()
