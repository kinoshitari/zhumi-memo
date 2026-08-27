import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from clipboard_plus.config import data_directory, default_data_directory, set_storage_location


class StoragePointerTests(unittest.TestCase):
    def test_custom_storage_pointer_survives_restart_lookup(self):
        with tempfile.TemporaryDirectory() as folder:
            local = Path(folder) / "local"
            custom = Path(folder) / "custom"
            with patch.dict(os.environ, {"LOCALAPPDATA": str(local)}):
                self.assertEqual(data_directory(), default_data_directory())
                set_storage_location(custom)
                self.assertEqual(data_directory(), custom.resolve())
                set_storage_location(default_data_directory())
                self.assertEqual(data_directory(), default_data_directory())


if __name__ == "__main__":
    unittest.main()
