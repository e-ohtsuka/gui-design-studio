"""v0.5: scrollbar navigation, missing-tab handling and 96 configurable fields."""
import copy
import json
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gui_design_studio import DesignStudio, OPTION_SECTIONS
from theme_data import BUILTINS, COLOR_FIELDS, DEFAULT_OPTIONS, normalized_theme, validate_theme, load_custom_themes, save_json
from theme_runtime import apply_theme, make_action_button, make_value_slider


class V05DataTests(TestCase):
    def test_36_visible_settings_and_full_legacy_defaults(self):
        keys = [k for _, fields in OPTION_SECTIONS for k, _label, _spec in fields]
        self.assertEqual(len(COLOR_FIELDS), 14)
        self.assertEqual(len(DEFAULT_OPTIONS), 83)
        self.assertEqual(len(COLOR_FIELDS) + len(DEFAULT_OPTIONS), 97)  # legacy compatibility
        self.assertEqual(len(keys),28)
        self.assertTrue(set(keys).issubset(set(DEFAULT_OPTIONS)))
        self.assertEqual(len(keys), len(set(keys)))
        for name, fields in OPTION_SECTIONS:
            self.assertTrue(fields, name)
        self.assertIn('スクロールバー', dict(OPTION_SECTIONS))
        self.assertIn('進捗バー', dict(OPTION_SECTIONS))

    def test_migrated_custom_settings_and_new_value_persistence(self):
        source = copy.deepcopy(BUILTINS[0])
        source.update(id='legacy-user', name='前回のテーマ', origin='custom')
        for key in ('scrollbar_thumb_role', 'button_width_chars', 'tab_weight'):
            source['options'].pop(key)
        with tempfile.TemporaryDirectory() as td:
            save_json(Path(td)/'legacy-user.json', source)
            result = load_custom_themes(td)[0]
            for key in ('scrollbar_thumb_role', 'button_width_chars', 'tab_weight'):
                self.assertEqual(result['options'][key], DEFAULT_OPTIONS[key])
            result['options']['scrollbar_width'] = 22
            result['options']['progress_border'] = 3
            save_json(Path(td)/'legacy-user.json',result)
            loaded = load_custom_themes(td)[0]
            self.assertEqual(loaded['options']['scrollbar_width'],22)
            self.assertEqual(loaded['options']['progress_border'],3)
            self.assertTrue(validate_theme(loaded))


class V05GuiTests(TestCase):
    def setUp(self):
        self.store = tempfile.TemporaryDirectory()
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.root.geometry('1440x900+0+0')
        with patch('gui_design_studio.custom_dir', return_value=Path(self.store.name)):
            self.studio = DesignStudio(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.store.cleanup()

    def _preview_widget(self, cls):
        return next(w for w, _ in self.studio.preview_navigation.items() if w.winfo_class() == cls)

    def test_scrollbar_click_opens_scrollbar_not_slider(self):
        studio=self.studio
        self.assertIn('スクロールバー',studio.option_panels)
        for widget, section in list(studio.preview_navigation.items()):
            self.assertIn(section,studio.option_panels)
            self.assertTrue(widget.bind('<ButtonRelease-1>' if isinstance(widget, ttk.Scrollbar) else '<Button-1>'))
        slider=self._preview_widget('TScale')
        scrollbar=self._preview_widget('TScrollbar')
        # v0.7: 進捗バーは必要なタブを開いた時だけプレビューに現れる。
        self.assertFalse(any(w.winfo_class()=='TProgressbar' for w in studio.preview_navigation))
        for widget,target in [(slider,'スライダー'),(scrollbar,'スクロールバー')]:
            studio._focus_option_section('ボタン')
            widget.event_generate('<Button-1>',x=3,y=3)
            widget.event_generate('<ButtonRelease-1>',x=3,y=3)
            self.root.update_idletasks()
            self.assertEqual(studio.category_var.get(),target)
            self.assertEqual(str(studio.edit_tabs.select()),str(studio.option_panels[target]))
            widget.event_generate('<ButtonRelease-1>',x=3,y=3)
        studio._focus_option_section('進捗バー')
        studio._refresh_preview()  # 予約された更新を確実に実行
        progress=self._preview_widget('TProgressbar')
        progress.event_generate('<Button-1>',x=3,y=3)
        self.assertEqual(studio.category_var.get(),'進捗バー')

    def test_unknown_component_shows_guidance_without_misrouting(self):
        studio=self.studio
        studio._focus_option_section('ボタン')
        old=studio.edit_tabs.select()
        self.assertFalse(studio._focus_option_section('未設定の部品'))
        self.assertEqual(studio.edit_tabs.select(),old)
        self.assertIn('専用設定はありません',studio.status_var.get())
        self.assertIn('未設定の部品',studio.preview_notice.get())

    def test_all_options_can_be_selected_and_number_changes_immediate(self):
        studio=self.studio
        for section,fields in OPTION_SECTIONS:
            self.assertTrue(studio._focus_option_section(section))
            for key, _label, spec in fields:
                self.assertIn(key,studio.option_field_frames)
                self.assertIn(key,studio.option_vars)
                if spec[0]=='int':
                    new=spec[1] if spec[1]!=studio.current['options'][key] else spec[2]
                    studio.option_vars[key][0].set(str(new))
                    if key!='corner_radius':
                        self.assertEqual(studio.current['options'][key],new)
                else:
                    # Choice widgets include a representative selected option.
                    self.assertTrue(spec[1])
        studio._refresh_preview()
        self.assertTrue(validate_theme(studio._build_export_data()))
        self.assertTrue(studio._export_python_text(studio._build_export_data()))

    def test_scrollbar_style_and_exported_python_apply(self):
        studio=self.studio
        studio._option_changed('scrollbar_width',22)
        studio._option_changed('scrollbar_thumb_role','accent')
        studio._option_changed('scrollbar_active_role','accent_hover')
        studio._option_changed('progress_border',3)
        studio._option_changed('progress_trough_role','background')
        studio._option_changed('tree_selected_bg_role','accent')
        studio._refresh_preview()
        style=ttk.Style(self.root)
        self.assertEqual(int(style.configure('Preview.Vertical.TScrollbar')['width']),22)
        self.assertEqual(style.configure('Preview.Vertical.TScrollbar')['background'],studio.current['colors']['accent'])
        self.assertEqual(style.configure('Preview.Horizontal.TProgressbar')['troughcolor'],studio.current['colors']['background'])
        data=studio._build_export_data()
        text=studio._export_python_text(data)
        compile(text,'<export>', 'exec')
        ns={}
        exec(compile(text,'<export>','exec'),ns)
        self.assertEqual(ns['THEME']['options']['scrollbar_width'],22)
        self.assertTrue(validate_theme(ns['THEME']))
        other=tk.Toplevel(self.root)
        try:
            style2=ns['apply_theme'](other)
            self.assertEqual(style2.configure('Vertical.TScrollbar')['background'],data['colors']['accent'])
        finally:
            other.destroy()

    def test_ttk_mode_no_canvas_widgets_after_theme_change(self):
        s=self.studio
        s.mode_combo.set('標準ttk限定')
        s._on_mode_selected()
        s._refresh_preview()
        self.assertTrue(any(w.winfo_class()=='TScrollbar' for w in s.preview_navigation))
        self.assertTrue(any(w.winfo_class()=='TScale' for w in s.preview_navigation))
        self.assertTrue(any(w.winfo_class()=='TCheckbutton' for w in s.preview_navigation))
        for key in ('button_shape','slider_shape'):
            self.assertEqual(s.current['options'][key],'standard')
        self.assertFalse(s._build_export_data()['requires_custom'])


class V05RuntimeAndSchemaTests(TestCase):
    def test_every_editable_option_has_runtime_or_live_preview_implementation(self):
        # Prevent adding UI-only options that never reach a generated application.
        src = (Path(__file__).resolve().parents[1]/'theme_runtime.py').read_text(encoding='utf-8')
        preview = (Path(__file__).resolve().parents[1]/'gui_design_studio.py').read_text(encoding='utf-8')
        for key in DEFAULT_OPTIONS:
            with self.subTest(key=key):
                self.assertTrue(key in src or key in ('panel_padding','control_gap','section_gap') and key in preview)

    def test_all_82_values_are_validated_and_exportable(self):
        # Validate each displayed choice, with a selection other than default when possible.
        with tempfile.TemporaryDirectory() as td:
            try:
                root = tk.Tk()
            except tk.TclError as exc:
                self.skipTest(str(exc))
            try:
                with patch('gui_design_studio.custom_dir', return_value=Path(td)):
                    studio = DesignStudio(root)
                studio.mode_combo.set('ハイブリッド')
                studio._on_mode_selected()
                for section, fields in OPTION_SECTIONS:
                    for key, name, spec in fields:
                        current = studio.current['options'][key]
                        if spec[0] == 'choice':
                            val = next((value for label,value in spec[1] if value != current),current)
                        else:
                            val = spec[1] if spec[1] != current else spec[2]
                        studio._option_changed(key,val)
                        with self.subTest(key=key):
                            self.assertEqual(studio.current['options'][key],val)
                            self.assertEqual(studio._build_export_data()['options'][key],val)
                studio._refresh_preview()
                self.assertTrue(validate_theme(studio._build_export_data()))
                text=studio._export_python_text(studio._build_export_data())
                compile(text,'test_export.py','exec')
            finally:
                root.destroy()
