"""GUI Design Studio の自動テスト。TkのGUIテストはディスプレイ環境で実行。"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme_data import (BUILTINS, COLOR_FIELDS, DEFAULT_OPTIONS, PALETTES,
                        load_custom_themes, new_custom_theme, save_json, validate_theme)
from theme_runtime import apply_theme, make_action_button, make_value_slider


class ThemeDataTests(unittest.TestCase):
    def test_builtin_themes(self):
        self.assertGreaterEqual(len(BUILTINS), 12)
        self.assertEqual(len({x['id'] for x in BUILTINS}), len(BUILTINS))
        for item in BUILTINS:
            self.assertTrue(validate_theme(item))

    def test_palette_roles(self):
        for name, palette in PALETTES.items():
            self.assertEqual(len(palette), len(COLOR_FIELDS), name)
            for color in palette:
                self.assertEqual(len(color), 7)
                self.assertTrue(color.startswith('#'))

    def test_custom_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            new = new_custom_theme(BUILTINS[0], '自作テスト')
            path = Path(td)/(new['id']+'.json')
            save_json(path, new)
            loaded = load_custom_themes(td)
            self.assertEqual(len(loaded),1)
            self.assertEqual(loaded[0]['name'],'自作テスト')
            self.assertEqual(loaded[0]['colors'],new['colors'])

    def test_reject_bad_theme(self):
        bad = copy.deepcopy(BUILTINS[0])
        bad['colors']['accent'] = 'not-color'
        with self.assertRaises(ValueError):
            validate_theme(bad)


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        cls.tk = tk
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except tk.TclError as exc:
            raise unittest.SkipTest(f'GUI用ディスプレイがありません: {exc}')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'root'):
            cls.root.destroy()

    def test_apply_ttk_style(self):
        import tkinter.ttk as ttk
        style = apply_theme(self.root, BUILTINS[0])
        self.assertIsInstance(style, ttk.Style)
        self.assertTrue(style.lookup('Primary.TButton','background'))

    def test_standard_widgets_not_canvas(self):
        from tkinter import ttk
        theme = copy.deepcopy(BUILTINS[0])
        theme['render_mode']='standard_ttk'
        theme['options']['button_shape']='pill'  # 設定に紛れ込んでも標準ttkのまま
        theme['options']['slider_shape']='custom'
        button = make_action_button(self.root,'test',lambda:None,theme)
        slider = make_value_slider(self.root,self.tk.DoubleVar(value=20),theme)
        try:
            self.assertIsInstance(button,ttk.Button)
            self.assertIsInstance(slider,ttk.Scale)
        finally:
            button.destroy()
            slider.destroy()

    def test_custom_widgets_when_enabled(self):
        from theme_runtime import CanvasActionButton, CanvasValueSlider
        theme=copy.deepcopy(BUILTINS[-1])
        theme['render_mode']='design'
        button=make_action_button(self.root,'test',lambda:None,theme)
        slider=make_value_slider(self.root,self.tk.DoubleVar(value=20),theme)
        try:
            self.assertIsInstance(button,CanvasActionButton)
            self.assertIsInstance(slider,CanvasValueSlider)
        finally:
            button.destroy()
            slider.destroy()

    def test_save_custom_and_export_files(self):
        from unittest.mock import patch
        from gui_design_studio import DesignStudio
        root=self.tk.Toplevel(self.root)
        root.withdraw()
        studio=DesignStudio(root)
        with tempfile.TemporaryDirectory() as td:
            studio.theme_dir=Path(td)/'themes'
            studio.preferences_file=Path(td)/'prefs.json'
            with patch('gui_design_studio.simpledialog.askstring', return_value='独自ブルー'):
                studio.save_as_custom()
            self.assertEqual(studio.current['name'],'独自ブルー')
            self.assertEqual(len(load_custom_themes(studio.theme_dir)),1)
            selected_id=studio.selected_id
            studio.current['colors']['accent']='#123456'
            studio.overwrite_custom()
            self.assertEqual(load_custom_themes(studio.theme_dir)[0]['colors']['accent'],'#123456')
            filename=Path(td)/'design_theme.json'
            with patch('gui_design_studio.filedialog.asksaveasfilename', return_value=str(filename)):
                with patch('gui_design_studio.messagebox.showinfo'):
                    studio.export_theme()
            self.assertTrue(filename.exists())
            self.assertTrue(filename.with_suffix('.py').exists())
            exported=json.loads(filename.read_text(encoding='utf-8'))
            self.assertEqual(exported['colors']['accent'],'#123456')
            self.assertTrue(validate_theme(exported))
            with patch('gui_design_studio.messagebox.askyesno', return_value=True):
                studio.delete_custom()
            self.assertEqual(len(load_custom_themes(studio.theme_dir)),0)
            self.assertNotEqual(studio.selected_id,selected_id)
        root.destroy()

    def test_studio_and_export_code(self):
        from gui_design_studio import DesignStudio
        root=self.tk.Toplevel(self.root)
        root.withdraw()
        studio=DesignStudio(root)
        with tempfile.TemporaryDirectory() as td:
            studio.theme_dir=Path(td)/'themes'
            studio.preferences_file=Path(td)/'prefs.json'
            studio.apply_palette()
            studio.apply_global_shape('square')
            data=studio._build_export_data()
            self.assertEqual(data['render_mode'],'standard_ttk')
            self.assertFalse(data['requires_custom'])
            source=studio._export_python_text(data)
            compile(source,'design-theme.py','exec')
            namespace={'__name__':'themed_export'}
            exec(compile(source,'design-theme.py','exec'),namespace)
            self.assertEqual(namespace['THEME']['name'],data['name'])
            button=namespace['make_action_button'](root,'Go',lambda:None)
            self.assertEqual(button.winfo_class(),'TButton')
            button.destroy()
        root.destroy()


if __name__ == '__main__':
    unittest.main()
