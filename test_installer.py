"""Exercise boot-file replacement against temporary files, never a real Cube."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location("cube_fix", Path(__file__).with_name("cube-dv-fix.py"))
fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)


class FakeCube(fix.Cube):
    def __init__(self, base):
        super().__init__(base)
        self.calls = []
        self.kodi_active = True
        self.change_kernel_on_stop = False

    def root_required(self):
        pass

    def command(self, arguments, check=True):
        self.calls.append(arguments)
        result = 0
        if arguments[:2] == ["systemctl", "is-active"]:
            result = 0 if self.kodi_active else 3
        elif arguments[:2] == ["systemctl", "stop"]:
            self.kodi_active = False
            if self.change_kernel_on_stop:
                self.path("/flash/kernel.img").write_bytes(b"concurrent update")
        elif arguments[:2] == ["systemctl", "start"]:
            self.kodi_active = True
        return SimpleNamespace(returncode=result, stdout="", stderr="")


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cube = FakeCube(self.root)
        self.stock = b"original device kernel and initramfs" * 32
        self.patched = b"verified corrected kernel and same initramfs" * 32
        self.orig_sha = hashlib.sha256(self.stock).hexdigest()
        self.fixed_sha = hashlib.sha256(self.patched).hexdigest()
        original, patched = fix.ORIGINAL_SHA, fix.FIXED_SHA
        fix.ORIGINAL_SHA, fix.FIXED_SHA = self.orig_sha, self.fixed_sha
        self.addCleanup(lambda: setattr(fix, "ORIGINAL_SHA", original))
        self.addCleanup(lambda: setattr(fix, "FIXED_SHA", patched))
        files = {
            "/proc/device-tree/model": fix.MODEL + "\0",
            "/proc/device-tree/amlogic-dt-id": "t7_gazelle_pvt\0",
            "/proc/sys/kernel/osrelease": fix.KERNEL_RELEASE,
            "/proc/mounts": "/dev/data /flash ext4 rw,noatime 0 0\n",
            "/proc/modules": "dovi 1234 1 - Live 0x0\n",
            "/etc/os-release": 'ID="coreelec"\nVERSION="' + fix.RELEASE + '"\n',
        }
        for name, content in files.items():
            destination = self.cube.path(name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content)
        self.active = self.cube.path("/flash/kernel.img")
        self.active.parent.mkdir(exist_ok=True)
        self.active.write_bytes(self.stock)
        self.package = self.cube.path("/storage/Cube-DV-Fix")
        self.package.mkdir(parents=True)
        (self.package / "kernel.pq-guard.img").write_bytes(self.patched)
        self.backup = self.cube.path(fix.BACKUP_DIR)

    def test_check_does_not_change_files(self):
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        report = fix.inspect(self.cube, self.package)
        self.assertEqual(report["status"], "READY TO INSTALL")
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        self.assertEqual(self.cube.calls, [])

    def test_install_backup_idempotence_and_rollback(self):
        self.assertEqual(fix.install(self.cube, self.package), "installed")
        self.assertEqual(self.active.read_bytes(), self.patched)
        self.assertEqual((self.backup / "kernel.original.img").read_bytes(), self.stock)
        self.assertEqual(json.loads((self.backup / "manifest.json").read_text())["status"], "installed")
        calls = list(self.cube.calls)
        self.assertEqual(fix.install(self.cube, self.package), "already-installed")
        self.assertEqual(self.cube.calls, calls)
        self.assertEqual(fix.rollback(self.cube), "restored")
        self.assertEqual(self.active.read_bytes(), self.stock)
        self.assertEqual(fix.rollback(self.cube), "already-restored")
        self.assertEqual((self.backup / "kernel.original.img").read_bytes(), self.stock)

    def test_wrong_build_refused_without_backup_or_service_changes(self):
        self.cube.path("/etc/os-release").write_text('ID="coreelec"\nVERSION="another-build"\n')
        with self.assertRaises(fix.FixError):
            fix.install(self.cube, self.package)
        self.assertEqual(self.active.read_bytes(), self.stock)
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.cube.calls)

    def test_wrong_hardware_refused(self):
        self.cube.path("/proc/device-tree/model").write_text("Other player")
        with self.assertRaises(fix.FixError):
            fix.install(self.cube, self.package)
        self.assertFalse(self.backup.exists())
        self.assertEqual(self.active.read_bytes(), self.stock)

    def test_unknown_original_kernel_refused(self):
        self.active.write_bytes(b"another kernel")
        with self.assertRaises(fix.FixError):
            fix.install(self.cube, self.package)
        self.assertEqual(self.active.read_bytes(), b"another kernel")
        self.assertFalse(self.backup.exists())

    def test_damaged_payload_refused(self):
        (self.package / "kernel.pq-guard.img").write_bytes(b"bad transfer")
        with self.assertRaises(fix.FixError):
            fix.install(self.cube, self.package)
        self.assertEqual(self.active.read_bytes(), self.stock)
        self.assertFalse(self.backup.exists())

    def test_read_only_flash_restored_after_install_and_rollback(self):
        self.cube.path("/proc/mounts").write_text("/dev/boot /flash vfat ro,noatime 0 0\n")
        fix.install(self.cube, self.package)
        fix.rollback(self.cube)
        mounts = [c for c in self.cube.calls if c[0] == "mount"]
        self.assertEqual(mounts, [["mount", "-o", "remount,rw", "/flash"],
                                  ["mount", "-o", "remount,ro", "/flash"]] * 2)

    def test_bad_staging_does_not_replace_active_kernel_and_restarts_kodi(self):
        real_copy = fix.durable_copy
        def corrupt_staging(source, destination):
            if Path(destination).name.endswith(".pending"):
                Path(destination).write_bytes(b"bad disk copy")
            else:
                real_copy(source, destination)
        with mock.patch.object(fix, "durable_copy", side_effect=corrupt_staging):
            with self.assertRaises(fix.FixError):
                fix.install(self.cube, self.package)
        self.assertEqual(self.active.read_bytes(), self.stock)
        self.assertTrue(self.cube.kodi_active)
        self.assertEqual((self.backup / "kernel.original.img").read_bytes(), self.stock)

    def test_existing_pending_file_preserved(self):
        pending = self.cube.path("/flash/kernel.cube-dv-fix.pending")
        pending.write_bytes(b"inspect me")
        with self.assertRaises(fix.FixError):
            fix.install(self.cube, self.package)
        self.assertEqual(pending.read_bytes(), b"inspect me")
        self.assertEqual(self.active.read_bytes(), self.stock)
        self.assertFalse(self.cube.calls)

    def test_corrupt_backup_prevents_rollback(self):
        fix.install(self.cube, self.package)
        (self.backup / "kernel.original.img").write_bytes(b"bad backup")
        with self.assertRaises(fix.FixError):
            fix.rollback(self.cube)
        self.assertEqual(self.active.read_bytes(), self.patched)

    def test_an_unrelated_new_kernel_is_not_rolled_back(self):
        fix.install(self.cube, self.package)
        self.active.write_bytes(b"later user update")
        with self.assertRaises(fix.FixError):
            fix.rollback(self.cube)
        self.assertEqual(self.active.read_bytes(), b"later user update")

    def test_changed_rootfs_release_is_not_rolled_back(self):
        fix.install(self.cube, self.package)
        self.cube.path("/etc/os-release").write_text('ID="coreelec"\nVERSION="later-update"\n')
        with self.assertRaises(fix.FixError):
            fix.rollback(self.cube)
        self.assertEqual(self.active.read_bytes(), self.patched)

    def test_concurrent_kernel_update_is_preserved(self):
        self.cube.change_kernel_on_stop = True
        with self.assertRaises(fix.FixError):
            fix.install(self.cube, self.package)
        self.assertEqual(self.active.read_bytes(), b"concurrent update")
        self.assertTrue(self.cube.kodi_active)

    def test_symbolic_boot_image_is_refused(self):
        target = self.cube.path("/flash/some-other-file")
        self.active.rename(target)
        self.active.symlink_to(target)
        with self.assertRaises(fix.FixError):
            fix.install(self.cube, self.package)
        self.assertTrue(self.active.is_symlink())
        self.assertEqual(target.read_bytes(), self.stock)


if __name__ == "__main__":
    unittest.main(verbosity=2)
