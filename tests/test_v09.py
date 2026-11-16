"""v0.9.1: three-pane layout, status, and unified actions tests."""
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

from gui_design_studio import DesignStudio, APP_TITLE, OPTION_SECTIONS


class StudioFinalShellTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.tmp.cleanup()
            self.skipTest(str(exc))
        self.root.geometry('1400x830+0+0')
        with patch('gui_design_studio.custom_dir', return_value=Path(self.tmp.name)):
            self.app = DesignStudio(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.tmp.cleanup()

    @staticmethod
    def descendants(widget):
        result = [widget]
        for child in widget.winfo_children():
            result.extend(StudioFinalShellTests.descendants(child))
        return result

    def test_no_duplicate_navigation_and_uniform_three_headers(self):
        self.assertIn('v1.00', APP_TITLE)
        all_widgets = self.descendants(self.root)
        labels = [w.cget('text') for w in all_widgets if w.winfo_class() == 'TLabel']
        self.assertEqual(sum('テーマギャラリー' in x for x in labels), 1)
        self.assertEqual(sum('◉  プレビュー' == x for x in labels), 1)
        self.assertEqual(sum('⚙  詳細設定' == x for x in labels), 1)
        heads = [w for w in all_widgets if w.winfo_class() == 'TLabel' and
                 w.cget('style') == 'StudioGroupHeader.TLabel']
        self.assertEqual(len(heads), 3)
        buttons = [w.cget('text') for w in all_widgets if w.winfo_class() == 'Button']
        self.assertEqual(buttons.count('マイテーマに保存'), 1)
        self.assertEqual(buttons.count('ファイルに出力'), 1)
        self.assertEqual(buttons.count('テーマを読込'), 1)
        self.assertIn('先頭へ', buttons)
        self.assertNotIn('ようこそ', buttons)
        self.assertNotIn('テーマをデザイン', buttons)

    def test_gallery_cards_single_column(self):
        cards = self.app.gallery_contents['配色'].winfo_children()
        self.assertEqual(len(cards), 20)
        self.assertTrue(all(int(card.grid_info()['column']) == 0 for card in cards))
        self.assertEqual(len({int(card.grid_info()['row']) for card in cards}), 20)

    def test_editor_value_preserved_across_gallery_tabs(self):
        self.app._option_changed('button_padding_x', 21)
        before = self.app.current['options']['button_padding_x']
        self.app.gallery_tabs.select(self.app.gallery_pages['マイテーマ'])
        self.app.gallery_tabs.select(self.app.gallery_pages['配色'])
        self.assertEqual(self.app.current['options']['button_padding_x'], before)

    def test_own_panels_fixed_width_and_dynamic_center(self):
        initial = (self.app.gallery_tabs.master.winfo_width(),
                   self.app.edit_tabs.master.winfo_width())
        self.assertEqual(initial, (330, 335))
        for name, _ in OPTION_SECTIONS:
            self.app._focus_option_section(name)
        self.root.update()
        final = (self.app.gallery_tabs.master.winfo_width(),
                 self.app.edit_tabs.master.winfo_width())
        self.assertEqual(final, initial)

    def test_theme_summary_updates_on_edit_and_reset(self):
        summary = self.app.theme_summary.get()
        self.assertIn('配色：Urban', summary)
        self.assertIn('形状：', summary)
        self.assertIn('変更なし', summary)
        self.app._option_changed('button_padding_x', 21)
        self.assertIn('未保存', self.app.theme_summary.get())
        self.app.reset_to_selected()
        self.assertNotIn('未保存', self.app.theme_summary.get())

    def test_outline_buttons_have_visible_border(self):
        buttons = [w for w in self.descendants(self.root) if w.winfo_class() == 'Button']
        prominent = {'マイテーマに保存','ファイルに出力','テーマを読込','削除','先頭へ'}
        for b in buttons:
            if b.cget('text') in prominent:
                self.assertEqual(int(b.cget('borderwidth')), 1)
                self.assertEqual(b.cget('relief'), 'solid')


if __name__ == '__main__':
    unittest.main()
