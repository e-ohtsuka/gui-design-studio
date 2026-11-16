"""v0.3: 暗色テーマ追加・標準/マイテーマのタブ・詳細設定・出力互換性。"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from theme_data import BUILTINS, COLOR_FIELDS, DEFAULT_OPTIONS, PALETTES, load_custom_themes, new_custom_theme, save_json, validate_theme
from gui_design_studio import OPTION_SECTIONS, DesignStudio
from theme_runtime import apply_theme, make_action_button, make_value_slider


class V03DataTests(unittest.TestCase):
    def test_preset_and_options_counts(self):
        self.assertEqual(len(BUILTINS), 36)
        self.assertEqual(len(PALETTES), 9)
        self.assertEqual(len(COLOR_FIELDS), 14)
        self.assertGreaterEqual(len(DEFAULT_OPTIONS), 42)
        self.assertEqual(sum(len(fields) for _, fields in OPTION_SECTIONS), 28)
        self.assertTrue({k for _, fields in OPTION_SECTIONS for k, _, _ in fields}.issubset(set(DEFAULT_OPTIONS)))

    def test_all_presets_valid_and_unique(self):
        self.assertEqual(len({x['id'] for x in BUILTINS}), len(BUILTINS))
        self.assertEqual(len({x['name'] for x in BUILTINS}), len(BUILTINS))
        for t in BUILTINS:
            with self.subTest(theme=t['name']):
                self.assertTrue(validate_theme(t))

    def test_original_studio_dark_and_ps_differ(self):
        by_name = {t['name']: t for t in BUILTINS}
        self.assertNotEqual(by_name['Studio Dark']['colors']['accent'],
                            by_name['Photoshop風']['colors']['accent'])
        self.assertEqual(by_name['Studio Dark']['colors']['accent'], '#4B9F92')

    def test_calendar_theme_uses_real_original_palette(self):
        t = next(x for x in BUILTINS if x['name'] == 'Store Holiday Blue')
        self.assertEqual(t['colors']['background'], '#F3F7FD')
        self.assertEqual(t['colors']['accent'], '#1765C7')
        self.assertEqual(t['colors']['text'], '#182C4E')
        self.assertEqual(t['colors']['border'], '#BDD0E7')

    def test_v02_theme_default_options_migrated(self):
        t = copy.deepcopy(BUILTINS[0])
        t.update({'origin':'custom','id':'old-theme','name':'旧テーマ'})
        for new_key in ('font_weight', 'choice_font_size', 'input_focus_role',
                        'progress_color_role', 'tab_selected_text_role'):
            t['options'].pop(new_key)
        with tempfile.TemporaryDirectory() as td:
            save_json(Path(td)/'old-theme.json', t)
            loaded = load_custom_themes(td)
        self.assertEqual(len(loaded), 1)
        for new_key in ('font_weight','choice_font_size','input_focus_role','progress_color_role','tab_selected_text_role'):
            self.assertEqual(loaded[0]['options'][new_key], DEFAULT_OPTIONS[new_key])


class V03GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        cls.tk = tk
        try:
            cls.root = tk.Tk()
        except tk.TclError as exc:
            raise unittest.SkipTest(f'画面なし: {exc}')
        cls.root.geometry('1280x800+0+0')

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.win = self.tk.Toplevel(self.root)
        self.win.geometry('1280x800+0+0')
        with patch('gui_design_studio.custom_dir', return_value=Path(self.tmp.name)):
            self.studio = DesignStudio(self.win)
        self.win.update()

    def tearDown(self):
        self.win.destroy()
        self.tmp.cleanup()

    def test_gallery_tabs_and_click_card(self):
        studio = self.studio
        self.assertEqual(len(studio.gallery_pages), 4)
        self.assertEqual(studio.gallery_tabs.tab(0, 'text'), '配色')
        self.assertEqual(len(studio.gallery_contents['配色'].winfo_children()), 20)
        self.assertEqual(len(studio.gallery_contents['マイテーマ'].winfo_children()), 1)  # empty hint
        names = [t['name'] for t in BUILTINS]
        urban_idx = names.index('Urban')
        forest_idx = names.index('Forest')
        studio.select_theme(BUILTINS[forest_idx])
        self.win.update()
        self.assertEqual(studio.current['name'], 'Forest')
        card = studio.gallery_contents['配色'].winfo_children()[0]
        self.assertTrue(card.bind('<Button-1>'))
        self.assertFalse(any('このテーマを適用' in str(child.cget('text')) for child in card.winfo_children() if 'text' in child.keys()))
        self.assertEqual(studio.current['render_mode'], 'standard_ttk')
        # プレビュー（カード全体）をクリックして適用できる。
        label = card.winfo_children()[1].winfo_children()[0]
        label.event_generate('<Button-1>')
        self.win.update()
        self.assertEqual(studio.current['name'], 'Atelier')

    def test_advanced_settings_and_output(self):
        studio=self.studio
        self.assertEqual(studio.option_field_frames['tree_selected_bg_role'].winfo_manager(), 'grid')
        self.assertNotIn('danger', studio.color_field_frames)
        self.assertEqual(len(studio.color_field_frames), 9)
        studio._option_changed('progress_color_role', 'success')
        studio._option_changed('font_weight', 'bold')
        studio._option_changed('choice_font_size', 13)
        exported=studio._build_export_data()
        self.assertEqual(exported['options']['progress_color_role'], 'success')
        self.assertEqual(exported['options']['font_weight'], 'bold')
        self.assertEqual(exported['options']['choice_font_size'], 13)
        self.assertFalse(exported['requires_custom'])
        source=studio._export_python_text(exported)
        compile(source,'theme_out.py','exec')
        style=apply_theme(self.win,exported)
        self.assertEqual(style.lookup('Horizontal.TProgressbar','background'), exported['colors']['success'])

    def test_save_my_theme_auto_select_my_tab(self):
        studio=self.studio
        with patch('gui_design_studio.simpledialog.askstring', return_value='ブルー改'):
            studio.save_as_custom()
        self.win.update()
        self.assertEqual(studio.current['name'], 'ブルー改')
        self.assertEqual(studio.gallery_tabs.index('current'), 2)
        self.assertTrue((studio.theme_dir/(studio.selected_id+'.json')).is_file())
        self.assertEqual(len(studio.gallery_contents['マイテーマ'].winfo_children()), 1)

    def test_standard_mode_no_canvas_with_new_dark_themes(self):
        studio=self.studio
        dark=next(x for x in BUILTINS if x['name']=='Obsidian')
        studio.select_theme(dark)
        theme=studio._build_export_data()
        btn=make_action_button(self.win,'Test',lambda:None,theme)
        slider=make_value_slider(self.win,self.tk.DoubleVar(value=10),theme)
        try:
            self.assertEqual(btn.winfo_class(),'TButton')
            self.assertEqual(slider.winfo_class(),'TScale')
        finally:
            btn.destroy();slider.destroy()


if __name__ == '__main__':
    unittest.main()
