"""v0.7: preview scrollbar label, on-demand progress, fixed width editor, legacy settings."""
import copy
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gui_design_studio import DesignStudio, OPTION_SECTIONS, EDITABLE_COLOR_KEYS
from theme_data import DEFAULT_OPTIONS


class DataTests(unittest.TestCase):
    def test_scrollbar_editor_uses_two_color_controls_and_legacy_width_is_preserved(self):
        fields = dict(OPTION_SECTIONS)['スクロールバー']
        self.assertEqual({x[0] for x in fields}, {'scrollbar_appearance', 'scrollbar_thumb_role', 'scrollbar_trough_role'})
        self.assertIn('scrollbar_width', DEFAULT_OPTIONS)
        self.assertEqual(len(EDITABLE_COLOR_KEYS) + sum(map(lambda x:len(x[1]), OPTION_SECTIONS)),37)
        self.assertIn('進捗バー', dict(OPTION_SECTIONS))


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.temp.cleanup()
            self.skipTest(str(exc))
        self.root.geometry('1210x810+0+0')
        with patch('gui_design_studio.custom_dir',return_value=Path(self.temp.name)):
            self.app=DesignStudio(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.temp.cleanup()

    def _column_widths(self):
        a=self.app
        return (a.gallery_tabs.master.winfo_width(),
                a.preview_area.master.winfo_width(),
                a.edit_tabs.master.winfo_width())

    def test_scrollbar_title_placed_between_slider_and_list(self):
        a=self.app
        labels = [w.cget('text') for w in a.preview_navigation if w.winfo_class() == 'TLabel']
        self.assertIn('スライダー', labels)
        self.assertIn('スクロールバー', labels)
        self.assertIn('一覧・タブ', labels)
        self.assertLess(labels.index('スライダー'), labels.index('スクロールバー'))
        self.assertLess(labels.index('スクロールバー'), labels.index('一覧・タブ'))
        scrollbar = next(w for w in a.preview_navigation if w.winfo_class()=='TScrollbar')
        scrollbar.event_generate('<Button-1>',x=3,y=3)
        scrollbar.event_generate('<ButtonRelease-1>',x=3,y=3)
        self.assertEqual(a.category_var.get(),'スクロールバー')

    def test_progressbar_only_when_editing_its_tab(self):
        a=self.app
        self.assertNotIn('進捗バー', a.preview_navigation.values())
        a._focus_option_section('進捗バー')
        a._refresh_preview()
        self.assertIn('進捗バー', a.preview_navigation.values())
        self.assertTrue(any(w.winfo_class()=='TProgressbar' for w in a.preview_navigation))
        a._option_changed('progress_color_role','success')
        a._refresh_preview()
        self.assertEqual(a._build_export_data()['options']['progress_color_role'], 'success')
        a._focus_option_section('スライダー')
        a._refresh_preview()
        self.assertNotIn('進捗バー',a.preview_navigation.values())

    def test_sidebar_width_stays_fixed_during_tab_and_style_changes(self):
        a=self.app
        original=self._column_widths()
        self.assertEqual(original[0],330)
        self.assertEqual(original[2],335)
        for name in ('文字', '進捗バー', 'スクロールバー','一覧・タブ','カラー','ボタン', '入力・選択'):
            a._focus_option_section(name)
            a._refresh_preview()
            self.root.update()
            with self.subTest(section=name):
                self.assertEqual(self._column_widths(),original)
        a._option_changed('button_padding_x',24)
        a._refresh_preview();self.root.update()
        self.assertEqual(self._column_widths(),original)
        a._option_changed('font_size',15)
        a._refresh_preview();self.root.update()
        self.assertEqual(self._column_widths(),original)

    def test_window_resize_changes_only_preview_column(self):
        original=self._column_widths()
        self.root.geometry('1050x810+0+0')
        self.root.update()
        resized=self._column_widths()
        self.assertEqual(resized[0],original[0])
        self.assertEqual(resized[2],original[2])
        self.assertLess(resized[1],original[1])

    def test_legacy_width_value_is_saved_but_no_longer_editable(self):
        a=self.app
        a.current['options']['scrollbar_width']=22
        self.assertNotIn('scrollbar_width',a.option_vars)
        a._option_changed('scrollbar_thumb_role','accent')
        a._option_changed('scrollbar_trough_role','surface_alt')
        data=a._build_export_data()
        self.assertEqual(data['options']['scrollbar_width'],22)
        self.assertEqual(data['options']['scrollbar_thumb_role'],'accent')
        self.assertEqual(data['options']['scrollbar_trough_role'],'surface_alt')
        compile(a._export_python_text(data),'design_theme.py','exec')

if __name__=='__main__': unittest.main()
