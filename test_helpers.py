"""No network: exercise both computer helpers with synthetic images and SSH/SCP stubs."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
STOCK = b'synthetic original kernel fixture'
FIXED = b'synthetic fixed kernel fixture'
STOCK_SHA = hashlib.sha256(STOCK).hexdigest()
FIXED_SHA = hashlib.sha256(FIXED).hexdigest()
PWSH = os.environ.get('CUBE_TEST_PWSH') or shutil.which('pwsh')

STUB = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
tool = Path(sys.argv[0]).name.split('.')[0]
args = sys.argv[1:]
with open(os.environ['CALL_LOG'], 'a') as log:
    log.write(json.dumps([tool, args]) + '\n')
mode = os.environ['TEST_MODE']
status = ('ALREADY INSTALLED' if mode == 'already' else
          'DIFFERENT BUILD OR HARDWARE — NO INSTALL' if mode == 'unsupported' else
          'READY TO INSTALL')
if tool == 'ssh':
    command = args[-1]
    if 'tar -xf -' in command: sys.stdin.buffer.read()
    if 'kernel_config_available' in command: sys.exit(1)
    if 'json.load' in command and '["status"]' in command: print(status)
    elif command.endswith('cube-dv-fix.py check'):
        print(status)
        sys.exit(2 if mode == 'unsupported' else 0)
    elif command.endswith('cube-dv-fix.py install') and mode == 'install-failure': sys.exit(1)
    elif command.endswith('cube-dv-fix.py rollback') and mode == 'rollback-failure': sys.exit(1)
elif tool == 'scp':
    if mode == 'transfer-failure': sys.exit(1)
    if mode == 'legacy-scp' and '-O' not in args: sys.exit(1)
    source, destination = args[-2:]
    if ':/' in destination: sys.exit(0)
    destination = Path(destination)
    if source.endswith('/check-report.json'):
        destination.write_text(json.dumps({'status': status, 'kernel_config_available': False}))
    elif source.endswith('/flash/kernel.img'):
        destination.write_bytes(b'corrupt' if mode == 'bad-backup' else b'synthetic original kernel fixture')
    elif source.endswith('/manifest.json'): destination.write_text('{}')
    else: sys.exit(1)
'''


class HelperTests(unittest.TestCase):
    helper = 'mac'

    def run_helper(self, mode='normal', action='install', address='192.168.1.50', label='friend'):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        package = root / 'package with spaces'
        package.mkdir()
        script_name = 'run-on-mac.sh' if self.helper == 'mac' else 'run-on-windows.ps1'
        script = package / script_name
        source = (ROOT / script_name).read_text().replace(
            'cde2bace4057ce743d26735a81c8323b21fcce638b1649e4bda309568b683d16', STOCK_SHA).replace(
            '071498095ae2362caaea3ff052b3262fadd904fd37bd607128fc307b517e4b10', FIXED_SHA)
        script.write_text(source)
        (package / 'kernel.pq-guard.img').write_bytes(b'corrupt' if mode == 'bad-payload' else FIXED)
        (package / 'cube-dv-fix.py').write_text('# synthetic fixture\n')
        fakebin = root / 'bin'
        fakebin.mkdir()
        for name in ['ssh', 'scp', 'ssh.exe', 'scp.exe']:
            stub = fakebin / name
            stub.write_text(STUB)
            stub.chmod(0o755)
        log = root / 'calls.jsonl'
        environment = dict(os.environ, CUBE_DV_REPORTS_DIR=str(root / 'reports'),
                           PATH=str(fakebin) + os.pathsep + os.environ['PATH'],
                           CALL_LOG=str(log), TEST_MODE=mode, PYTHONDONTWRITEBYTECODE='1')
        if self.helper == 'mac':
            command = ['bash', str(script), action]
            stdin = address + '\n' + label + '\n'
        else:
            command = [PWSH, '-NoLogo', '-NoProfile', '-File', str(script), action,
                       '-CubeAddress', address, '-CubeLabel', label,
                       '-ReportsDirectory', str(root / 'reports with spaces')]
            stdin = ''
        result = subprocess.run(command, input=stdin, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=environment, timeout=30)
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        commands = [args[-1] for tool, args in calls if tool == 'ssh']
        return result, root, commands, calls

    def test_success_backs_up_before_install_and_reboot(self):
        result, root, commands, calls = self.run_helper()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        backups = list(root.rglob('kernel.before-install.img'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), STOCK)
        backup_index = next(i for i, (tool, args) in enumerate(calls)
                            if tool == 'scp' and args[-2].endswith('/flash/kernel.img'))
        install_index = next(i for i, (tool, args) in enumerate(calls)
                             if tool == 'ssh' and args[-1].endswith('cube-dv-fix.py install'))
        self.assertLess(backup_index, install_index)
        self.assertLess(commands.index('python3 /storage/Cube-DV-Fix/cube-dv-fix.py install'),
                        commands.index('sync; systemctl reboot'))

    def test_wrong_build_reports_without_install_or_reboot(self):
        result, root, commands, _ = self.run_helper('unsupported')
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertTrue(list(root.rglob('check-report.json')))
        self.assertFalse(any(c.endswith(' install') or 'systemctl reboot' in c for c in commands))

    def test_install_failure_never_reboots(self):
        result, _, commands, _ = self.run_helper('install-failure')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('sync; systemctl reboot', commands)

    def test_bad_backup_never_installs(self):
        result, _, commands, _ = self.run_helper('bad-backup')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(c.endswith('cube-dv-fix.py install') for c in commands))

    def test_already_installed_is_idempotent(self):
        result, root, commands, _ = self.run_helper('already')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(list(root.rglob('kernel.before-install.img')))
        self.assertNotIn('sync; systemctl reboot', commands)

    def test_check_does_not_install(self):
        result, _, commands, _ = self.run_helper(action='check')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(any(c.endswith(' install') or 'systemctl reboot' in c for c in commands))

    def test_status_does_not_install(self):
        result, _, commands, _ = self.run_helper(action='status')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('python3 /storage/Cube-DV-Fix/cube-dv-fix.py status', commands)
        self.assertNotIn('sync; systemctl reboot', commands)

    def test_rollback_precedes_reboot(self):
        result, _, commands, _ = self.run_helper(action='rollback')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertLess(commands.index('python3 /storage/Cube-DV-Fix/cube-dv-fix.py rollback'),
                        commands.index('sync; systemctl reboot'))

    def test_failed_rollback_never_reboots(self):
        result, _, commands, _ = self.run_helper('rollback-failure', action='rollback')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('sync; systemctl reboot', commands)

    def test_scp_fallback(self):
        result, _, _, calls = self.run_helper('legacy-scp')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(any(tool == 'scp' and '-O' in args for tool, args in calls))

    def test_transfer_failure_never_installs(self):
        result, _, commands, _ = self.run_helper('transfer-failure')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(c.endswith(' install') or 'systemctl reboot' in c for c in commands))

    def test_invalid_address_never_connects(self):
        result, _, commands, _ = self.run_helper(address='999.1.1.1')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands, [])

    def test_invalid_label_never_connects(self):
        result, _, commands, _ = self.run_helper(label='bad/label')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands, [])

    def test_local_corruption_never_connects(self):
        result, _, commands, _ = self.run_helper('bad-payload')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(commands, [])


@unittest.skipUnless(PWSH, 'Set CUBE_TEST_PWSH to include the PowerShell helper tests.')
class WindowsHelperTests(HelperTests):
    helper = 'windows'


if __name__ == '__main__':
    unittest.main(verbosity=2)
