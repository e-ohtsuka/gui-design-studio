"""GUI Design Studio v0.2: UI操作性・過去テーマ互換性の回帰テスト。"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme_data import BUILTINS, DEFAULT_OPTIONS, load_custom_themes, save_json
from theme_runtime import apply_theme


class CompatibilityTests(unittest.TestCase):
    def test_read_v01_custom_theme_with_new_defaults(self):
        """v0.1のマイテーマをv0.2でも表示できること。"""
        theme = copy.deepcopy(BUILTINS[0])
        theme.update({'id': 'legacy', 'origin': 'custom', 'name': '以前のテーマ'})
        for key in ('choice_label_color', 'choice_font_weight', 'choice_indicator_color',
                    'choice_padding_x', 'choice_padding_y'):
            theme['options'].pop(key)
        with tempfile.TemporaryDirectory() as td:
            save_json(Path(td) / 'legacy.json', theme)
            loaded = load_custom_themes(td)
        self.assertEqual(len(loaded), 1)
        for key in ('choice_label_color', 'choice_font_weight', 'choice_indicator_color',
                    'choice_padding_x', 'choice_padding_y'):
            self.assertEqual(loaded[0]['options'][key], DEFAULT_OPTIONS[key])


class UsabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        cls.tk = tk
        try:
            cls.root = tk.Tk()
        except tk.TclError as exc:
            raise unittest.SkipTest(f'ディスプレイなし: {exc}')
        cls.root.geometry('1350x840+0+0')

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        from gui_design_studio import DesignStudio
        self.window = self.tk.Toplevel(self.root)
        self.window.geometry('1350x840+0+0')
        with patch('gui_design_studio.custom_dir') as get_root:
            self.temp = tempfile.TemporaryDirectory()
            get_root.return_value = Path(self.temp.name)
            self.studio = DesignStudio(self.window)
        self.window.update_idletasks()
        self.window.update()

    def tearDown(self):
        for job in (self.studio.preview_job, self.studio.gallery_job):
            if job is not None:
                self.window.after_cancel(job)
        self.window.destroy()
        self.temp.cleanup()

    def test_gallery_wheel_on_thumbnail_and_caption(self):
        """カード画像や文字の上でもホイールが紐付く。"""
        card = self.studio.gallery_content.winfo_children()[0]
        thumbnail = card.winfo_children()[0]
        label_area = card.winfo_children()[1]
        label = label_area.winfo_children()[0]
        for widget in (thumbnail, label):
            self.assertTrue(widget.bind('<MouseWheel>'))
        self.studio.gallery_canvas.yview_moveto(0)
        self.window.update_idletasks()
        before = self.studio.gallery_canvas.yview()
        self.assertEqual(self.studio._gallery_wheel(SimpleNamespace(delta=-120)), 'break')
        after = self.studio.gallery_canvas.yview()
        self.assertGreater(after[0], before[0])
        self.assertEqual(self.studio._gallery_wheel(SimpleNamespace(delta=0, num=4)), 'break')
        self.assertLess(self.studio.gallery_canvas.yview()[0], after[0])

    def test_component_navigation(self):
        self.studio._focus_option_section('チェック・ラジオ')
        self.assertEqual(self.studio.category_var.get(), 'チェック・ラジオ')
        self.assertEqual(self.studio.edit_tabs.select(),
                         str(self.studio.option_panels['チェック・ラジオ']))
        self.assertIn('choice_indicator_shape', self.studio.option_vars)
        self.assertIn('choice_font_size', self.studio.option_vars)
        self.studio._focus_option_section('文字')
        self.assertEqual(self.studio.category_var.get(), '文字')

    def test_dark_theme_font_controls_contrast(self):
        from tkinter import ttk
        dark = next(x for x in BUILTINS if x['name'] == 'Studio Dark')
        self.studio.select_theme(dark)
        self.studio._refresh_preview()
        font_field = self.studio.option_vars['font_family'][1]
        self.assertEqual(font_field.cget('style'), 'StudioEditor.TCombobox')
        self.assertEqual(self.studio.mode_combo.cget('style'), 'StudioEditor.TCombobox')
        styles = ttk.Style(self.window)
        self.assertEqual(styles.lookup('StudioEditor.TCombobox', 'foreground', ('readonly',)), '#20354E')
        self.assertEqual(styles.lookup('StudioEditor.TCombobox', 'fieldbackground', ('readonly',)), '#FFFFFF')
        self.assertEqual(styles.lookup('Preview.TCombobox', 'fieldbackground', ('readonly',)),
                         dark['colors']['field_background'])

    def test_choice_options_apply_and_export(self):
        from tkinter import ttk
        s = self.studio
        s._option_changed('choice_font_weight', 'bold')
        s._option_changed('choice_label_color', 'accent')
        s._option_changed('choice_indicator_color', 'accent')
        s._option_changed('choice_padding_x', 8)
        s._refresh_preview()
        styles = ttk.Style(self.window)
        self.assertEqual(styles.lookup('Preview.Card.TCheckbutton', 'foreground'),
                         s.current['colors']['accent'])
        self.assertIn('bold', styles.lookup('Preview.Card.TRadiobutton', 'font'))
        data = s._build_export_data()
        self.assertEqual(data['options']['choice_padding_x'], 8)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'theme.json'
            save_json(path, data)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['options']['choice_font_weight'], 'bold')


if __name__ == '__main__':
    unittest.main()
