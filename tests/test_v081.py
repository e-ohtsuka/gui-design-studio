"""v0.8.1 regression: flat scrollbar thumbs must retain draggable track area."""
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gui_design_studio import DesignStudio


class FlatScrollbarRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.temp.cleanup()
            self.skipTest(str(exc))
        self.root.geometry('1210x810+0+0')
        with patch('gui_design_studio.custom_dir', return_value=Path(self.temp.name)):
            self.studio = DesignStudio(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.temp.cleanup()

    @staticmethod
    def scrollbar_elements(bar):
        """Inspect the actual element under each vertical pixel of a scrollbar."""
        x = max(1, bar.winfo_width() // 2)
        items = [bar.identify(x, y) for y in range(bar.winfo_height())]
        thumbs = [y for y, name in enumerate(items) if name.endswith('.thumb')]
        track = [y for y, name in enumerate(items) if name == 'trough']
        return thumbs, track

    def _check_draggable(self, bar, content):
        first, last = content.yview()
        self.assertLess(last - first, 0.9, 'The content should be scrollable')
        thumbs, trough = self.scrollbar_elements(bar)
        self.assertGreater(len(thumbs), 8, 'The thumb should be visible')
        self.assertGreater(len(trough), 8, 'The thumb must not cover the entire track')
        self.assertTrue(thumbs[0] < trough[-1])

        x = bar.winfo_width() // 2
        y = thumbs[0] + 3
        target = min(bar.winfo_height() - 25, y + 55)
        bar.event_generate('<ButtonPress-1>', x=x, y=y)
        self.root.update()
        bar.event_generate('<B1-Motion>', x=x, y=target)
        self.root.update()
        self.assertGreater(content.yview()[0], first,
                           'Dragging the flat thumb must scroll the content')
        bar.event_generate('<ButtonRelease-1>', x=x, y=target)
        self.root.update()

    def test_five_row_sample_scrollbar_can_be_dragged(self):
        self._check_draggable(self.studio.preview_scrollbar_sample,
                              self.studio.preview_scrollbar_tree)

    def test_whole_preview_scrollbar_can_be_dragged(self):
        self._check_draggable(self.studio.preview_vertical_scroll,
                              self.studio.preview_canvas)

    def test_flat_thumbnail_element_name_ends_in_thumb(self):
        style = ttk.Style(self.root)
        for name in ('Vertical.TScrollbar', 'Vertical.Preview.Vertical.TScrollbar'):
            layout = style.layout(name)
            elements = []
            def visit(nodes):
                for element, attrs in nodes:
                    elements.append(element)
                    visit(attrs.get('children', []))
            visit(layout)
            self.assertTrue(any(e.startswith('GDSFlatThumb') and e.endswith('.thumb')
                                for e in elements))

    def test_exported_code_keeps_thumb_recognition(self):
        generated = self.studio._export_python_text(self.studio._build_export_data())
        self.assertIn("element = f'GDSFlatThumb{digest}.thumb'", generated)
        compile(generated, 'design_theme.py', 'exec')


if __name__ == '__main__':
    unittest.main()
