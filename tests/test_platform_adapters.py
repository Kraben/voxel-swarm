"""Pruebas unitarias para los adaptadores de plataforma (Windows, Linux, macOS)."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import system_adapters


class PlatformAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_adapter_selection(self):
        darwin = system_adapters.get_adapter('darwin')
        self.assertIsInstance(darwin, system_adapters.DarwinAdapter)
        win = system_adapters.get_adapter('win32')
        self.assertIsInstance(win, system_adapters.WindowsAdapter)
        linux = system_adapters.get_adapter('linux')
        self.assertIsInstance(linux, system_adapters.LinuxAdapter)

    def test_windows_adapter_discovery_and_builtins(self):
        adapter = system_adapters.WindowsAdapter()
        apps = adapter.installed_apps(roots=[self.root])
        # Builtin apps must always be present
        names = {a['command'] for a in apps}
        self.assertIn('calc', names)
        self.assertIn('notepad', names)
        self.assertIn('explorer', names)

        # Create a mock Start Menu shortcut
        shortcut = self.root / 'MiPrograma.lnk'
        shortcut.write_bytes(b'dummy shortcut')
        apps_with_shortcut = adapter.installed_apps(roots=[self.root])
        ids = {a['id'] for a in apps_with_shortcut}
        self.assertIn(str(shortcut.resolve()), ids)

    def test_windows_adapter_launch_and_close(self):
        adapter = system_adapters.WindowsAdapter()
        app = {'id': 'calc.exe', 'name': 'Calculadora', 'command': 'calc', 'path': 'calc.exe'}
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='CLOSED', stderr='')
            result = adapter.close_app(app)
            self.assertIn('He cerrado Calculadora', result)

            mock_run.return_value = MagicMock(returncode=0, stdout='NOT_RUNNING', stderr='')
            result2 = adapter.close_app(app)
            self.assertIn('ya estaba cerrada', result2)

            mock_run.return_value = MagicMock(returncode=0, stdout='STILL_RUNNING', stderr='')
            result3 = adapter.close_app(app)
            self.assertIn('Sigue abierta', result3)

    def test_linux_adapter_desktop_file_parsing(self):
        adapter = system_adapters.LinuxAdapter()
        desktop_dir = self.root / 'applications'
        desktop_dir.mkdir()

        # Create valid desktop entry with Spanish localization
        calc_entry = desktop_dir / 'org.gnome.Calculator.desktop'
        calc_entry.write_text("""[Desktop Entry]
Name=Calculator
Name[es]=Calculadora
Comment=Perform arithmetic calculations
Exec=gnome-calculator %u
Icon=org.gnome.Calculator
Terminal=false
Type=Application
Categories=GNOME;GTK;Utility;Calculator;
""")

        # Create hidden desktop entry (must be skipped)
        hidden_entry = desktop_dir / 'hidden.desktop'
        hidden_entry.write_text("""[Desktop Entry]
Name=Hidden Tool
Exec=hidden-tool
NoDisplay=true
Type=Application
""")

        apps = adapter.installed_apps(roots=[desktop_dir])
        self.assertEqual(len(apps), 1)
        app = apps[0]
        self.assertEqual(app['name'], 'Calculadora')
        self.assertEqual(app['executable'], 'gnome-calculator')
        self.assertIn('calculadora', app['aliases'])
        self.assertIn('calculator', app['aliases'])

    def test_linux_adapter_launch_and_close(self):
        adapter = system_adapters.LinuxAdapter()
        app = {'id': '/usr/share/applications/editor.desktop', 'name': 'Editor', 'command': 'editor', 'executable': 'editor'}
        with patch('shutil.which') as mock_which, patch('subprocess.run') as mock_run:
            mock_which.side_effect = lambda cmd: '/usr/bin/' + cmd if cmd in ('gtk-launch', 'pgrep', 'pkill') else None
            adapter.launch_app(app)
            mock_run.assert_called_with(['gtk-launch', 'editor.desktop'], check=True, timeout=10, shell=False)

            # Test close app when process is running and closes
            mock_run.side_effect = [
                MagicMock(returncode=0),  # pgrep: running
                MagicMock(returncode=0),  # pkill -15
                MagicMock(returncode=1),  # pgrep: not running anymore
            ]
            msg = adapter.close_app(app)
            self.assertIn('He cerrado Editor', msg)


if __name__ == '__main__':
    unittest.main()
