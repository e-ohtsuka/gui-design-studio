"""v0.8: 汎用部品見本・設定欄と同順・5行スクロールバー・フラット／標準表示。"""
import copy
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gui_design_studio import DesignStudio, OPTION_SECTIONS, EDITABLE_COLOR_KEYS
from theme_data import BUILTINS, DEFAULT_OPTIONS, normalized_theme
from theme_runtime import apply_theme


def _all_elements(layout):
    for name, kw in layout:
        yield name
        yield from _all_elements(kw.get('children', []))


class V08SchemaTests(unittest.TestCase):
    def test_37_settings_include_scroll_appearance(self):
        keys = [k for _section, group in OPTION_SECTIONS for k, _name, _spec in group]
        self.assertEqual(len(keys) + len(EDITABLE_COLOR_KEYS), 37)
        self.assertIn('scrollbar_appearance', keys)
        self.assertEqual(DEFAULT_OPTIONS['scrollbar_appearance'], 'flat')

    def test_older_custom_theme_keeps_original_scrollbar_style(self):
        old = copy.deepcopy(BUILTINS[0])
        old['options'].pop('scrollbar_appearance')
        restored = normalized_theme(old)
        self.assertEqual(restored['options']['scrollbar_appearance'], 'standard')
        self.assertEqual(normalized_theme(BUILTINS[0])['options']['scrollbar_appearance'], 'flat')


class V08GuiTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.td.cleanup()
            self.skipTest(str(exc))
        self.root.geometry('1210x810+0+0')
        with patch('gui_design_studio.custom_dir', return_value=Path(self.td.name)):
            self.app = DesignStudio(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.td.cleanup()

    def test_preview_order_matches_editor_and_uses_generic_labels(self):
        app = self.app
        names = ['カラー', *(name for name, _ in OPTION_SECTIONS if name != '進捗バー')]
        self.assertEqual(list(app.preview_sections), names)
        texts = [w.cget('text') for w in app.preview_navigation if w.winfo_class() == 'TLabel']
        self.assertIn('Entry 1', texts)
        self.assertIn('Select 1', texts)
        self.assertIn('Slider 1', texts)
        self.assertNotIn('現在のフォルダ', texts)
        combo = next(w for w in app.preview_navigation if isinstance(w, ttk.Combobox))
        self.assertEqual(combo.get(), 'Select 1')
        self.assertEqual(app.preview_navigation[combo], '入力・選択')

    def test_sample_scrollbar_is_five_rows_and_actually_scrolls(self):
        app = self.app
        self.assertEqual(int(app.preview_scrollbar_tree['height']), 5)
        self.assertEqual(len(app.preview_scrollbar_tree.get_children()), 16)
        self.assertEqual(str(app.preview_scrollbar_sample.cget('orient')), 'vertical')
        self.assertEqual(app.preview_navigation[app.preview_scrollbar_sample], 'スクロールバー')
        initial = app.preview_scrollbar_tree.yview()
        app.preview_scrollbar_tree.yview_scroll(2, 'units')
        self.assertGreater(app.preview_scrollbar_tree.yview()[0], initial[0])
        app.preview_scrollbar_sample.event_generate('<Button-1>', x=3, y=30)
        app.preview_scrollbar_sample.event_generate('<ButtonRelease-1>', x=3, y=30)
        self.assertEqual(app.category_var.get(), 'スクロールバー')

    def test_preview_has_separate_scrolling_and_preserves_position(self):
        app = self.app
        initial = app.preview_canvas.yview()
        self.assertLess(initial[1], 1.0)
        header = app.preview_sections['ボタン']
        header.event_generate('<MouseWheel>', delta=-120)
        self.root.update()
        self.assertGreater(app.preview_canvas.yview()[0], initial[0])
        app._refresh_preview()
        self.root.update()
        self.assertGreater(app.preview_canvas.yview()[0], 0)
        app._focus_option_section('一覧・タブ')
        self.assertGreater(app.preview_canvas.yview()[0], 0.4)

    def test_slider_scrollbar_and_progress_click_destinations(self):
        app = self.app
        for section, predicate in (
            ('スライダー', lambda w: isinstance(w, ttk.Scale)),
            ('入力・選択', lambda w: isinstance(w, ttk.Entry)),
            ('チェック・ラジオ', lambda w: isinstance(w, ttk.Checkbutton)),
        ):
            sample = next(w for w, dest in app.preview_navigation.items()
                          if dest == section and predicate(w))
            sample.event_generate('<Button-1>', x=5, y=5)
            self.assertEqual(app.category_var.get(), section)
        app._focus_option_section('進捗バー')
        app._refresh_preview()
        self.assertEqual(list(app.preview_sections).index('進捗バー'),
                         list(app.preview_sections).index('スクロールバー') + 1)

    def test_flat_scrollbar_has_plain_image_element_and_can_restore_native(self):
        app = self.app
        style = ttk.Style(self.root)
        target = 'Vertical.Preview.Vertical.TScrollbar'
        flat_layout = str(style.layout(target))
        self.assertIn('GDSFlatThumb', flat_layout)
        self.assertNotIn('Scrollbar.thumb', flat_layout)
        self.assertIsInstance(app.preview_scrollbar_sample, ttk.Scrollbar)
        app._option_changed('scrollbar_appearance', 'standard')
        app._refresh_preview()
        self.assertIn('Scrollbar.thumb', str(style.layout(target)))
        app._option_changed('scrollbar_appearance', 'flat')
        app._refresh_preview()
        self.assertIn('GDSFlatThumb', str(style.layout(target)))
        self.assertEqual(app._build_export_data()['options']['scrollbar_appearance'], 'flat')

    def test_exported_theme_contains_flat_styling(self):
        app = self.app
        code = app._export_python_text(app._build_export_data())
        namespace = {'__name__':'exported_theme'}
        exec(compile(code, 'design_theme.py', 'exec'), namespace)
        self.assertEqual(namespace['THEME']['options']['scrollbar_appearance'], 'flat')
        another = tk.Toplevel(self.root)
        try:
            another.withdraw()
            with patch('gui_design_studio.custom_dir', return_value=Path(self.td.name)):
                namespace['apply_theme'](another)
            style = ttk.Style(another)
            self.assertTrue(any('GDSFlatThumb' in name for name in
                                _all_elements(style.layout('Vertical.TScrollbar'))))
        finally:
            another.destroy()


if __name__ == '__main__':
    unittest.main()
