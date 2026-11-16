"""v1.00: narrow windows must retain a usable preview scroll bar."""
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from gui_design_studio import APP_TITLE, DesignStudio

class ReleaseRegressionTests(unittest.TestCase):
    def test_preview_scrollbar_visible_in_narrow_window(self):
        self.assertIn('v1.00', APP_TITLE)
        with tempfile.TemporaryDirectory() as temporary:
            root = tk.Tk()
            self.addCleanup(root.destroy)
            root.geometry('1210x810+0+0')
            with patch('gui_design_studio.custom_dir', return_value=Path(temporary)):
                app = DesignStudio(root)
            root.update()
            bar = app.preview_vertical_scroll
            self.assertTrue(bar.winfo_ismapped())
            self.assertGreater(bar.winfo_width(), 5)
            self.assertGreater(bar.winfo_height(), 20)
            self.assertLess(app.preview_canvas.yview()[1], 1.0)

if __name__ == '__main__':
    unittest.main()
