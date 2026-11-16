"""v0.4: preview-only styling, click navigation, immediate numeric edits, indicator shapes."""
import copy
import json
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from unittest import TestCase, main
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gui_design_studio import DesignStudio
from theme_data import BUILTINS, DEFAULT_OPTIONS, normalized_theme, validate_theme
from theme_runtime import apply_theme, make_action_button, make_value_slider


class V04Tests(TestCase):
    def setUp(self):
        self.storage = tempfile.TemporaryDirectory()
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(str(exc))
        self.root.geometry('1300x800+0+0')
        with patch('gui_design_studio.custom_dir', return_value=Path(self.storage.name)):
            self.studio = DesignStudio(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.storage.cleanup()

    def _theme(self, name):
        return next(t for t in BUILTINS if t['name'] == name)

    def test_all_preview_controls_navigate(self):
        studio = self.studio
        self.assertGreaterEqual(len(studio.preview_navigation), 16)
        required = {'全体・レイアウト', '文字', '入力・選択',
                    'チェック・ラジオ', 'ボタン', 'スライダー', '一覧・タブ'}
        self.assertTrue(required.issubset(set(studio.preview_navigation.values())))
        for widget, section in list(studio.preview_navigation.items()):
            with self.subTest(widget=widget.winfo_class(), section=section):
                self.assertTrue(widget.bind('<ButtonRelease-1>' if widget.winfo_class() == 'TScrollbar' else '<Button-1>'))
                # Ensure the actual event switches to the section, not just a mapping.
                if widget.winfo_class() != 'TScrollbar':
                    widget.event_generate('<Button-1>', x=3, y=3)
                    widget.event_generate('<ButtonRelease-1>', x=3, y=3)
                    self.root.update_idletasks()
                if widget.winfo_class() != 'TScrollbar':
                    self.assertEqual(studio.category_var.get(), section)

    def test_numeric_updates_immediately_without_focusout(self):
        studio = self.studio
        studio._focus_option_section('ボタン')
        self.root.update()
        var, spin, _ = studio.option_vars['button_padding_x']
        self.assertEqual(spin.cget('style'), 'StudioEditor.TSpinbox')
        var.set('21')
        self.assertEqual(studio.current['options']['button_padding_x'], 21)
        self.assertTrue(studio.dirty)
        self.assertIsNotNone(studio.preview_job)
        self.root.after(190, self.root.quit)
        self.root.mainloop()
        self.assertIsNone(studio.preview_job)
        self.assertEqual(ttk.Style(self.root).configure('Preview.Primary.TButton')['padding'][0], round(21 * 0.75))
        var.set('')
        self.assertEqual(studio.current['options']['button_padding_x'], 21)

    def test_theme_editor_stays_unchanged_when_preview_changes(self):
        studio = self.studio
        style = ttk.Style(self.root)
        editor_fg = style.lookup('TLabel', 'foreground')
        editor_bg = style.lookup('TButton', 'background')
        gallery_bg = studio.gallery_contents['配色'].winfo_children()[0].winfo_children()[0].cget('background')
        studio.select_theme(self._theme('Noir'))
        studio._refresh_preview()
        self.assertEqual(style.lookup('TLabel', 'foreground'), editor_fg)
        self.assertEqual(style.lookup('TButton', 'background'), editor_bg)
        self.assertEqual(studio.gallery_contents['配色'].winfo_children()[0].winfo_children()[0].cget('background'), gallery_bg)
        self.assertEqual(style.lookup('Preview.TLabel', 'foreground'), self._theme('Noir')['colors']['text'])

    def test_gallery_tag_stays_custom_in_hybrid(self):
        s = self.studio
        custom = self._theme('Custom Glass')
        s.favorites.add(custom['id'])
        s._update_gallery()
        def get_label():
            for card in s.gallery_contents['お気に入り'].winfo_children():
                labels = card.winfo_children()[1].winfo_children()
                if labels[0].cget('text').endswith('Custom Glass'):
                    return labels[1]
            raise AssertionError('Custom Glass card not found')
        label = get_label()
        self.assertEqual(label.cget('text'), '独自描画テーマ')
        self.assertEqual(label.cget('foreground'), '#637A8D')
        s.mode_combo.set('ハイブリッド')
        s._on_mode_selected()
        s._update_gallery()
        label = get_label()
        self.assertEqual(label.cget('text'), '独自描画テーマ')
        self.assertEqual(label.cget('foreground'), '#637A8D')

    def test_checkbox_cross_and_tick_are_standard_ttk_widgets(self):
        s = self.studio
        style = ttk.Style(self.root)
        for choice in ('cross', 'check', 'system'):
            s._option_changed('choice_indicator_shape', choice)
            s._refresh_preview()
            widget = next(w for w,section in s.preview_navigation.items()
                          if w.winfo_class()=='TCheckbutton')
            self.assertEqual(widget.winfo_class(), 'TCheckbutton')
            layout = str(style.layout('Preview.Card.TCheckbutton'))
            if choice == 'system':
                self.assertIn('Checkbutton.indicator',layout)
            else:
                self.assertIn('GDSCheck',layout)
            data = s._build_export_data()
            self.assertEqual(data['options']['choice_indicator_shape'],choice)
            self.assertTrue(validate_theme(data))
            exported_code = s._export_python_text(data)
            compile(exported_code, '<theme_export>', 'exec')
        s.mode_combo.set('標準ttk限定')
        self.assertEqual(s.current['render_mode'], 'standard_ttk')
        self.assertFalse(s._build_export_data()['requires_custom'])

    def test_old_theme_gains_indicator_default(self):
        data = copy.deepcopy(BUILTINS[0])
        del data['options']['choice_indicator_shape']
        migrated = normalized_theme(data)
        self.assertEqual(migrated['options']['choice_indicator_shape'], 'check')

if __name__ == '__main__':
    main()
