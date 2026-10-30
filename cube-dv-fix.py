#!/usr/bin/env python3
"""Checked installer for the tested third-generation Cube kernel correction.

Uses Python's standard library. No credentials, network calls or forced options.
"""
import argparse
from contextlib import contextmanager
import datetime
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PACKAGE_VERSION = "1.1"
MODEL = "Amazon Fire TV 3rd gen Cube"
RELEASE = "22.0-Piers-samurihl_20260928164552"
KERNEL_RELEASE = "5.15.196"
ORIGINAL_SHA = "cde2bace4057ce743d26735a81c8323b21fcce638b1649e4bda309568b683d16"
FIXED_SHA = "071498095ae2362caaea3ff052b3262fadd904fd37bd607128fc307b517e4b10"
BACKUP_DIR = "/storage/cube-dv-fix-backup"


class FixError(Exception):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path):
    try:
        return Path(path).read_text().replace("\0", "").strip()
    except (OSError, UnicodeError):
        return ""


def durable_copy(source, destination):
    with Path(source).open("rb") as source_file:
        with Path(destination).open("xb") as destination_file:
            shutil.copyfileobj(source_file, destination_file, 1024 * 1024)
            destination_file.flush()
            os.fsync(destination_file.fileno())


def sync_directory(directory):
    descriptor = os.open(str(directory), os.O_RDONLY | os.O_DIRECTORY)
    try:
        try:
            os.fsync(descriptor)
        except OSError as error:
            if error.errno not in (errno.EINVAL, errno.ENOTSUP):
                raise
    finally:
        os.close(descriptor)


def write_json(path, data):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(str(temporary), str(path))
    sync_directory(path.parent)


class Cube:
    def __init__(self, base=Path("/")):
        self.base = Path(base)

    def path(self, absolute):
        return self.base / absolute.lstrip("/")

    def command(self, arguments, check=True):
        return subprocess.run(arguments, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True,
                              timeout=45, check=check)

    def root_required(self):
        if not hasattr(os, "geteuid") or os.geteuid() != 0:
            raise FixError("Install and rollback must be run as root on the Cube.")

    def kernel_release(self):
        return read_text(self.path("/proc/sys/kernel/osrelease"))

    def flash_options(self):
        for line in read_text(self.path("/proc/mounts")).splitlines():
            fields = line.split()
            if len(fields) >= 4 and fields[1] == "/flash":
                return fields[3].split(",")
        raise FixError("Cannot identify the /flash mount; no boot files changed.")

    @contextmanager
    def writable_flash(self):
        originally_read_only = "ro" in self.flash_options()
        if originally_read_only:
            self.command(["mount", "-o", "remount,rw", "/flash"])
        try:
            yield
        finally:
            os.sync()
            if originally_read_only:
                self.command(["mount", "-o", "remount,ro", "/flash"])


def os_release(cube):
    values = {}
    wanted = {"NAME", "ID", "VERSION", "VERSION_ID", "PRETTY_NAME",
              "BUILD_ID", "DISTRO_ARCH", "DISTRO_BUILD", "DISTRO_DEVICE"}
    for line in read_text(cube.path("/etc/os-release")).splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key in wanted:
                values[key] = value.strip().strip('"')
    return values


def inspect(cube, package):
    model = read_text(cube.path("/proc/device-tree/model"))
    release = os_release(cube)
    active = cube.path("/flash/kernel.img")
    active_sha = sha256(active) if active.is_file() else None
    payload = Path(package) / "kernel.pq-guard.img"
    payload_sha = sha256(payload) if payload.is_file() else None
    reasons = []
    if model != MODEL:
        reasons.append("Hardware is not the tested third-generation Fire TV Cube.")
    if release.get("ID") != "coreelec" or release.get("VERSION") != RELEASE:
        reasons.append("CoreELEC build differs from the tested release.")
    if cube.kernel_release() != KERNEL_RELEASE:
        reasons.append("Running kernel version differs from the tested kernel.")
    if active.is_symlink():
        reasons.append("Boot image is a symbolic link; this layout needs review.")
    if active_sha not in (ORIGINAL_SHA, FIXED_SHA):
        reasons.append("Boot image does not match the tested original or fixed image.")
    compatible = not reasons
    if not compatible:
        status = "DIFFERENT BUILD OR HARDWARE — NO INSTALL"
    elif active_sha == FIXED_SHA:
        status = "ALREADY INSTALLED"
    elif payload_sha != FIXED_SHA:
        status = "RE-COPY PACKAGE — kernel file missing or damaged"
    else:
        status = "READY TO INSTALL"
    config = cube.path("/proc/config.gz")
    modules = []
    for line in read_text(cube.path("/proc/modules")).splitlines():
        fields = line.split()
        if fields and fields[0].startswith("dovi"):
            modules.append(fields[0])
    return {
        "package_version": PACKAGE_VERSION,
        "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model": model, "amlogic_dt_id": read_text(cube.path("/proc/device-tree/amlogic-dt-id")),
        "os_release": release, "running_kernel": cube.kernel_release(),
        "kernel_image_sha256": active_sha, "kernel_image_bytes": active.stat().st_size if active.is_file() else None,
        "package_kernel_sha256": payload_sha,
        "kernel_config_available": config.is_file(),
        "kernel_config_sha256": sha256(config) if config.is_file() else None,
        "dolby_module_names": modules,
        "runtime_fix_switch": read_text(cube.path("/sys/module/aml_media/parameters/pq_vadj1_sync")) or None,
        "runtime_corrections": read_text(cube.path("/sys/module/aml_media/parameters/pq_vadj1_resyncs")) or None,
        "compatible": compatible, "status": status, "reasons": reasons,
        "expected_release": RELEASE, "expected_original_kernel_sha256": ORIGINAL_SHA,
    }


def show_report(report, saved=None):
    print("Cube Dolby Vision fix — compatibility check")
    print("Model:    " + (report["model"] or "unknown"))
    print("CoreELEC: " + report["os_release"].get("VERSION", "unknown"))
    print("Kernel:   " + (report["running_kernel"] or "unknown"))
    print("Result:   " + report["status"])
    for reason in report["reasons"]:
        print("  " + reason)
    if saved:
        print("Report:   " + str(saved))
    if not report["compatible"]:
        print("Send check-report.json for a matching package. Nothing was installed.")


def read_backup(cube):
    directory = cube.path(BACKUP_DIR)
    if directory.is_symlink():
        raise FixError("Backup directory is a symbolic link; preserve it for review.")
    original = directory / "kernel.original.img"
    manifest = directory / "manifest.json"
    if not original.is_file() or original.is_symlink() or not manifest.is_file():
        raise FixError("A complete installer backup was not found. No boot files changed.")
    metadata = json.loads(manifest.read_text())
    if metadata.get("original_sha256") != ORIGINAL_SHA or metadata.get("fixed_sha256") != FIXED_SHA:
        raise FixError("Backup belongs to another package. No boot files changed.")
    if sha256(original) != ORIGINAL_SHA:
        raise FixError("Backup checksum differs. No boot files changed.")
    return directory, original, manifest, metadata


def make_backup(cube, report):
    directory = cube.path(BACKUP_DIR)
    if directory.exists():
        return read_backup(cube)
    directory.mkdir(mode=0o700)
    original = directory / "kernel.original.img"
    durable_copy(cube.path("/flash/kernel.img"), original)
    if sha256(original) != ORIGINAL_SHA:
        raise FixError("Backup verification failed. No boot files changed.")
    manifest = directory / "manifest.json"
    metadata = {"package_version": PACKAGE_VERSION, "original_sha256": ORIGINAL_SHA,
                "fixed_sha256": FIXED_SHA, "status": "backed-up", "original_report": report}
    write_json(manifest, metadata)
    sync_directory(directory.parent)
    return directory, original, manifest, metadata


def replace_kernel(cube, source, expected_sha, pending_name):
    pending = cube.path("/flash/" + pending_name)
    if pending.exists():
        raise FixError("A previous staging file exists: " + str(pending) + ". Preserve it for review.")
    with cube.writable_flash():
        durable_copy(source, pending)
        if sha256(pending) != expected_sha:
            raise FixError("Staging checksum differs; active kernel was not replaced.")
        os.replace(str(pending), str(cube.path("/flash/kernel.img")))
        sync_directory(cube.path("/flash"))
        os.sync()
        if sha256(cube.path("/flash/kernel.img")) != expected_sha:
            raise FixError("Active kernel verification failed. Do not reboot; ask for help.")


def install(cube, package):
    cube.root_required()
    report = inspect(cube, package)
    show_report(report)
    if not report["compatible"]:
        raise FixError("This Cube needs a matching build. Install refused.")
    if report["kernel_image_sha256"] == FIXED_SHA:
        print("The fixed kernel is already installed. Nothing changed.")
        return "already-installed"
    payload = Path(package) / "kernel.pq-guard.img"
    if not payload.is_file() or payload.is_symlink() or sha256(payload) != FIXED_SHA:
        raise FixError("Kernel file is missing or damaged. Re-copy the complete package.")
    pending = cube.path("/flash/kernel.cube-dv-fix.pending")
    if pending.exists():
        raise FixError("A previous staging file exists. Preserve it for review; install refused.")
    storage = cube.path("/storage")
    flash = cube.path("/flash")
    reserve = 2 * 1024 * 1024
    backup_needed = not cube.path(BACKUP_DIR).exists()
    flash_required = payload.stat().st_size + reserve
    if os.stat(storage).st_dev == os.stat(flash).st_dev:
        required = flash_required + (report["kernel_image_bytes"] if backup_needed else 0)
        if shutil.disk_usage(flash).free < required:
            raise FixError("Not enough free space to keep a backup and stage the kernel.")
    else:
        if shutil.disk_usage(flash).free < flash_required:
            raise FixError("Not enough free space on the boot volume.")
        if backup_needed and shutil.disk_usage(storage).free < report["kernel_image_bytes"] + reserve:
            raise FixError("Not enough free space for the original kernel backup.")
    cube.flash_options()
    directory, original, manifest, metadata = make_backup(cube, report)
    kodi_was_active = cube.command(["systemctl", "is-active", "kodi"], check=False).returncode == 0
    stopped = False
    activated = False
    try:
        if kodi_was_active:
            stopped = True
            cube.command(["systemctl", "stop", "kodi"])
        # Recheck immediately before activation; do not overwrite a concurrent update.
        if sha256(cube.path("/flash/kernel.img")) != ORIGINAL_SHA:
            raise FixError("The active kernel changed during installation. Stopped.")
        replace_kernel(cube, payload, FIXED_SHA, "kernel.cube-dv-fix.pending")
        activated = True
        metadata["status"] = "installed"
        metadata["installed_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write_json(manifest, metadata)
    finally:
        if stopped and not activated:
            cube.command(["systemctl", "start", "kodi"], check=False)
    print("Installed and verified. Original backup: " + str(original))
    print("Now run: reboot")
    return "installed"


def rollback(cube):
    cube.root_required()
    if read_text(cube.path("/proc/device-tree/model")) != MODEL:
        raise FixError("Rollback is restricted to the tested third-generation Cube.")
    if os_release(cube).get("VERSION") != RELEASE:
        raise FixError("CoreELEC release has changed. Preserve its current kernel for review.")
    directory, original, manifest, metadata = read_backup(cube)
    active = cube.path("/flash/kernel.img")
    if active.is_symlink():
        raise FixError("Boot image is a symbolic link; preserve it for review.")
    current = sha256(active)
    if current == ORIGINAL_SHA:
        print("Original kernel is already restored. Nothing changed.")
        return "already-restored"
    if current != FIXED_SHA:
        raise FixError("Another kernel is installed. It will not be overwritten.")
    cube.command(["systemctl", "stop", "kodi"])
    try:
        replace_kernel(cube, original, ORIGINAL_SHA, "kernel.cube-dv-rollback.pending")
        metadata["status"] = "rolled-back"
        write_json(manifest, metadata)
    except Exception:
        cube.command(["systemctl", "start", "kodi"], check=False)
        raise
    print("Original kernel restored and verified. Now run: reboot")
    return "restored"


def main():
    parser = argparse.ArgumentParser(description="Cube DV fix: check, install, status or rollback")
    parser.add_argument("action", choices=["check", "install", "status", "rollback"])
    parser.add_argument("--no-save", action="store_true", help="Do not save a check report")
    args = parser.parse_args()
    cube = Cube()
    package = Path(__file__).resolve().parent
    try:
        if args.action in ("check", "status"):
            report = inspect(cube, package)
            destination = None
            if args.action == "check" and not args.no_save:
                destination = package / "check-report.json"
                write_json(destination, report)
                config = cube.path("/proc/config.gz")
                if config.is_file():
                    shutil.copyfile(config, package / "kernel-config.gz")
            show_report(report, destination)
            if args.action == "status":
                print("Running fix: " + str(report["runtime_fix_switch"]))
                print("Corrections: " + str(report["runtime_corrections"]))
                if report["kernel_image_sha256"] == FIXED_SHA and report["runtime_fix_switch"] != "Y":
                    print("Fixed image is on disk, but the running guard is not on. Reboot, then check again.")
            return 0 if report["compatible"] else 2
        if args.action == "install":
            install(cube, package)
        else:
            rollback(cube)
        return 0
    except (FixError, OSError, ValueError, subprocess.SubprocessError) as error:
        print("STOP: " + str(error), file=sys.stderr)
        print("No automatic reboot was sent.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
