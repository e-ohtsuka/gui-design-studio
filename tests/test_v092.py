"""v0.9.2 UI final tweaks: tab prominence, card clipping, scroll and footer."""
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
from gui_design_studio import APP_TITLE, DesignStudio, ScrollPanel


class FinalPolishTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.root.geometry('1650x950+0+0')
        with patch('gui_design_studio.custom_dir', return_value=Path(self.temp.name)):
            self.app = DesignStudio(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.temp.cleanup()

    def test_active_tab_has_more_padding_than_inactive(self):
        from tkinter import ttk
        style = ttk.Style(self.root)
        self.assertEqual(tuple(style.lookup('StudioTop.TNotebook.Tab','padding',('selected',))),(10,11))
        self.assertEqual(tuple(style.lookup('StudioTop.TNotebook.Tab','padding',('!selected',))),(10,6))

    def test_shape_cards_fit_gallery(self):
        self.app.gallery_tabs.select(self.app.gallery_pages['形状'])
        self.root.update()
        canvas = self.app.gallery_canvases['形状']
        content = self.app.gallery_contents['形状']
        self.assertEqual(len(content.winfo_children()),4)
        widths = [w.winfo_x()+w.winfo_width() for w in content.winfo_children()]
        self.assertLessEqual(max(widths), canvas.winfo_width()+1)
        self.assertGreater(canvas.winfo_width(),260)

    def test_sidebar_dimensions_and_summary_footer(self):
        self.assertIn('v1.00', APP_TITLE)
        self.assertEqual(self.app.gallery_tabs.master.winfo_width(),330)
        self.assertEqual(self.app.edit_tabs.master.winfo_width(),335)
        label = self.app.theme_summary_label
        self.assertGreater(label.winfo_rooty(), self.app.gallery_tabs.winfo_rooty())
        self.assertIn('配色：Urban',label.cget('textvariable') and self.app.theme_summary.get())

    def test_detail_does_not_scroll_if_everything_fits(self):
        self.app._focus_option_section('ボタン')
        self.root.update()
        panel=self.app.option_panels['ボタン']
        panel.canvas.yview_moveto(0.4)
        self.root.update()
        before=panel.canvas.yview()
        class Wheel: delta = -120
        panel._wheel(Wheel())
        self.assertEqual(before,panel.canvas.yview())
        self.assertAlmostEqual(panel.canvas.yview()[0],0,places=2)

    def test_detail_reset_on_section_change(self):
        self.app._focus_option_section('カラー')
        self.root.update()
        panel=self.app.option_panels['カラー']
        panel.canvas.yview_moveto(0.5)
        self.app._focus_option_section('文字')
        self.root.update()
        self.assertAlmostEqual(self.app.option_panels['文字'].canvas.yview()[0],0,places=2)

if __name__ == '__main__': unittest.main()
