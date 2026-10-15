"""Exercise preflight helpers without touching disks or running installers."""
import pathlib
import subprocess
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "linux/preflight-check.sh"
SOURCE = SCRIPT.read_text()
HELPERS = SOURCE.split("# HEADER")[0].rsplit("# ================================================================", 1)[0]


class PreflightTests(unittest.TestCase):
    def run_shell(self, code):
        result = subprocess.run(["bash", "-c", HELPERS + "\n" + code], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_mount_fallback_source_and_readonly_options(self):
        output = self.run_shell(r'''
command() { if [[ "$1" == -v && "$2" == findmnt ]]; then return 1; fi; builtin command "$@"; }
mount() { printf '%s\n' '/dev/sdb1 on /media/usb type ext4 (ro,nosuid,nodev)' '/dev/sdc1 on /other type ext4 (rw)'; }
resolve_mount_source /media/usb
resolve_mount_options /media/usb
''')
        self.assertEqual(output.splitlines(), ["/dev/sdb1", "ro,nosuid,nodev"])

    def test_invalid_requested_mount_preserves_valid_selection(self):
        output = self.run_shell('''
REQUESTED_MOUNT=/tmp
TARGET_MOUNT=/media/usb
CURRENT_DEVICE=/dev/sdb1
resolve_mount_source() { echo /dev/internal; }
device_visible() { return 0; }
is_removable_or_usb() { return 1; }
if use_requested_mount; then exit 1; fi
printf '%s|%s' "$TARGET_MOUNT" "$CURRENT_DEVICE"
''')
        self.assertEqual(output, "/media/usb|/dev/sdb1")

    def test_failed_io_is_not_reported_as_measured_speed(self):
        for kind, start, end in [("Write", "WRITE_MBPS=0\nWRITE_OK=false", '# ── Read Speed'), ("Read", "READ_MBPS=0\nREAD_OK=false", '# ── USB generation hint')]:
            section = SOURCE[SOURCE.index(start):].split(end)[0]
            result = self.run_shell('''
TMPFILE=$(mktemp)
dd() { return 1; }
sync() { :; }
date() { echo 1000000000; }
''' + section + '\nprintf "COUNTS:%s" "$FAIL_COUNT"')
            self.assertIn(kind + " benchmark failed", result)
            self.assertIn("COUNTS:1", result)


if __name__ == "__main__":
    unittest.main()
