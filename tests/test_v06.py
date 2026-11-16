"""v0.6: 配色/形状の独立選択、36項目の簡素化、旧テーマ互換性。"""
import copy
import json
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from tkinter import ttk
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gui_design_studio import (
    DesignStudio, OPTION_SECTIONS, EDITABLE_COLOR_KEYS, COLOR_PRESETS,
    COLOR_PRESET_NAMES, SHAPE_PRESETS, shape_preset_for)
from theme_data import BUILTINS, DEFAULT_OPTIONS, normalized_theme, load_custom_themes
from theme_runtime import apply_theme, make_action_button, CanvasActionButton


class V06DataTests(unittest.TestCase):
    def test_36_only_visible_and_legacy_defaults_preserved(self):
        keys = [k for _s, group in OPTION_SECTIONS for k, _l, _v in group]
        self.assertEqual(len(keys), 28)
        self.assertEqual(len(EDITABLE_COLOR_KEYS), 9)
        self.assertEqual(len(keys)+len(EDITABLE_COLOR_KEYS), 37)
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(set(keys).issubset(DEFAULT_OPTIONS))
        self.assertEqual(len(DEFAULT_OPTIONS), 83)  # 旧マイテーマ読込用

    def test_curated_colors_are_distinct_and_keep_legacy(self):
        self.assertEqual(len(COLOR_PRESETS), 20)
        self.assertEqual(len(COLOR_PRESET_NAMES), len(set(COLOR_PRESET_NAMES)))
        self.assertEqual(len(BUILTINS), 36)  # 既存のIDは残す
        self.assertIn('Atelier', COLOR_PRESET_NAMES)
        self.assertNotIn('Autumn', COLOR_PRESET_NAMES)
        self.assertNotIn('Sandstone', COLOR_PRESET_NAMES)
        signatures = [tuple(t['colors'].values()) for t in COLOR_PRESETS]
        self.assertEqual(len(signatures), len(set(signatures)))
        self.assertIn('Store Holiday Blue', COLOR_PRESET_NAMES)

    def test_default_tick_and_older_explicit_system_choice_preserved(self):
        self.assertEqual(DEFAULT_OPTIONS['choice_indicator_shape'],'check')
        self.assertTrue(all(t['options']['choice_indicator_shape']=='check' for t in BUILTINS))
        old=copy.deepcopy(BUILTINS[0])
        old['options']['choice_indicator_shape']='system'
        self.assertEqual(normalized_theme(old)['options']['choice_indicator_shape'], 'system')

    def test_shape_presets_are_unique_and_have_safe_standard_modes(self):
        self.assertEqual(len(SHAPE_PRESETS),4)
        for preset in SHAPE_PRESETS:
            opts = copy.deepcopy(DEFAULT_OPTIONS)
            opts.update(preset['values'])
            self.assertEqual(shape_preset_for(opts), preset['id'])
            if not preset['requires_custom']:
                self.assertEqual(opts['button_shape'], 'standard')
                self.assertEqual(opts['slider_shape'], 'standard')


class V06GuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.temp.cleanup()
            self.skipTest(f'ディスプレイがありません: {exc}')
        self.root.geometry('1450x900+0+0')
        with patch('gui_design_studio.custom_dir',return_value=Path(self.temp.name)):
            self.app=DesignStudio(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.temp.cleanup()

    def test_tabs_and_click_color_does_not_change_shape(self):
        s=self.app
        self.assertEqual([s.gallery_tabs.tab(i,'text') for i in range(4)],
                         ['配色','形状','マイテーマ','お気に入り'])
        self.assertEqual(len(s.gallery_contents['配色'].winfo_children()), 20)
        self.assertEqual(len(s.gallery_contents['形状'].winfo_children()), 4)
        s.select_shape_preset(SHAPE_PRESETS[0])
        options=copy.deepcopy(s.current['options'])
        target=next(x for x in COLOR_PRESETS if x['name']=='Noir')
        s.select_color_preset(target)
        self.assertEqual(s.current['colors'], target['colors'])
        self.assertEqual(s.current['options'],options)
        self.assertEqual(s.selected_color_id,target['id'])

    def test_shape_change_preserves_palette_and_editor_choices(self):
        s=self.app
        s.select_color_preset(COLOR_PRESETS[5])
        colors=copy.deepcopy(s.current['colors'])
        s._option_changed('font_size',12)
        s.select_shape_preset(SHAPE_PRESETS[2])
        self.assertEqual(s.current['colors'],colors)
        self.assertEqual(s.current['options']['font_size'],12)
        self.assertEqual(s.current['options']['button_style'],'outline')

    def test_click_on_palette_card_applies_palette(self):
        s=self.app
        cards=s.gallery_contents['配色'].winfo_children()
        first=cards[0]
        self.assertTrue(first.bind('<Button-1>'))
        s.select_shape_preset(SHAPE_PRESETS[2])
        first.event_generate('<Button-1>',x=5,y=5)
        self.root.update_idletasks()
        self.assertEqual(s.selected_color_id, sorted(COLOR_PRESETS,key=lambda x:x['name'].casefold())[0]['id'])
        self.assertEqual(s.current['options']['button_style'],'outline')

    def test_shape_round_blocked_in_standard_mode(self):
        s=self.app
        original=copy.deepcopy(s.current)
        with patch('gui_design_studio.messagebox.showinfo') as info:
            self.assertFalse(s.select_shape_preset(SHAPE_PRESETS[3]))
        info.assert_called_once()
        self.assertEqual(s.current['options'],original['options'])
        self.assertFalse(s._build_export_data()['requires_custom'])

    def test_round_allowed_hybrid_and_export_code_builds_custom_button(self):
        s=self.app
        s.mode_combo.set('ハイブリッド')
        s._on_mode_selected()
        self.assertTrue(s.select_shape_preset(SHAPE_PRESETS[3]))
        data=s._build_export_data()
        self.assertTrue(data['requires_custom'])
        self.assertEqual(data['shape_preset_id'],'shape-rounded')
        self.assertEqual(data['options']['button_shape'],'pill')
        code=s._export_python_text(data)
        ns={'__name__':'exported'}
        exec(compile(code,'design_theme.py','exec'),ns)
        widget=ns['make_action_button'](self.root,'Go',lambda:None)
        self.assertEqual(widget.__class__.__name__, 'CanvasActionButton')
        widget.destroy()

    def test_saved_combination_reopens_and_keeps_legacy_settings(self):
        s=self.app
        s.select_color_preset(next(x for x in COLOR_PRESETS if x['name']=='Store Holiday Blue'))
        s.select_shape_preset(SHAPE_PRESETS[0])
        s.current['options']['button_pressed_role']='selection'  # 以前の細かい値も保持
        with patch('gui_design_studio.simpledialog.askstring',return_value='カレンダー・フラット'):
            s.save_as_custom()
        items=load_custom_themes(s.theme_dir)
        self.assertEqual(len(items),1)
        obj=items[0]
        self.assertEqual(obj['shape_preset_id'],'shape-flat')
        self.assertEqual(obj['color_preset_id'],next(x['id'] for x in COLOR_PRESETS if x['name']=='Store Holiday Blue'))
        self.assertEqual(obj['colors']['accent'],'#1765C7')
        self.assertEqual(obj['options']['button_pressed_role'],'selection')
        self.assertEqual(s.gallery_tabs.tab(s.gallery_tabs.index('current'),'text'),'マイテーマ')

    def test_reset_restore_both_palette_and_shape(self):
        s=self.app
        original=copy.deepcopy(s.base_theme)
        s.select_color_preset(COLOR_PRESETS[-1])
        s.select_shape_preset(SHAPE_PRESETS[0])
        s.reset_to_selected()
        self.assertEqual(s.current['colors'],original['colors'])
        self.assertEqual(s.current['options'],original['options'])
        self.assertFalse(s.dirty)

    def test_native_indicator_restored_from_check(self):
        s=self.app
        style=ttk.Style(self.root)
        self.assertIn('GDSCheck',str(style.layout('Preview.Card.TCheckbutton')))
        s._option_changed('choice_indicator_shape','system')
        s._refresh_preview()
        self.assertNotIn('GDSCheck',str(style.layout('Preview.Card.TCheckbutton')))
        s._option_changed('choice_indicator_shape','check')
        s._refresh_preview()
        self.assertIn('GDSCheck',str(style.layout('Preview.Card.TCheckbutton')))
        check=next(w for w in s.preview_navigation if w.winfo_class()=='TCheckbutton')
        self.assertEqual(check.winfo_class(),'TCheckbutton')

    def test_palette_does_not_repaint_gallery_and_scroll_navigates(self):
        s=self.app
        card=s.gallery_contents['配色'].winfo_children()[0]
        before=card.winfo_children()[0].cget('bg')
        s.select_color_preset(next(t for t in COLOR_PRESETS if t['name']=='Noir'))
        s._refresh_preview()
        self.assertEqual(s.gallery_contents['配色'].winfo_children()[0].winfo_children()[0].cget('bg'),before)
        scrollbar=next(w for w in s.preview_navigation if w.winfo_class()=='TScrollbar')
        scrollbar.event_generate('<Button-1>',x=4,y=4)
        scrollbar.event_generate('<ButtonRelease-1>',x=4,y=4)
        self.assertEqual(s.category_var.get(),'スクロールバー')


if __name__=='__main__':
    unittest.main()
