"""v0.8.2 regression: visible gallery scrollbar and consistent wheel routing."""
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gui_design_studio import DesignStudio


class GalleryAndPreviewWheelTests(unittest.TestCase):
    def setUp(self):
        self.store = tempfile.TemporaryDirectory()
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.store.cleanup()
            self.skipTest(str(exc))
        self.root.geometry('1210x810+0+0')
        with patch('gui_design_studio.custom_dir', return_value=Path(self.store.name)):
            self.app = DesignStudio(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.store.cleanup()

    def gallery_bar(self, name):
        canvas = self.app.gallery_canvases[name]
        return next(child for child in canvas.master.winfo_children()
                    if isinstance(child, ttk.Scrollbar))

    def event_scrolls(self, target, scroller, *, delta=-120):
        scroller.yview_moveto(0.2)
        self.root.update()
        before = scroller.yview()[0]
        target.event_generate('<MouseWheel>', delta=delta, x=3, y=4)
        self.root.update()
        return before, scroller.yview()[0]

    def test_gallery_scrollbar_visible_at_small_and_large_window(self):
        for geometry in ('980x650', '1210x810', '1600x900'):
            with self.subTest(geometry=geometry):
                self.root.geometry(geometry+'+0+0')
                self.root.update()
                for name in ('配色','形状','マイテーマ','お気に入り'):
                    self.app.gallery_tabs.select(self.app.gallery_pages[name])
                    self.root.update()
                    bar = self.gallery_bar(name)
                    self.assertTrue(bar.winfo_ismapped())
                    self.assertGreaterEqual(bar.winfo_width(), 10)

    def test_theme_card_and_its_nested_color_swatch_scroll_gallery(self):
        canvas = self.app.gallery_canvases['配色']
        card = self.app.gallery_contents['配色'].winfo_children()[0]
        swatch = card.winfo_children()[0].winfo_children()[0].winfo_children()[0]
        for target in (canvas, card, swatch, self.gallery_bar('配色')):
            with self.subTest(widget=str(target)):
                before, after = self.event_scrolls(target, canvas)
                self.assertGreater(after, before)

    def test_gallery_scrollbar_can_drag_without_mouse_wheel(self):
        canvas = self.app.gallery_canvases['配色']
        bar = self.gallery_bar('配色')
        canvas.yview_moveto(0)
        self.root.update()
        first = canvas.yview()[0]
        x = bar.winfo_width() // 2
        elements = [bar.identify(x, y) for y in range(bar.winfo_height())]
        thumb = [i for i, item in enumerate(elements) if item.endswith('.thumb')]
        self.assertTrue(thumb, 'Scrollbar thumb must be visible')
        start = thumb[len(thumb)//2]
        end = min(bar.winfo_height()-10, start+80)
        bar.event_generate('<ButtonPress-1>', x=x, y=start)
        self.root.update()
        bar.event_generate('<B1-Motion>', x=x, y=end)
        self.root.update()
        bar.event_generate('<ButtonRelease-1>', x=x, y=end)
        self.root.update()
        self.assertGreater(canvas.yview()[0], first)

    def test_gallery_x11_wheel(self):
        canvas = self.app.gallery_canvases['配色']
        canvas.yview_moveto(.3)
        self.root.update()
        before = canvas.yview()[0]
        canvas.event_generate('<Button-5>', x=2, y=2)
        self.root.update()
        self.assertGreater(canvas.yview()[0], before)
        canvas.event_generate('<Button-4>', x=2, y=2)
        self.root.update()
        self.assertAlmostEqual(canvas.yview()[0], before, delta=0.002)

    def test_preview_bg_button_slider_entry_wheel_scroll_outer(self):
        canvas = self.app.preview_canvas
        targets = [self.app.preview_area,
                   self.app.preview_samples['ボタン'][-1],
                   self.app.preview_samples['スライダー'][-1],
                   self.app.preview_samples['入力・選択'][2],
                   self.app.preview_vertical_scroll]
        for target in targets:
            with self.subTest(widget=str(target)):
                before, after = self.event_scrolls(target, canvas)
                self.assertGreater(after, before)

    def test_sample_list_tree_and_bar_scroll_themselves_not_outer_preview(self):
        outer = self.app.preview_canvas
        inner = self.app.preview_scrollbar_tree
        for target in (inner, self.app.preview_scrollbar_sample):
            with self.subTest(widget=str(target)):
                outer.yview_moveto(.2)
                inner.yview_moveto(.2)
                self.root.update()
                outer_before = outer.yview()
                inner_before = inner.yview()
                target.event_generate('<MouseWheel>', delta=-120, x=3, y=4)
                self.root.update()
                self.assertEqual(outer.yview(), outer_before)
                self.assertGreater(inner.yview()[0], inner_before[0])

    def test_custom_slider_wheel_still_scrolls_outer_preview(self):
        from theme_runtime import CanvasValueSlider
        self.app.current['render_mode'] = 'hybrid'
        self.app.current['options']['slider_shape'] = 'custom'
        self.app._refresh_preview()
        self.root.update()
        slider = next(w for w in self.app.preview_samples['スライダー']
                      if isinstance(w, CanvasValueSlider))
        before, after = self.event_scrolls(slider, self.app.preview_canvas)
        self.assertGreater(after, before)

    def test_gallery_and_preview_wheel_do_not_affect_each_other(self):
        gallery = self.app.gallery_canvases['配色']
        preview = self.app.preview_canvas
        gallery.yview_moveto(.2)
        preview.yview_moveto(.2)
        self.root.update()
        gallery_before = gallery.yview()
        self.app.preview_samples['ボタン'][-1].event_generate('<MouseWheel>', delta=-120)
        self.root.update()
        self.assertEqual(gallery.yview(), gallery_before)
        preview_before = preview.yview()
        card = self.app.gallery_contents['配色'].winfo_children()[0]
        card.event_generate('<MouseWheel>', delta=-120)
        self.root.update()
        self.assertEqual(preview.yview(), preview_before)

    def test_gallery_scroll_keeps_position_across_refresh(self):
        gallery = self.app.gallery_canvases['配色']
        gallery.yview_moveto(.2)
        self.root.update()
        before = gallery.yview()[0]
        self.app._update_gallery()
        self.root.update()
        self.assertAlmostEqual(gallery.yview()[0], before, delta=0.01)


if __name__ == '__main__':
    unittest.main()
