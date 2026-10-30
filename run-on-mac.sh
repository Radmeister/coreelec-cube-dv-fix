#!/usr/bin/env bash
# Run on the computer, not inside an SSH session on the Cube.
set -euo pipefail

action=${1:-check}
case "$action" in
  check|install|status|rollback) ;;
  *) echo "Use: bash run-on-mac.sh check|install|status|rollback"; exit 1 ;;
esac
package_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
for tool in ssh scp tar; do
  command -v "$tool" >/dev/null || { echo "$tool is required on this computer."; exit 1; }
done
if command -v shasum >/dev/null; then
  hash_file() { shasum -a 256 "$1" | cut -d ' ' -f 1; }
elif command -v sha256sum >/dev/null; then
  hash_file() { sha256sum "$1" | cut -d ' ' -f 1; }
else
  echo "A SHA256 checksum utility is required."; exit 1
fi
expected_payload=071498095ae2362caaea3ff052b3262fadd904fd37bd607128fc307b517e4b10
if [[ ! -f "$package_dir/kernel.pq-guard.img" || ! -f "$package_dir/cube-dv-fix.py" ]]; then
  echo "Download and extract Cube-DV-Fix-v1.1.zip from Releases, then run this helper from that folder."
  exit 1
fi
if [[ "$(hash_file "$package_dir/kernel.pq-guard.img")" != "$expected_payload" ]]; then
  echo "The local kernel checksum differs. Download a fresh release package. Nothing uploaded."
  exit 1
fi

read -r -p "Cube's IPv4 address (from CoreELEC network information): " cube_ip
if [[ ! "$cube_ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
  echo "Enter an IPv4 address such as 192.168.1.50."; exit 1
fi
IFS=. read -r a b c d <<< "$cube_ip"
for part in "$a" "$b" "$c" "$d"; do
  if (( 10#$part > 255 )); then echo "Invalid IPv4 address."; exit 1; fi
done
read -r -p "Label for this Cube [cube] (for example home2, friend or brother): " cube_label
cube_label=${cube_label:-cube}
if [[ ! "$cube_label" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "Use letters, numbers, hyphens or underscores for the label."; exit 1
fi

target="root@$cube_ip"
temporary=$(mktemp -d /tmp/cube-dv-fix.XXXXXX)
control="$temporary/ssh"
cleanup() {
  ssh -S "$control" -O exit "$target" >/dev/null 2>&1 || true
  rm -f "$control"
  rmdir "$temporary" 2>/dev/null || true
}
trap cleanup EXIT
ssh_options=(-o "ControlPath=$control" -o ConnectTimeout=8)
ssh -o ControlMaster=auto -o ControlPersist=600 "${ssh_options[@]}" "$target" true

# Use the same authenticated connection; no password is stored in this package.
copy_files() {
  if scp "${ssh_options[@]}" "$@"; then return 0; fi
  echo "Retrying with the older SCP transfer mode..."
  scp -O "${ssh_options[@]}" "$@"
}
remote() { ssh "${ssh_options[@]}" "$target" "$1"; }

reports_base=${CUBE_DV_REPORTS_DIR:-"$HOME/Downloads/Cube-DV-Fix-Backups"}
backup_dir="$reports_base/$cube_label-$cube_ip-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
# Stream the contents so repeat uploads cannot nest an old package directory.
COPYFILE_DISABLE=1 tar -C "$package_dir" -cf - cube-dv-fix.py kernel.pq-guard.img | remote 'set -e; mkdir -p /storage/Cube-DV-Fix; tar -xf - -C /storage/Cube-DV-Fix'

check_code=0
remote 'python3 /storage/Cube-DV-Fix/cube-dv-fix.py check' || check_code=$?
copy_files "$target:/storage/Cube-DV-Fix/check-report.json" "$backup_dir/check-report.json"
if remote 'python3 -c '\''import json,sys; sys.exit(0 if json.load(open("/storage/Cube-DV-Fix/check-report.json"))["kernel_config_available"] else 1)'\'''; then
  copy_files "$target:/storage/Cube-DV-Fix/kernel-config.gz" "$backup_dir/kernel-config.gz"
fi
echo "Computer reports/backups: $backup_dir"
if (( check_code != 0 )); then
  echo "Nothing was installed. Send check-report.json for a matching build."
  exit "$check_code"
fi
result=$(remote 'python3 -c '\''import json; print(json.load(open("/storage/Cube-DV-Fix/check-report.json"))["status"])'\''')

case "$action" in
  check)
    echo "Check finished. No boot files or settings changed."
    ;;
  status)
    remote 'python3 /storage/Cube-DV-Fix/cube-dv-fix.py status'
    ;;
  install)
    if [[ "$result" == "ALREADY INSTALLED" ]]; then
      echo "This Cube already has the fixed kernel. Nothing changed."
      exit 0
    fi
    if [[ "$result" != "READY TO INSTALL" ]]; then
      echo "Install stopped: $result"; exit 1
    fi
    copy_files "$target:/flash/kernel.img" "$backup_dir/kernel.before-install.img"
    expected=cde2bace4057ce743d26735a81c8323b21fcce638b1649e4bda309568b683d16
    if [[ "$(hash_file "$backup_dir/kernel.before-install.img")" != "$expected" ]]; then
      echo "Computer backup checksum differs. Nothing installed."; exit 1
    fi
    remote 'python3 /storage/Cube-DV-Fix/cube-dv-fix.py install'
    copy_files "$target:/storage/cube-dv-fix-backup/manifest.json" "$backup_dir/manifest.json"
    echo "Kernel installed; original backed up on both Cube and computer. Requesting reboot."
    remote 'sync; systemctl reboot' || echo "Connection closed around reboot. Check the TV for restart."
    ;;
  rollback)
    remote 'python3 /storage/Cube-DV-Fix/cube-dv-fix.py rollback'
    echo "Original kernel restored. Requesting reboot."
    remote 'sync; systemctl reboot' || echo "Connection closed around reboot. Check the TV for restart."
    ;;
esac
