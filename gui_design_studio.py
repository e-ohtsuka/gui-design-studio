"""GUI Design Studio v1.00

Tkinter / ttk 向けのテーマを選び、部品単位で編集し、JSONとPythonを出力する。
実行: python gui_design_studio.py
標準ライブラリのみ。自作テーマはユーザー設定ディレクトリに自動保存。
"""
from __future__ import annotations

import copy
import json
import pprint
import traceback
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
from pathlib import Path

from theme_data import (
    BUILTINS, COLOR_FIELDS, DEFAULT_OPTIONS, PALETTES, custom_dir,
    load_custom_themes, new_custom_theme, normalized_theme, save_json, validate_theme,
)
from theme_runtime import (
    apply_theme, CanvasActionButton, CanvasValueSlider,
    make_action_button, make_value_slider,
)

APP_TITLE = 'GUI Design Studio v1.00'

# 日常のGUI開発で重要かつ見た目の変化が分かりやすい項目だけを表示。
# 旧テーマの詳細設定はtheme_data側で保持しており、削除・上書きしない。
# 配色9項目 + 部品28項目 = 編集画面で操作できる37項目。
EDITABLE_COLOR_KEYS = ('background', 'surface', 'surface_alt', 'accent', 'text',
                       'muted', 'border', 'field_background', 'selection')
OPTION_SECTIONS = [
    ('全体・レイアウト', [
        ('density','画面密度', ('choice', [('コンパクト','compact'),('標準','normal'),('ゆったり','spacious')])),
        ('panel_padding','パネル内側の余白（px）', ('int',3,30)),
        ('control_gap','部品間の余白（px）', ('int',2,24)),
    ]),
    ('ボタン', [
        ('button_style','ボタンの外観', ('choice',[('フラット','flat'),('立体','raised'),('枠線付き','outline')])),
        ('button_shape','特別なボタン形状', ('choice',[('標準ttk','standard'),('角丸（独自描画）','pill')])),
        ('button_padding_x','左右の余白（px）', ('int',3,30)),
        ('button_padding_y','上下の余白（px）', ('int',2,22)),
    ]),
    ('入力・選択', [
        ('input_padding_x','左右の余白（px）', ('int',2,24)),
        ('input_padding_y','上下の余白（px）', ('int',2,20)),
        ('input_border','入力欄の枠線（px）', ('int',0,4)),
    ]),
    ('チェック・ラジオ', [
        ('choice_indicator_shape','チェックマーク', ('choice',[('✓','check'),('OS標準（環境依存）','system'),('×','cross')])),
        ('choice_indicator_color','マークの色', ('choice',[('本文色','default'),('アクセント色','accent')])),
        ('choice_font_size','選択肢の文字サイズ（pt）', ('int',8,18)),
    ]),
    ('スライダー', [
        ('slider_shape','スライダーの種類', ('choice',[('標準ttk','standard'),('独自描画','custom')])),
        ('slider_thumb_size','つまみの大きさ（px）', ('int',10,28)),
        ('slider_track_color_role','トラックの色', ('choice',[('副パネル','surface_alt'),('枠線','border')])),
    ]),
    ('スクロールバー', [
        ('scrollbar_appearance','つまみの形状', ('choice',[('フラット（横線なし）','flat'),('標準（OS/Tkテーマ準拠）','standard')])),
        ('scrollbar_thumb_role','つまみの色', ('choice',[('副パネル','surface_alt'),('枠線','border'),('アクセント','accent')])),
        ('scrollbar_trough_role','レールの色', ('choice',[('背景','background'),('副パネル','surface_alt'),('枠線','border')])),
    ]),
    ('進捗バー', [
        ('progress_height','太さ（px）', ('int',7,25)),
        ('progress_color_role','進捗色', ('choice',[('メイン色','accent'),('成功色','success'),('注意色','warning')])),
    ]),
    ('文字', [
        ('font_family','フォント', ('choice',[('Yu Gothic UI','Yu Gothic UI'),('Meiryo','Meiryo'),('Segoe UI','Segoe UI'),('Arial','Arial'),('MS Gothic','MS Gothic')])),
        ('font_size','本文サイズ（pt）', ('int',8,16)),
        ('title_size','タイトルサイズ（pt）', ('int',12,26)),
        ('section_size','見出しサイズ（pt）', ('int',9,20)),
    ]),
    ('一覧・タブ', [
        ('row_height','一覧の行高さ（px）', ('int',18,48)),
        ('tree_selected_bg_role','選択行の背景色', ('choice',[('選択色','selection'),('アクセント','accent'),('副パネル','surface_alt')])),
        ('tab_padding_x','タブの左右余白（px）', ('int',5,28)),
    ]),
]

# 36種類の旧標準テーマは読み込み互換性のため維持する一方、
# 配色ギャラリーには重複が少ないものだけを出す。
# 「Atelier」と「Autumn」のように、形状差だけで似ていたものは整理する。
COLOR_PRESET_NAMES = (
    'Urban', 'Forest', 'Atelier', 'Chrome風',
    'Studio Dark', 'Photoshop風', 'Midnight', 'Ocean', 'Sakura',
    'Slate', 'Mint', 'Store Holiday Blue', 'Code Night',
    'Carbon', 'Obsidian', 'Noir', 'Night Forest',
    'Quiet Sand', 'Warm Charcoal', 'Terminal Green',
)
COLOR_PRESETS = [t for name in COLOR_PRESET_NAMES for t in BUILTINS if t['name'] == name]

# 配色とは独立に適用。各形状の変更対象は必要最小限のオプションのみ。
SHAPE_PRESETS = [
    {'id':'shape-flat','name':'フラット','description':'平面的で軽い操作感',
     'requires_custom':False,'values':{'button_style':'flat','button_shape':'standard','slider_shape':'standard'}},
    {'id':'shape-raised','name':'立体','description':'押せることが分かりやすい',
     'requires_custom':False,'values':{'button_style':'raised','button_shape':'standard','slider_shape':'standard'}},
    {'id':'shape-outline','name':'アウトライン','description':'輪郭を強調した業務画面',
     'requires_custom':False,'values':{'button_style':'outline','button_shape':'standard','slider_shape':'standard'}},
    {'id':'shape-rounded','name':'角丸','description':'角丸ボタンのみ独自描画',
     'requires_custom':True,'values':{'button_style':'flat','button_shape':'pill','slider_shape':'standard','corner_radius':18}},
]


def shape_preset_for(options):
    """形状に関係する3項目から現在に近いプリセットを判定。"""
    for preset in SHAPE_PRESETS:
        if all(options.get(key) == value for key, value in preset['values'].items()
               if key in ('button_style','button_shape','slider_shape')):
            return preset['id']
    return None


class ScrollPanel(ttk.Frame):
    """右側設定欄をスクロール表示。デザインの出力先には影響しない。"""
    def __init__(self, master):
        super().__init__(master)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, bg='#F0F5FC')
        self.bar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.bar.pack(side='right', fill='y')
        self.inner = ttk.Frame(self.canvas)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor='nw')
        self.inner.bind('<Configure>', self._update_scrollregion)
        self.canvas.bind('<Configure>', self._canvas_resized)
        self.canvas.bind('<MouseWheel>', self._wheel)
        self.inner.bind('<MouseWheel>', self._wheel)

    def _update_scrollregion(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        # 項目がすべて収まるときは、ホイールで内容が動かないよう固定する。
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            self.canvas.yview_moveto(0)

    def _canvas_resized(self, event):
        self.canvas.itemconfigure(self.window_id, width=event.width)
        self._update_scrollregion()

    def reset_view(self):
        # 別カテゴリに切り替えた際、前のスクロール位置を引き継がない。
        self.canvas.yview_moveto(0)

    def _wheel(self, event):
        first, last = self.canvas.yview()
        if last - first >= 0.999:  # スクロールの必要がないページ
            return 'break'
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, 'units')
        return 'break'


class DesignStudio:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        # 1920×1080を最小想定とし、4Kでも適切な初期ウィンドウサイズにする。
        # Tk/Windows側のDPIスケールを尊重し、画面の論理ピクセル数を使用。
        # 最大化・手動リサイズは従来どおり可能。
        self.root.minsize(980, 600)
        width = min(1880, max(980, round(root.winfo_screenwidth() * 0.86)))
        height = min(1060, max(620, round(root.winfo_screenheight() * 0.88)))
        self.root.geometry(f'{width}x{height}')

        self.store = custom_dir()
        self.theme_dir = self.store/'themes'
        self.preferences_file = self.store/'preferences.json'
        self.pref = self._load_preferences()
        self.favorites = set(self.pref.get('favorites', []))
        self.custom = load_custom_themes(self.theme_dir)
        self.current = copy.deepcopy(BUILTINS[0])
        self.selected_id = self.current['id']
        self.base_theme = copy.deepcopy(self.current)  # 最後に選択したテーマ（戻す用）
        self.selected_color_id = self.current['id']
        self.selected_shape_id = shape_preset_for(self.current['options'])
        self.dirty = False
        self.loading = False
        self.preview_job = None
        self.gallery_job = None
        self.option_vars = {}
        self.option_panels = {}
        self.color_buttons = {}
        self.option_field_frames = {}
        self.option_section_keys = {}
        self.color_field_frames = {}
        self.advanced_var = tk.BooleanVar(value=False)
        self.custom_only_widgets = {}
        self.all_controls = []
        self.sample_controls = []

        self.filter_var = tk.StringVar(value='配色')
        self.search_var = tk.StringVar()
        self.mode_var = tk.StringVar(value='standard_ttk')
        self.family_var = tk.StringVar(value=self.current['palette_family'])
        self.shape_var = tk.StringVar(value='standard')
        self.density_var = tk.StringVar(value='normal')
        self.status_var = tk.StringVar(value='左から配色と形状を選び、必要な項目だけ右で調整してください。')
        self.preview_notice = tk.StringVar(value='')
        self.theme_summary = tk.StringVar(value='')
        # Initialise the studio's *own* neutral ttk styles once. The preview uses
        # Preview.* names, so editing a theme does not repaint the gallery/editor.
        apply_theme(self.root, BUILTINS[0])
        self._build_layout()
        self._refresh_editor_values()
        self._update_gallery()
        self._refresh_preview()
        self._refresh_theme_summary()
        self.root.protocol('WM_DELETE_WINDOW', self._close)
        # テストなどから直接destroy()された場合も、予約済みの描画を破棄する。
        self.root.bind('<Destroy>', self._on_destroy, add='+')

    def _load_preferences(self):
        try:
            result = json.loads(self.preferences_file.read_text(encoding='utf-8'))
            return result if isinstance(result, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_preferences(self):
        save_json(self.preferences_file, {'favorites': sorted(self.favorites)})

    def _all_themes(self):
        return BUILTINS + self.custom

    def _theme_by_id(self, theme_id):
        return next((x for x in self._all_themes() if x['id'] == theme_id), None)

    def _studio_styles(self):
        """スタジオ本体は固定のライトブルー配色。編集中のテーマから独立させる。"""
        st = ttk.Style(self.root)
        st.configure('StudioShell.TFrame', background='#F2F6FD')
        st.configure('StudioSurface.TFrame', background='#FFFFFF')
        st.configure('StudioShellTitle.TLabel', background='#F2F6FD', foreground='#13243E',
                     font=('Yu Gothic UI', 18, 'bold'))
        st.configure('StudioPaneTitle.TLabel', background='#FFFFFF', foreground='#17345F',
                     font=('Yu Gothic UI', 12, 'bold'))
        # 3つの大見出しは同じ高さ・背景色・余白に統一する。
        st.configure('StudioGroupHeader.TLabel', background='#E6F0FD', foreground='#173A67',
                     font=('Yu Gothic UI', 12, 'bold'), padding=(11, 9))
        st.configure('StudioSummary.TLabel', background='#EDF4FE', foreground='#30547A',
                     font=('Yu Gothic UI', 10), padding=(12, 8))
        st.configure('StudioFooterSummary.TLabel', background='#F2F6FD', foreground='#56728F',
                     font=('Yu Gothic UI', 9), padding=(7, 2))
        st.configure('StudioPaneHint.TLabel', background='#FFFFFF', foreground='#667990',
                     font=('Yu Gothic UI', 9))
        st.configure('StudioTop.TNotebook', background='#F2F6FD', borderwidth=0)
        # 選択タブが『凹んで小さく』見えないよう、選択時の上下余白を増やす。
        # 下のページと面がつながるChrome風の表現。標準ttkだけで描画する。
        st.configure('StudioTop.TNotebook.Tab', background='#E2ECFA', foreground='#4C5F78',
                     bordercolor='#B8CEE9', borderwidth=1,
                     font=('Yu Gothic UI', 10), padding=(10, 6))
        st.map('StudioTop.TNotebook.Tab',
               background=[('selected', '#FFFFFF'), ('active', '#F5F9FF')],
               foreground=[('selected', '#115DBB')],
               padding=[('selected', (10, 11)), ('!selected', (10, 6))],
               bordercolor=[('selected', '#5A93D7')])
        st.configure('StudioPrimary.TButton', background='#1765C7', foreground='#FFFFFF',
                     padding=(14, 10), bordercolor='#1765C7',
                     font=('Yu Gothic UI', 10, 'bold'))
        st.map('StudioPrimary.TButton', background=[('pressed', '#0B4FA3'), ('active', '#2777DE')],
               foreground=[('active', '#FFFFFF')])
        st.configure('StudioSecondary.TButton', background='#FFFFFF', foreground='#1759A5',
                     padding=(12, 9), bordercolor='#A9C4E7',
                     font=('Yu Gothic UI', 10, 'bold'))
        st.map('StudioSecondary.TButton', background=[('pressed', '#DFECFC'), ('active', '#F0F7FF')])

    def _studio_button(self, parent, text, command, *, primary=False, compact=False):
        """押せることが分かる枠線付きボタン。内部GUIのみで使用。"""
        return tk.Button(
            parent, text=text, command=command, cursor='hand2',
            bg='#1765C7' if primary else '#FFFFFF',
            fg='#FFFFFF' if primary else '#1759A5',
            activebackground='#0B4FA3' if primary else '#E7F1FD',
            activeforeground='#FFFFFF' if primary else '#1759A5',
            borderwidth=1, relief='solid',
            highlightthickness=0, padx=9 if compact else 13,
            pady=4 if compact else 7,
            font=('Yu Gothic UI', 9 if compact else 10, 'bold'))

    def _refresh_theme_summary(self):
        """現在の配色・形状と未保存状態を表示。テーマの実データは変更しない。"""
        palette = next((t['name'] for t in COLOR_PRESETS
                        if t['id'] == self.selected_color_id), None)
        if palette is None:
            palette = self.current.get('name', 'カスタム')
        shape = next((p['name'] for p in SHAPE_PRESETS
                      if p['id'] == self.selected_shape_id), 'カスタム')
        suffix = '  ｜  ● 未保存の変更あり' if self.dirty else '  ｜  変更なし'
        self.theme_summary.set(f'現在の配色：{palette}    ＋    形状：{shape}{suffix}')

    def _navigate_studio(self, action):
        """旧画面の重複ナビは廃止。旧呼び出しには対応する。"""
        if action == 'theme':
            self.gallery_tabs.select(self.gallery_pages['配色'])
            self._focus_option_section('カラー')
        elif action == 'mine':
            self.gallery_tabs.select(self.gallery_pages['マイテーマ'])
        elif action == 'favorite':
            self.gallery_tabs.select(self.gallery_pages['お気に入り'])
        elif action == 'import':
            self.import_theme()
        elif action == 'export':
            self.export_theme()
        elif action == 'help':
            self.show_about()

    def _build_layout(self):
        """シンプルな3カラム構成。上部疑似タブと左ナビの重複を解消。"""
        self._create_menu()
        self._studio_styles()
        shell = ttk.Frame(self.root, style='StudioShell.TFrame')
        shell.pack(fill='both', expand=True)

        header = ttk.Frame(shell, style='StudioSurface.TFrame', padding=(16, 12))
        header.pack(fill='x')
        # 操作の重要度と保存先が一目で分かる文言にする。
        self._studio_button(header, 'ファイルに出力', self.export_theme, primary=True).pack(side='right')
        self._studio_button(header, 'マイテーマに保存', self.save_as_custom).pack(
            side='right', padx=(0, 9))
        ttk.Label(header, text='GUI Design Studio', style='StudioPaneTitle.TLabel',
                  font=('Yu Gothic UI', 17, 'bold')).pack(side='left')
        ttk.Label(header, text='  配色と形状を選び、部品の見た目を調整',
                  style='StudioPaneHint.TLabel').pack(side='left', padx=8)

        main = ttk.Frame(shell, style='StudioShell.TFrame', padding=(8, 7, 8, 5))
        main.pack(fill='both', expand=True)
        # 左右を固定し中央だけ伸縮。幅変更のたびに各欄が揺れないようにする。
        # 形状カード2列を収めるため左側を45px増やす。中央プレビューは十分広い。
        main.columnconfigure(0, weight=0, minsize=330)
        main.columnconfigure(1, weight=1, minsize=250)
        main.columnconfigure(2, weight=0, minsize=335)
        main.rowconfigure(0, weight=1)
        left = ttk.Frame(main, style='StudioSurface.TFrame', padding=8)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 7))
        left.configure(width=330)
        left.pack_propagate(False)
        center = ttk.Frame(main, style='StudioSurface.TFrame', padding=8)
        center.grid(row=0, column=1, sticky='nsew', padx=(0, 7))
        right = ttk.Frame(main, style='StudioSurface.TFrame', padding=8)
        right.grid(row=0, column=2, sticky='nsew')
        right.configure(width=335)
        right.pack_propagate(False)
        self._build_gallery(left)
        self._build_editor(right)
        self._build_preview(center)

        footer = ttk.Frame(shell, style='StudioShell.TFrame', padding=(14, 7))
        footer.pack(fill='x')
        # 操作結果は左、配色・形状・保存状態は下部右側の補助情報にまとめる。
        self._studio_button(footer, 'テーマ全体を元に戻す',
                            self.reset_to_selected, compact=True).pack(side='right')
        self.theme_summary_label = ttk.Label(footer, textvariable=self.theme_summary,
                                             style='StudioFooterSummary.TLabel')
        self.theme_summary_label.pack(side='right', padx=(10, 15))
        ttk.Label(footer, textvariable=self.status_var, style='Muted.TLabel').pack(
            side='left', fill='x', expand=True)

    def _create_menu(self):
        bar = tk.Menu(self.root)
        menu = tk.Menu(bar, tearoff=0)
        menu.add_command(label='テーマをインポート…', command=self.import_theme)
        menu.add_command(label='JSON + Pythonを出力…', command=self.export_theme)
        menu.add_separator()
        menu.add_command(label='終了', command=self._close)
        bar.add_cascade(label='ファイル', menu=menu)
        themes = tk.Menu(bar, tearoff=0)
        themes.add_command(label='マイテーマに名前を付けて保存…', command=self.save_as_custom)
        themes.add_command(label='現在のマイテーマに上書き', command=self.overwrite_custom)
        themes.add_command(label='現在のマイテーマを削除', command=self.delete_custom)
        themes.add_separator()
        themes.add_command(label='お気に入りを切り替える', command=self.toggle_favorite)
        bar.add_cascade(label='テーマ', menu=themes)
        help_menu = tk.Menu(bar, tearoff=0)
        help_menu.add_command(label='このツールについて', command=self.show_about)
        bar.add_cascade(label='ヘルプ', menu=help_menu)
        self.root.configure(menu=bar)

    def _build_gallery(self, parent):
        """タブ別の2列ギャラリー。テーマカード全体を押して適用する。"""
        ttk.Label(parent, text='▦  テーマギャラリー', style='StudioGroupHeader.TLabel').pack(
            fill='x', pady=(0, 8))
        ttk.Label(parent, text='配色と形状を別々に選択できます。',
                  style='StudioPaneHint.TLabel').pack(anchor='w', pady=(0, 7))
        self.gallery_tabs = ttk.Notebook(parent, style='StudioTop.TNotebook')
        self.gallery_tabs.pack(fill='both', expand=True)
        self.gallery_pages = {}
        self.gallery_canvases = {}
        self.gallery_contents = {}
        for tab_name in ('配色', '形状', 'マイテーマ', 'お気に入り'):
            tab = ttk.Frame(self.gallery_tabs)
            self.gallery_tabs.add(tab, text=tab_name)
            self.gallery_pages[tab_name] = tab
            outer = ttk.Frame(tab)
            outer.pack(fill='both', expand=True)
            # 親パネルが固定幅なのでCanvasの要求幅を抑え、先にスクロールバー
            # の幅を確保する。旧実装ではバーが1pxまで縮小されることがあった。
            canvas = tk.Canvas(outer, highlightthickness=0, bd=0,
                               bg='#F4F8FE', width=190)
            bar = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
            canvas.configure(yscrollcommand=bar.set)
            bar.pack(side='right', fill='y')
            canvas.pack(side='left', fill='both', expand=True)
            content = tk.Frame(canvas, bg='#F4F8FE')
            item = canvas.create_window((0, 0), window=content, anchor='nw')
            content.columnconfigure(0, weight=1, uniform='theme_col')
            content.columnconfigure(1, weight=1, uniform='theme_col')
            content.bind('<Configure>', lambda e, cv=canvas: cv.configure(
                scrollregion=cv.bbox('all')))
            canvas.bind('<Configure>', lambda e, cv=canvas, it=item: cv.itemconfigure(
                it, width=e.width))
            # カード・空白・つまみ上のどこでも、同じギャラリーを移動する。
            # 全アプリへのbind_all()は使わず、このギャラリー内だけを対象にする。
            for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                handler = lambda e, cv=canvas: self._gallery_wheel(e, cv)
                canvas.bind(sequence, handler)
                content.bind(sequence, handler)
                bar.bind(sequence, handler)
            self.gallery_canvases[tab_name] = canvas
            self.gallery_contents[tab_name] = content
        self.gallery_tabs.bind('<<NotebookTabChanged>>', self._gallery_tab_changed)
        self.gallery_canvas = self.gallery_canvases['配色']
        self.gallery_content = self.gallery_contents['配色']
        # 検索欄はタブと独立。選択中のテーマグループだけを絞り込む。
        searchbar = ttk.Frame(parent)
        searchbar.pack(fill='x', pady=(7,6), before=self.gallery_tabs)
        ttk.Label(searchbar, text='検索:', style='Muted.TLabel').pack(side='left')
        self.search_entry = ttk.Entry(searchbar, textvariable=self.search_var)
        self.search_entry.pack(side='left', fill='x', expand=True, padx=(4,4))
        self._studio_button(searchbar, '☆', self.toggle_favorite, compact=True).pack(side='right')
        self.search_var.trace_add('write', lambda *_: self._schedule_gallery())
        actions = ttk.Frame(parent)
        actions.pack(fill='x', pady=(5,0))
        self._studio_button(actions, 'テーマを読込', self.import_theme,
                            compact=True).pack(side='left', fill='x', expand=True, padx=(0, 4))
        self._studio_button(actions, '削除', self.delete_custom,
                            compact=True).pack(side='left', fill='x', expand=True)

    def _gallery_tab_changed(self, event=None):
        index = self.gallery_tabs.index('current')
        name = ('配色', '形状', 'マイテーマ', 'お気に入り')[index]
        self.filter_var.set(name)
        self.gallery_canvas = self.gallery_canvases[name]
        self.gallery_content = self.gallery_contents[name]

    @staticmethod
    def _wheel_steps(event):
        """Windowsのホイール差分とX11のButton-4/5をスクロール量に変換。"""
        delta = getattr(event, 'delta', 0)
        if delta:
            direction = -1 if delta > 0 else 1
            return direction * max(1, abs(int(delta)) // 120)
        num = getattr(event, 'num', None)
        return -1 if num == 4 else 1 if num == 5 else 0

    def _gallery_wheel(self, event, canvas=None):
        """カード・画像・文字・スクロールバー上でギャラリーをスクロール。"""
        steps = self._wheel_steps(event)
        if steps:
            (canvas if canvas is not None else self.gallery_canvas).yview_scroll(steps, 'units')
        return 'break'

    def _bind_gallery_wheel(self, widget, canvas=None):
        """bind_allを使わず、ギャラリー内のウィジェットにのみ登録する。"""
        for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            widget.bind(sequence, lambda e, cv=canvas: self._gallery_wheel(e,cv), add='+')
        for child in widget.winfo_children():
            self._bind_gallery_wheel(child, canvas)

    def _build_preview(self, parent):
        ttk.Label(parent, text='◉  プレビュー', style='StudioGroupHeader.TLabel').pack(
            fill='x', pady=(0, 7))
        ttk.Label(parent, text='各部品をクリックすると右側の編集欄に移動します。',
                  style='StudioPaneHint.TLabel', wraplength=400).pack(fill='x', pady=(0, 6))
        # 各部品の見本は設定項目と同順で縦に並べる。見本が増えてもウィンドウを
        # 拡大させずに済むよう、中央プレビューだけ独立してスクロールさせる。
        preview_holder = ttk.Frame(parent)
        preview_holder.pack(fill='both', expand=True)
        self.preview_canvas = tk.Canvas(preview_holder, highlightthickness=0,
                                        borderwidth=0, bg='#F0F5FC')
        self.preview_vertical_scroll = ttk.Scrollbar(preview_holder, orient='vertical',
                                                      command=self.preview_canvas.yview)
        self.preview_canvas.configure(yscrollcommand=self.preview_vertical_scroll.set)
        # 狭いウィンドウでもスクロールバーがCanvasの要求幅に押し出されないよう、
        # 右側のバーを先に配置してからCanvasに残り幅を割り当てる。
        self.preview_vertical_scroll.pack(side='right', fill='y')
        self.preview_canvas.pack(side='left', fill='both', expand=True)
        # つまみ上のホイールも外側プレビューのスクロールに統一する。
        for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            self.preview_vertical_scroll.bind(sequence, self._preview_wheel)
        self.preview_area = ttk.Frame(self.preview_canvas)
        self.preview_window_id = self.preview_canvas.create_window(
            (0, 0), window=self.preview_area, anchor='nw')
        self.preview_area.bind('<Configure>', self._preview_content_resized, add='+')
        self.preview_canvas.bind('<Configure>', self._preview_canvas_resized, add='+')
        self.preview_canvas.bind('<MouseWheel>', self._preview_wheel, add='+')
        self.preview_canvas.bind('<Button-4>', self._preview_wheel, add='+')
        self.preview_canvas.bind('<Button-5>', self._preview_wheel, add='+')
        self.preview_area.bind('<Button-1>', lambda _e: self._focus_option_section('全体・レイアウト'), add='+')
        bottom = ttk.Frame(parent)
        bottom.pack(fill='x', pady=(8,0))
        self._studio_button(bottom, '先頭へ',
                            lambda: self.preview_canvas.yview_moveto(0),
                            compact=True).pack(side='right', padx=(7, 0))
        ttk.Label(bottom, textvariable=self.preview_notice,
                  style='Muted.TLabel', wraplength=480).pack(side='left', fill='x', expand=True)

    def _preview_content_resized(self, _event=None):
        if self.preview_canvas.winfo_exists():
            self.preview_canvas.configure(scrollregion=self.preview_canvas.bbox('all'))

    def _preview_canvas_resized(self, event):
        if self.preview_canvas.winfo_exists():
            self.preview_canvas.itemconfigure(self.preview_window_id, width=max(1, event.width))

    def _preview_wheel(self, event):
        """中央プレビューをスクロール。ボタンやスライダー上でも有効。"""
        steps = self._wheel_steps(event)
        if steps:
            self.preview_canvas.yview_scroll(steps, 'units')
        return 'break'

    def _sample_list_wheel(self, event):
        """5行のサンプル一覧上では、その一覧だけをスクロールする。"""
        steps = self._wheel_steps(event)
        if steps:
            self.preview_scrollbar_tree.yview_scroll(steps, 'units')
        return 'break'

    def _bind_preview_wheel(self, widget):
        """プレビューの子孫すべてに一度だけホイール操作を登録する。

        Treeviewとそのスクロールバーだけは内側の5行リストを動かし、
        スライダーやその他の見本上では外側プレビューを動かす。
        bind_allは使わず、右側エディタやギャラリーへ影響させない。
        """
        if widget is getattr(self, 'preview_scrollbar_tree', None) or \
           widget is getattr(self, 'preview_scrollbar_sample', None):
            handler = self._sample_list_wheel
        else:
            handler = self._preview_wheel
        for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
            widget.bind(sequence, handler, add='+')
        for child in widget.winfo_children():
            self._bind_preview_wheel(child)

    def _build_editor(self, parent):
        # 配色と形状は左ギャラリーから個別に選ぶ。右は微調整専用。
        ttk.Label(parent, text='⚙  詳細設定', style='StudioGroupHeader.TLabel').pack(
            fill='x', pady=(0, 10))
        # 部品名から設定先を探せる。小さい画面でタブが隠れても移動できる。
        nav = ttk.Frame(parent)
        nav.pack(fill='x', pady=(6, 2))
        ttk.Label(nav, text='対象部品', style='Section.TLabel').pack(side='left', padx=(0, 6))
        self.category_var = tk.StringVar(value='カラー')
        self.category_combo = ttk.Combobox(
            nav, state='readonly', style='StudioEditor.TCombobox',
            textvariable=self.category_var, values=['カラー', *(name for name, _ in OPTION_SECTIONS)])
        self.category_combo.pack(side='left', fill='x', expand=True)
        self.category_combo.bind('<<ComboboxSelected>>',
                                 lambda _e: self._focus_option_section(self.category_var.get()))
        ttk.Label(parent, text='よく使う設定37項目に絞っています。',
                  style='StudioPaneHint.TLabel').pack(anchor='w', pady=(4,0))
        self.mode_container = ttk.Frame(parent, style='StudioSurface.TFrame')
        self.mode_container.pack(side='bottom', fill='x', pady=(8, 1))
        ttk.Label(self.mode_container, text='描画方式', style='StudioPaneTitle.TLabel').pack(anchor='w')
        # モード選択UIは設定欄に置く。変数や処理は従来のまま。
        mode_choices = [('標準ttk限定', 'standard_ttk'),
                        ('ハイブリッド', 'hybrid'), ('デザイン優先', 'design')]
        self.mode_combo = ttk.Combobox(self.mode_container, state='readonly', width=18,
                style='StudioEditor.TCombobox',
                values=[label for label, _ in mode_choices])
        self.mode_combo.pack(fill='x', pady=(3, 2))
        self.mode_combo.set(mode_choices[0][0])
        self.mode_combo.bind('<<ComboboxSelected>>', self._on_mode_selected)
        self.mode_choices = mode_choices
        self.mode_label = ttk.Label(self.mode_container, style='Muted.TLabel',
                                    text='軽量・互換性重視：出力先で独自描画しません。', wraplength=400)
        self.mode_label.pack(fill='x', pady=(1, 5))
        # 項目別のページ切替は上のコンボボックスに一本化。
        # Notebookの大量のタブを狭い固定幅へ詰め込むと文字が読めないため、
        # タブ見出しを非表示にし、ページ切替機能だけを内部で利用する。
        editor_style = ttk.Style(self.root)
        editor_style.layout('StudioTabless.TNotebook',
                            [('Notebook.client', {'sticky': 'nswe'})])
        editor_style.layout('StudioTabless.TNotebook.Tab', [])
        self.edit_tabs = ttk.Notebook(parent, style='StudioTabless.TNotebook')
        self.edit_tabs.pack(fill='both', expand=True, pady=(6,0))
        self._build_color_tab()
        short_tabs = {'全体・レイアウト': '全体', '入力・選択': '入力',
                      'チェック・ラジオ': '選択部品', '一覧・タブ': '一覧'}
        for section, fields in OPTION_SECTIONS:
            panel = ScrollPanel(self.edit_tabs)
            self.option_panels[section] = panel
            self.edit_tabs.add(panel, text=short_tabs.get(section, section))
            self.option_section_keys[section] = tuple(key for key, _, _ in fields)
            if section == 'スクロールバー':
                ttk.Label(panel.inner,
                          text='つまみの長さは表示範囲に応じて自動調整されます。\n'
                               'バーの太さはOS・Tkテーマに依存するため設定対象外です。',
                          style='Muted.TLabel', wraplength=265, justify='left').grid(
                              row=0, column=0, sticky='ew', padx=8, pady=(8, 2))
            for key, label, spec in fields:
                self._build_option_field(panel.inner, key, label, spec)
        self.edit_tabs.bind('<<NotebookTabChanged>>', self._on_tab_changed)
        self._enable_custom_controls()
        self._update_option_visibility()

    def _update_option_visibility(self):
        """v0.6は絞り込んだ項目をすべて表示。旧テーマの追加値は保持する。"""
        for frame in self.option_field_frames.values():
            frame.grid()
        for frame in self.color_field_frames.values():
            frame.grid()

    def _focus_option_section(self, section):
        """プレビュー上の部品から設定へ案内。該当項目がなくても誤誘導しない。"""
        panel = self.option_panels.get(section)
        if panel is None:
            message = f'「{section}」の専用設定はありません。全体またはカラーで調整してください。'
            self.preview_notice.set(message)
            self.status_var.set(message)
            return False
        keys = self.option_section_keys.get(section, ())
        if keys and not self.advanced_var.get() and not any(
                self.option_field_frames[key].winfo_manager() for key in keys):
            self.advanced_var.set(True)
            self._update_option_visibility()
        self.edit_tabs.select(panel)
        self.category_var.set(section)
        self.preview_notice.set(f'「{section}」の設定を右側に表示しています。')
        # 右側から編集対象を選択したとき、中央の同名見本が画面外なら移動する。
        # 進捗バーは必要時だけ作るため、選択直後に見本を生成する。
        if section == '進捗バー' and section not in getattr(self, 'preview_sections', {}):
            self._refresh_preview()
        self._scroll_to_preview_section(section)
        return True

    def _scroll_to_preview_section(self, section):
        target = getattr(self, 'preview_sections', {}).get(section)
        if target is None or not target.winfo_exists():
            return
        self.preview_canvas.update_idletasks()
        view_h = self.preview_canvas.winfo_height()
        y = target.winfo_y()
        current_y = self.preview_canvas.canvasy(0)
        if current_y <= y < current_y + max(1, view_h - 35):
            return  # 既に見えていればスクロール位置は動かさない。
        total_h = self.preview_area.winfo_height()
        scrollable = max(1, total_h - view_h)
        self.preview_canvas.yview_moveto(max(0, min(1, y / scrollable)))

    def _on_tab_changed(self, _event=None):
        chosen = self.edit_tabs.select()
        for name, panel in self.option_panels.items():
            if str(panel) == chosen:
                self.category_var.set(name)
                break
        # 設定ページを切り替えるたびに先頭に戻し、内容が収まるページは固定表示。
        chosen_panel = next((p for p in self.option_panels.values()
                             if str(p) == chosen), None)
        if chosen_panel is not None:
            chosen_panel.reset_view()
        # 使用頻度の低い進捗バーは、そのタブを編集するときだけ表示。
        # タブを切り替える度にほかの設定まで変えることはしない。
        visible = self.category_var.get() == '進捗バー'
        if visible != getattr(self, '_progress_preview_visible', False):
            self._progress_preview_visible = visible
            self._schedule_preview()

    def _build_color_tab(self):
        panel = ScrollPanel(self.edit_tabs)
        self.option_panels['カラー'] = panel
        self.edit_tabs.add(panel, text='カラー')
        ttk.Label(panel.inner, text='各色の役割を指定（クリックで色選択）',
                  style='Muted.TLabel').grid(row=0, column=0, sticky='ew', padx=8, pady=8)
        panel.inner.columnconfigure(0, weight=1)
        for index, (key, label) in enumerate((p for p in COLOR_FIELDS if p[0] in EDITABLE_COLOR_KEYS)):
            row = ttk.Frame(panel.inner)
            row.grid(row=index+1, column=0, sticky='ew', padx=8, pady=3)
            self.color_field_frames[key] = row
            ttk.Label(row, text=label).pack(side='left', fill='x', expand=True)
            btn = tk.Button(row, text='#FFFFFF', width=9, relief='solid', borderwidth=1,
                            command=lambda k=key: self.choose_color(k), cursor='hand2')
            btn.pack(side='right')
            self.color_buttons[key] = btn

    def _build_option_field(self, parent, key, label, spec):
        frame = ttk.Frame(parent)
        parent.columnconfigure(0, weight=1)
        frame.grid(row=len(parent.grid_slaves()), column=0, sticky='ew', padx=8, pady=(6,3))
        self.option_field_frames[key] = frame
        ttk.Label(frame, text=label).pack(anchor='w')
        if spec[0] == 'choice':
            var = tk.StringVar()
            labels = {name: value for name, value in spec[1]}
            inverse = {value: name for name, value in spec[1]}
            widget = ttk.Combobox(frame, state='readonly', values=list(labels),
                                  style='StudioEditor.TCombobox')
            widget.pack(fill='x', pady=(2,0))
            widget.bind('<<ComboboxSelected>>', lambda e, k=key, w=widget, items=labels:
                        self._option_changed(k, items.get(w.get(), '')))
            self.option_vars[key] = (var, widget, inverse)
        else:
            low, high = spec[1:]
            var = tk.StringVar()
            widget = ttk.Spinbox(frame, from_=low, to=high, increment=1, textvariable=var,
                                 style='StudioEditor.TSpinbox')
            widget.pack(fill='x', pady=(2,0))
            widget.bind('<Return>', lambda e, k=key: self._option_changed(k))
            widget.bind('<FocusOut>', lambda e, k=key: self._option_changed(k))
            var.trace_add('write', lambda *_args, k=key: self._numeric_edited(k))
            self.option_vars[key] = (var, widget, None)
        if key in ('button_shape', 'slider_shape'):
            self.custom_only_widgets[key] = widget

    def _numeric_edited(self, key):
        """Update a valid numeric value while typing, without stealing focus."""
        if self.loading:
            return
        var, _, _ = self.option_vars[key]
        raw = var.get().strip()
        if not raw.isdecimal():
            return  # empty intermediate edit: wait for further input / FocusOut
        spec = next(spec for _cat, fields in OPTION_SECTIONS for k, _l, spec in fields if k == key)
        value = int(raw)
        if not spec[1] <= value <= spec[2]:
            return
        if self.current['options'].get(key) != value:
            self.current['options'][key] = value
            self._mark_modified()
            self._schedule_preview()

    def _option_changed(self, key, value=None):
        if self.loading:
            return
        if value is None:
            var, widget, _ = self.option_vars[key]
            try:
                value = int(var.get())
            except ValueError:
                self.status_var.set('数値として入力してください。')
                self._refresh_editor_values()
                return
            spec = next(spec for _cat, fields in OPTION_SECTIONS for k, _l, spec in fields if k == key)
            value = max(spec[1], min(spec[2], value))
        if key == 'button_shape' and self.current['render_mode'] == 'standard_ttk' and value != 'standard':
            self.status_var.set('標準ttk限定では独自描画ボタンは使用できません。')
            return
        if key == 'slider_shape' and self.current['render_mode'] == 'standard_ttk' and value != 'standard':
            self.status_var.set('標準ttk限定では独自描画スライダーは使用できません。')
            return
        self.current['options'][key] = value
        if key in ('button_style','button_shape','slider_shape'):
            self.selected_shape_id = shape_preset_for(self.current['options'])
            self._schedule_gallery()
        self._mark_modified()
        self._refresh_editor_values()
        self._schedule_preview()

    def _refresh_editor_values(self):
        self.loading = True
        try:
            self.family_var.set(self.current.get('palette_family', 'カスタム'))
            self.mode_var.set(self.current.get('render_mode', 'standard_ttk'))
            mode_name = next((label for label, val in self.mode_choices if val == self.mode_var.get()), '標準ttk限定')
            self.mode_combo.set(mode_name)
            for key, button in self.color_buttons.items():
                color = self.current['colors'].get(key, '#FFFFFF')
                button.config(bg=color, activebackground=color, text=color,
                              fg='#151515' if self._luminance(color) > 0.53 else '#FFFFFF')
            for key, (var, widget, inverse) in self.option_vars.items():
                value = self.current['options'].get(key, DEFAULT_OPTIONS[key])
                if inverse is not None:
                    widget.set(inverse.get(value, list(inverse.values())[0]))
                else:
                    var.set(str(value))
            self._enable_custom_controls()
        finally:
            self.loading = False

    @staticmethod
    def _luminance(color):
        if len(color) != 7 or not color.startswith('#'):
            return 1
        vals = [int(color[i:i+2],16)/255 for i in (1,3,5)]
        return 0.2126*vals[0] + 0.7152*vals[1] + 0.0722*vals[2]

    def _enable_custom_controls(self):
        strict = self.current.get('render_mode') == 'standard_ttk'
        for key, widget in self.custom_only_widgets.items():
            try:
                widget.configure(state='disabled' if strict else ('readonly' if key in ('button_shape','slider_shape') else 'normal'))
            except tk.TclError:
                pass
        explanation = {
            'standard_ttk': '標準ttk限定：出力先でCanvas製カスタム部品を使用しません。',
            'hybrid': 'ハイブリッド：特殊な形状を選んだ部品だけ独自描画します。',
            'design': 'デザイン優先：サンプルボタンとスライダーを独自描画します。',
        }
        self.mode_label.config(text=explanation.get(self.mode_var.get(), ''))

    def _on_mode_selected(self, event=None):
        choice = dict(self.mode_choices).get(self.mode_combo.get(), 'standard_ttk')
        if choice == 'standard_ttk':
            self.current['options']['button_shape'] = 'standard'
            self.current['options']['slider_shape'] = 'standard'
        self.current['render_mode'] = choice
        self.selected_shape_id = shape_preset_for(self.current['options'])
        self._mark_modified()
        self._refresh_editor_values()
        self._schedule_gallery()
        self._schedule_preview()

    def _mark_modified(self):
        self.dirty = True
        self.status_var.set('編集中（未保存）— マイテーマに保存するか、ファイルに出力できます。')
        self._refresh_theme_summary()

    def _schedule_gallery(self):
        if self.gallery_job is not None:
            self.root.after_cancel(self.gallery_job)
        self.gallery_job = self.root.after(120, self._update_gallery)

    def _update_gallery(self):
        if self.gallery_job is not None:
            try:
                self.root.after_cancel(self.gallery_job)
            except tk.TclError:
                pass
        self.gallery_job = None
        term = self.search_var.get().strip().casefold()
        for tab_name, content in self.gallery_contents.items():
            canvas = self.gallery_canvases[tab_name]
            old_y = canvas.yview()[0] if canvas.yview() else 0.0
            for widget in content.winfo_children():
                widget.destroy()
            if tab_name == '形状':
                items = SHAPE_PRESETS
            elif tab_name == '配色':
                items = COLOR_PRESETS
            elif tab_name == 'マイテーマ':
                items = self.custom
            else:
                items = [t for t in self._all_themes() if t['id'] in self.favorites]
            items = [x for x in items if not term or term in
                     (x['name'] + ' ' + x.get('description','')).casefold()]
            if tab_name != '形状':
                items = sorted(items, key=lambda t: t['name'].casefold())
            for i, item in enumerate(items):
                if tab_name == '形状':
                    self._shape_card(content, item, i)
                else:
                    self._theme_card(content, item, i, palette_only=(tab_name == '配色'))
            if not items:
                text = ('保存したテーマはまだありません。' if tab_name == 'マイテーマ'
                        else '該当する候補がありません。')
                tk.Label(content, text=text, bg='#F0F2F6', fg='#66788B',
                         wraplength=220).grid(row=0,column=0,columnspan=2,pady=24)
            canvas.update_idletasks()
            canvas.yview_moveto(old_y)
            for child in content.winfo_children():
                self._bind_gallery_wheel(child, canvas)

    def _shape_card(self, parent, item, index=0):
        """形状プリセットのカード。配色に触らず部品の外観だけ切り替える。"""
        selected = item['id'] == self.selected_shape_id
        bg = '#DCEBFC' if selected else '#FFFFFF'
        outer = tk.Frame(parent, bg=bg, relief='solid', bd=1,
                         highlightbackground='#3580D3' if selected else '#C7D3DF',
                         highlightthickness=1, cursor='hand2')
        outer.grid(row=index//2,column=index%2,sticky='nsew',padx=3,pady=4)
        # 2列カードがWindowsのフォント/DPI差でも欠けにくいよう見本幅を抑える。
        sample = tk.Canvas(outer, width=106, height=52, bg=bg,
                           highlightthickness=0, cursor='hand2')
        sample.pack(fill='x', padx=7, pady=(3,1))
        kind = item['id']
        if kind == 'shape-raised':
            sample.create_rectangle(11,12,100,43,fill='#A1B3C9',outline='')
            sample.create_rectangle(8,8,97,39,fill='#1765C7',outline='#0B3D86',width=2)
        elif kind == 'shape-outline':
            sample.create_rectangle(8,8,97,39,fill='#FFFFFF',outline='#1765C7',width=2)
        elif kind == 'shape-rounded':
            sample.create_oval(8,8,41,39,fill='#1765C7',outline='')
            sample.create_oval(64,8,97,39,fill='#1765C7',outline='')
            sample.create_rectangle(25,8,81,39,fill='#1765C7',outline='')
        else:
            sample.create_rectangle(8,8,97,39,fill='#1765C7',outline='')
        sample.create_text(53,24,text='実行',
                           fill='#1765C7' if kind == 'shape-outline' else '#FFFFFF',
                           font=('Yu Gothic UI',10,'bold'))
        name = tk.Label(outer,text=item['name'],bg=bg,fg='#1C334D',
                        font=('Yu Gothic UI',10,'bold'),cursor='hand2')
        name.pack()
        label = tk.Label(outer,text='独自描画が必要' if item['requires_custom'] else '標準ttkで利用可',
                         bg=bg,fg='#65778A',font=('Yu Gothic UI',8),cursor='hand2')
        label.pack(pady=(1,5))
        for widget in (outer,sample,name,label):
            widget.bind('<Button-1>', lambda _event,preset=item: self.select_shape_preset(preset))

    def _theme_card(self, parent, item, index=0, *, palette_only=False):
        """縮小プレビューをクリックすると適用。テーマごとに独立したカード。"""
        selected = item['id'] == (self.selected_color_id if palette_only else self.selected_id)
        unsupported = (not palette_only and bool(item.get('requires_custom'))
                       and self.mode_var.get() == 'standard_ttk')
        bg = '#DCEBFC' if selected else '#FFFFFF'
        edge = '#3580D3' if selected else '#C7D3DF'
        outer = tk.Frame(parent, bg=bg, bd=1, relief='solid',
                         highlightbackground=edge, highlightthickness=1,
                         cursor='arrow' if unsupported else 'hand2')
        outer.grid(row=index, column=0, columnspan=2, sticky='nsew', padx=3, pady=3)
        colors = item['colors']
        thumbnail = tk.Frame(outer, bg=colors['background'], width=79, height=68,
                             cursor='arrow' if unsupported else 'hand2')
        thumbnail.pack(side='left', padx=(5, 2), pady=5)
        thumbnail.pack_propagate(False)
        block = tk.Frame(thumbnail, bg=colors['surface'])
        block.pack(fill='both', expand=True, padx=5, pady=6)
        bar = tk.Frame(block, bg=colors['surface_alt'], height=6)
        bar.pack(fill='x', padx=5, pady=(3,2))
        accent = tk.Frame(block, bg=colors['accent'], height=12)
        accent.pack(fill='x', padx=5, pady=(0,2))
        tk.Frame(block, bg=colors['selection'], height=5).pack(fill='x', padx=5, pady=(0,3))
        line = tk.Frame(outer, bg=bg)
        line.pack(side='left', fill='both', expand=True, padx=(2, 5), pady=(7,5))
        star = '★ ' if item['id'] in self.favorites else ''
        name = tk.Label(line, text=star+item['name'], bg=bg, fg='#1C334D',
                        font=('Yu Gothic UI',9,'bold'), anchor='center',
                        wraplength=148, justify='left', height=1)
        name.pack(fill='x', anchor='w')
        if palette_only:
            tag_text, tag_color = '配色のみ変更', '#637A8D'
        elif item.get('requires_custom'):
            tag_text, tag_color = '独自描画テーマ', '#637A8D'
        elif item.get('origin') == 'custom':
            tag_text, tag_color = 'マイテーマ', '#637A8D'
        else:
            tag_text, tag_color = '標準テーマ', '#637A8D'
        tag = tk.Label(line, text=tag_text, bg=bg, fg=tag_color,
                       font=('Yu Gothic UI',8), anchor='w')
        tag.pack(fill='x', anchor='w')
        detail = tk.Label(line, text=item.get('description', '')[:28],
                          bg=bg, fg='#62778E', font=('Yu Gothic UI',8),
                          anchor='w', justify='left', wraplength=150)
        detail.pack(fill='x', anchor='w')
        for widget in (outer, thumbnail, block, bar, accent, line, name, tag, detail):
            widget.bind('<Button-1>', lambda e, data=item, colors_only=palette_only: self.select_color_preset(data) if colors_only else self.select_theme(data))
        # 子をクリックしてもボタンを押さなくてよいよう、すべてに適用操作を関連付ける。
        for child in block.winfo_children():
            child.bind('<Button-1>', lambda e, data=item, colors_only=palette_only: self.select_color_preset(data) if colors_only else self.select_theme(data))

    def select_color_preset(self, data):
        """配色だけ交換。設定中の形状や文字サイズは維持する。"""
        self.current['colors'] = copy.deepcopy(data['colors'])
        self.current['palette_family'] = data.get('palette_family','カスタム')
        self.current['color_preset_id'] = data['id']
        self.selected_color_id = data['id']
        if self.current.get('origin') == 'built_in':
            self.current['name'] = data['name']
            self.current['id'] = data['id']
            self.selected_id = data['id']
        self._mark_modified()
        self._refresh_editor_values()
        self._schedule_gallery()
        self._schedule_preview()
        self.status_var.set(f'配色「{data["name"]}」を適用しました。ボタン形状は維持しています。')

    def select_shape_preset(self, preset):
        """形状だけ交換。色・フォント・マイテーマの名前は維持する。"""
        if preset['requires_custom'] and self.mode_var.get() == 'standard_ttk':
            messagebox.showinfo('標準ttk限定',
                '角丸ボタンは独自描画が必要です。ハイブリッドかデザイン優先に変更してください。',
                parent=self.root)
            return False
        self.current['options'].update(preset['values'])
        self.current['shape_preset_id'] = preset['id']
        self.selected_shape_id = preset['id']
        self._mark_modified()
        self._refresh_editor_values()
        self._schedule_gallery()
        self._schedule_preview()
        self.status_var.set(f'形状「{preset["name"]}」を適用しました。配色は維持しています。')
        return True

    def select_theme(self, data):
        if self.mode_var.get() == 'standard_ttk' and data.get('requires_custom'):
            messagebox.showinfo('非対応のテーマ',
                'このテーマは独自描画部品を使用します。\n使用するには描画方式を変更してください。',
                parent=self.root)
            return
        if self.dirty and not messagebox.askyesno('編集中の変更',
                '未保存のデザイン変更があります。破棄して別のテーマを選びますか？', parent=self.root):
            return
        mode = self.mode_var.get()
        self.current = copy.deepcopy(data)
        # ユーザーの選択した描画方式はテーマ変更で勝手に切り替えない。
        self.current['render_mode'] = mode
        if mode == 'standard_ttk':
            self.current['options']['button_shape'] = 'standard'
            self.current['options']['slider_shape'] = 'standard'
        self.selected_id = data['id']
        self.selected_color_id = self.current.get('color_preset_id', data['id'])
        self.selected_shape_id = shape_preset_for(self.current['options'])
        self.base_theme = copy.deepcopy(self.current)
        self.dirty = False
        self._refresh_editor_values()
        self._schedule_gallery()
        self._schedule_preview()
        self.status_var.set(f'テーマ「{data["name"]}」を適用しました。')

    def reset_to_selected(self):
        """配色と形状を編集する前、最後に読み込んだテーマ全体へ戻す。"""
        self.current = copy.deepcopy(self.base_theme)
        self.dirty = False
        self.selected_shape_id = shape_preset_for(self.current['options'])
        self.selected_color_id = self.current.get('color_preset_id', self.current['id'])
        self._refresh_editor_values()
        self._schedule_gallery()
        self._schedule_preview()
        self.status_var.set('最後に読み込んだテーマへ戻しました。')

    def choose_color(self, key):
        initial = self.current['colors'][key]
        selected = colorchooser.askcolor(color=initial, parent=self.root,
                                        title=f'色を選択: {dict(COLOR_FIELDS)[key]}')[1]
        if selected is None:
            return
        self.current['colors'][key] = selected.upper()
        self.current['palette_family'] = 'カスタム'
        self.selected_color_id = None
        self._mark_modified()
        self._refresh_editor_values()
        self._schedule_preview()

    def apply_palette(self):
        family = self.family_var.get()
        if family not in PALETTES:
            messagebox.showinfo('配色系統', '一覧から配色系統を選択してください。',parent=self.root)
            return
        self.current['colors'] = dict(zip((k for k, _ in COLOR_FIELDS), PALETTES[family]))
        self.current['palette_family'] = family
        self.selected_color_id = None
        self._mark_modified()
        self._refresh_editor_values()
        self._schedule_preview()

    def apply_global_shape(self, how):
        opts = self.current['options']
        if how == 'square':
            opts.update({'button_style':'outline', 'button_shape':'standard',
                         'slider_shape':'standard', 'corner_radius':0,
                         'frame_border':2, 'button_border':1})
        elif how == 'normal':
            opts.update({'button_style':'raised','button_shape':'standard',
                         'slider_shape':'standard','corner_radius':8,
                         'frame_border':1,'button_border':1})
        else:
            if self.mode_var.get() == 'standard_ttk':
                messagebox.showinfo('標準ttk限定',
                    '標準ttk限定では角丸カスタム部品を使用できません。\n'
                    '角丸を選ぶにはハイブリッドまたはデザイン優先を選択してください。',
                    parent=self.root)
                return
            opts.update({'button_style':'flat','button_shape':'pill',
                         'slider_shape':'custom','corner_radius':18,
                         'frame_border':0,'button_border':0})
        self.selected_shape_id = shape_preset_for(opts)
        self._mark_modified()
        self._refresh_editor_values()
        self._schedule_gallery()
        self._schedule_preview()

    def _schedule_preview(self):
        self._refresh_theme_summary()
        if self.preview_job is not None:
            self.root.after_cancel(self.preview_job)
        self.preview_job = self.root.after(130, self._refresh_preview)

    def _bind_preview_navigation(self, widget, section):
        """Navigate to component settings without blocking the widget's own action.

        スクロールバーはドラッグ・矢印押下時の標準動作を優先し、
        ボタンを離した後で切替える（押下中に部品を破棄しない）。
        """
        event_name = ('<ButtonRelease-1>' if isinstance(widget, ttk.Scrollbar)
                      else '<Button-1>')
        widget.bind(event_name, lambda _event, dest=section:
                    self._focus_option_section(dest), add='+')
        try:
            widget.configure(cursor='hand2')
        except tk.TclError:
            pass

    def _refresh_preview(self):
        """部品ごとの見本を編集欄と同じ順序で表示する。"""
        if self.preview_job is not None:
            try:
                self.root.after_cancel(self.preview_job)
            except tk.TclError:
                pass
        self.preview_job = None
        theme = self.current
        apply_theme(self.root, theme, style_prefix='Preview')
        ps = lambda name: 'Preview.' + name
        style = ttk.Style(self.root)
        style.configure('Preview.SampleHeader.TLabel',
                        background=theme['colors'].get('surface_alt', '#DDEAFF'),
                        foreground=theme['colors'].get('text','#17345F'),
                        font=(theme['options'].get('font_family','Yu Gothic UI'), 11, 'bold'),
                        padding=(10, 5))
        self.preview_area.configure(style=ps('TFrame'))
        self.preview_canvas.configure(bg=theme['colors'].get('background', '#F0F5FC'))
        scroll_pos = self.preview_canvas.yview()[0]
        for widget in self.preview_area.winfo_children():
            widget.destroy()
        v = theme['options']
        gap = int(v.get('control_gap', 9))
        pad = int(v.get('panel_padding', 14))
        self.preview_navigation = {}
        self.preview_sections = {}
        self.preview_samples = {}

        def register(widget, section):
            self.preview_navigation[widget] = section
            self.preview_samples.setdefault(section, []).append(widget)
            self._bind_preview_navigation(widget, section)
            return widget

        def section(name):
            header = ttk.Label(self.preview_area, text=name,
                               style='Preview.SampleHeader.TLabel')
            header.pack(fill='x', padx=(4, 4), pady=(max(6, int(v.get('section_gap', 15))), 5))
            register(header, name)
            frame = ttk.Frame(self.preview_area, style=ps('Card.TFrame'),
                              padding=max(6, min(pad, 15)))
            frame.pack(fill='x', padx=(2, 4))
            register(frame, name)
            self.preview_sections[name] = header
            return frame

        def caption(parent, text, dest):
            label = ttk.Label(parent, text=text, style=ps('Card.TLabel'))
            label.pack(anchor='w', pady=(0, 3))
            register(label, dest)
            return label

        # 右側「編集する部品」と同じ順序：カラー → 全体 → ボタン → 入力...
        colors = section('カラー')
        swatches = ttk.Frame(colors, style=ps('Card.TFrame'))
        swatches.pack(fill='x')
        register(swatches, 'カラー')
        for label, role in (('BG', 'background'), ('Panel', 'surface_alt'),
                            ('Accent', 'accent'), ('Select', 'selection')):
            tile = tk.Label(swatches, text=label, bg=theme['colors'].get(role, '#FFFFFF'),
                            fg=theme['colors']['text'] if role != 'accent'
                            else theme['colors'].get('accent_text', '#FFFFFF'),
                            font=(v.get('font_family', 'Yu Gothic UI'), 9),
                            padx=8, pady=5, cursor='hand2')
            tile.pack(side='left', fill='x', expand=True, padx=2)
            register(tile, 'カラー')

        layout = section('全体・レイアウト')
        caption(layout, 'Frame 1', '全体・レイアウト')
        panel = ttk.Frame(layout, style=ps('Alt.TFrame'), padding=(pad, max(4, pad // 2)))
        panel.pack(fill='x')
        register(panel, '全体・レイアウト')
        register(ttk.Label(panel, text='Panel 1', style=ps('TLabel')), '全体・レイアウト').pack(anchor='w')

        buttons = section('ボタン')
        row = ttk.Frame(buttons, style=ps('Card.TFrame'))
        row.pack(fill='x')
        register(row, 'ボタン')
        primary = make_action_button(row, 'Button 1',
                         lambda: self.status_var.set('Button 1 をクリックしました。'),
                         theme, ttk_style=ps('Primary.TButton'))
        primary.pack(side='left', padx=(0, 7))
        register(primary, 'ボタン')
        regular = ttk.Button(row, text='Button 2', style=ps('TButton'))
        regular.pack(side='left')
        register(regular, 'ボタン')

        inputs = section('入力・選択')
        caption(inputs, 'Entry 1', '入力・選択')
        entry = ttk.Entry(inputs, style=ps('TEntry'))
        entry.insert(0, 'Text 1')
        entry.pack(fill='x', pady=(0, gap))
        register(entry, '入力・選択')
        caption(inputs, 'Select 1', '入力・選択')
        combo = ttk.Combobox(inputs, state='readonly', style=ps('TCombobox'),
                             values=['Select 1', 'Select 2', 'Select 3'])
        combo.set('Select 1')
        combo.pack(fill='x')
        register(combo, '入力・選択')

        choices = section('チェック・ラジオ')
        self.preview_check_var = tk.BooleanVar(value=True)
        check = ttk.Checkbutton(choices, text='Check 1', variable=self.preview_check_var,
                                style=ps('Card.TCheckbutton'))
        check.pack(anchor='w')
        register(check, 'チェック・ラジオ')
        radio_group = ttk.Frame(choices, style=ps('Card.TFrame'))
        radio_group.pack(anchor='w', pady=(3, 0))
        register(radio_group, 'チェック・ラジオ')
        radio_value = tk.StringVar(value='r1')
        for i in (1, 2):
            radio = ttk.Radiobutton(radio_group, text=f'Radio {i}', value=f'r{i}',
                                    variable=radio_value, style=ps('Card.TRadiobutton'))
            radio.pack(side='left', padx=(0, 9))
            register(radio, 'チェック・ラジオ')

        sliders = section('スライダー')
        caption(sliders, 'Slider 1', 'スライダー')
        self.slider_val = tk.DoubleVar(value=53)
        scale = make_value_slider(sliders, self.slider_val, theme, ttk_style=ps('TScale'))
        scale.pack(fill='x')
        register(scale, 'スライダー')

        scrollers = section('スクロールバー')
        caption(scrollers, 'Scroll 1  （5行表示）', 'スクロールバー')
        tree_frame = ttk.Frame(scrollers, style=ps('Card.TFrame'))
        tree_frame.pack(fill='x')
        register(tree_frame, 'スクロールバー')
        scroll_tree = ttk.Treeview(tree_frame, columns=('sample',), show='headings',
                                   height=5, style=ps('Treeview'))
        scroll_tree.heading('sample', text='Item')
        scroll_tree.column('sample', width=150, stretch=True)
        for i in range(1, 17):
            scroll_tree.insert('', 'end', values=(f'Item {i}',))
        scroll_tree.pack(side='left', fill='both', expand=True)
        register(scroll_tree, 'スクロールバー')
        list_scroll = ttk.Scrollbar(tree_frame, orient='vertical',
                                    command=scroll_tree.yview,
                                    style=ps('Vertical.TScrollbar'))
        list_scroll.pack(side='right', fill='y')
        scroll_tree.configure(yscrollcommand=list_scroll.set)
        register(list_scroll, 'スクロールバー')
        self.preview_scrollbar_sample = list_scroll
        self.preview_scrollbar_tree = scroll_tree

        if self.category_var.get() == '進捗バー':
            progress_section = section('進捗バー')
            caption(progress_section, 'Progress 1', '進捗バー')
            progress = ttk.Progressbar(progress_section, mode='determinate', value=63,
                                        style=ps('Horizontal.TProgressbar'))
            progress.pack(fill='x')
            register(progress, '進捗バー')

        texts = section('文字')
        caption(texts, 'Text 1', '文字')
        register(ttk.Label(texts, text='Body 1', style=ps('Card.TLabel')), '文字').pack(anchor='w')
        register(ttk.Label(texts, text='Title 1', style=ps('Title.TLabel')), '文字').pack(anchor='w')

        lists = section('一覧・タブ')
        caption(lists, 'List 1 / Tab 1', '一覧・タブ')
        tabs = ttk.Notebook(lists, style=ps('TNotebook'))
        tabs.pack(fill='x')
        register(tabs, '一覧・タブ')
        tab_1 = ttk.Frame(tabs, style=ps('Card.TFrame'))
        tab_2 = ttk.Frame(tabs, style=ps('Card.TFrame'))
        tabs.add(tab_1, text='Tab 1')
        tabs.add(tab_2, text='Tab 2')
        register(tab_1, '一覧・タブ')
        register(tab_2, '一覧・タブ')
        list_example = ttk.Treeview(tab_1, columns=('name',), show='headings',
                                    height=2, style=ps('Treeview'))
        list_example.heading('name', text='Name')
        for i in range(1, 3):
            list_example.insert('', 'end', values=(f'Row {i}',))
        list_example.pack(fill='x')
        register(list_example, '一覧・タブ')
        register(ttk.Label(tab_2, text='Tab content 2',
                           style=ps('Card.TLabel')), '一覧・タブ').pack(anchor='w', padx=5, pady=5)

        # 見本を作り終えてから、入れ子のCanvasボタン・選択欄にも登録。
        # 再描画時は古い見本をdestroy()するためバインドが蓄積しない。
        self._bind_preview_wheel(self.preview_area)
        self.preview_canvas.update_idletasks()
        self._preview_content_resized()
        self.preview_canvas.yview_moveto(scroll_pos)
        self.preview_notice.set('部品の見本をクリックすると右の設定に移動します。')

    def _build_export_data(self):
        d = normalized_theme(self.current)
        d['origin'] = 'exported'
        d['color_preset_id'] = self.selected_color_id or 'custom'
        d['shape_preset_id'] = self.selected_shape_id or 'custom'
        d['requires_custom'] = bool(
            d['render_mode'] == 'design' or
            (d['render_mode'] != 'standard_ttk' and
             (d['options']['button_shape'] == 'pill' or d['options']['slider_shape'] == 'custom')))
        if d['render_mode'] == 'standard_ttk':
            d['options']['button_shape'] = 'standard'
            d['options']['slider_shape'] = 'standard'
            d['requires_custom'] = False
        validate_theme(d)
        return d

    def _export_python_text(self, data):
        source = (Path(__file__).resolve().parent/'theme_runtime.py').read_text(encoding='utf-8')
        return ('# GUI Design Studio で出力した再利用可能なテーマモジュール。\n'
                '# Python標準ライブラリのみで利用できます。\n'
                '# 適用: from design_theme import apply_theme; apply_theme(root)\n'
                'THEME = ' + pprint.pformat(data, width=110, sort_dicts=False) + '\n\n'
                + source)

    def export_theme(self):
        filename = filedialog.asksaveasfilename(parent=self.root, title='テーマを出力',
            initialfile='design_theme.json', defaultextension='.json',
            filetypes=[('テーマ設定（JSON）','*.json')])
        if not filename:
            return
        json_path = Path(filename)
        py_path = json_path.with_suffix('.py')
        if py_path.exists() and not messagebox.askyesno('既存ファイル',
                        f'{py_path.name} は既にあります。上書きしますか？',parent=self.root):
            return
        try:
            data = self._build_export_data()
            python_text = self._export_python_text(data)
            compile(python_text, str(py_path), 'exec')
            save_json(json_path, data)
            py_path.write_text(python_text, encoding='utf-8')
        except (OSError, ValueError, SyntaxError) as exc:
            messagebox.showerror('出力に失敗', str(exc),parent=self.root)
            return
        self.status_var.set(f'出力完了: {json_path.name} / {py_path.name}')
        messagebox.showinfo('出力完了', f'以下の2ファイルを出力しました。\n{json_path}\n{py_path}',
                            parent=self.root)

    def save_as_custom(self):
        name = simpledialog.askstring('マイテーマに保存', '新しいテーマ名を入力してください。',
                      initialvalue=self.current['name']+' カスタム', parent=self.root)
        if name is None:
            return
        if not name.strip() or len(name.strip()) > 80:
            messagebox.showwarning('テーマ名', '1～80文字のテーマ名を指定してください。',parent=self.root)
            return
        custom = new_custom_theme(self._build_export_data(), name)
        custom['origin'] = 'custom'
        try:
            save_json(self.theme_dir/(custom['id']+'.json'), custom)
        except OSError as exc:
            messagebox.showerror('保存できません', str(exc),parent=self.root)
            return
        self.custom.append(custom)
        self.gallery_tabs.select(self.gallery_pages['マイテーマ'])
        self.current = copy.deepcopy(custom)
        self.selected_id = custom['id']
        self.base_theme = copy.deepcopy(custom)
        self.dirty = False
        self._refresh_editor_values()
        self._schedule_gallery()
        self._schedule_preview()
        self.status_var.set(f'「{name}」をマイテーマに保存しました。')

    def overwrite_custom(self):
        if self.current.get('origin') != 'custom' or self.selected_id not in [x['id'] for x in self.custom]:
            messagebox.showinfo('上書き保存', '標準テーマは上書きできません。\n「マイテーマに保存」を使用してください。',
                                parent=self.root)
            return
        candidate = self._build_export_data()
        candidate['origin'] = 'custom'
        candidate['id'] = self.selected_id
        try:
            save_json(self.theme_dir/(candidate['id']+'.json'), candidate)
        except OSError as exc:
            messagebox.showerror('上書き保存できません', str(exc), parent=self.root)
            return
        self.custom = [candidate if x['id'] == candidate['id'] else x for x in self.custom]
        self.current = copy.deepcopy(candidate)
        self.base_theme = copy.deepcopy(candidate)
        self.dirty = False
        self._schedule_gallery()
        self.status_var.set('マイテーマを上書き保存しました。')

    def delete_custom(self):
        theme_id = self.selected_id
        target = self._theme_by_id(theme_id)
        if target is None or target.get('origin') != 'custom':
            messagebox.showinfo('テーマ削除', '削除できるのはマイテーマのみです。',parent=self.root)
            return
        if not messagebox.askyesno('削除の確認', f'「{target["name"]}」を削除しますか？',parent=self.root):
            return
        try:
            (self.theme_dir/(theme_id+'.json')).unlink()
        except OSError as exc:
            messagebox.showerror('削除できません', str(exc),parent=self.root)
            return
        self.custom = [x for x in self.custom if x['id'] != theme_id]
        self.favorites.discard(theme_id)
        self._save_preferences()
        self.dirty = False
        self.selected_id = BUILTINS[0]['id']
        self.current = copy.deepcopy(BUILTINS[0])
        self.base_theme = copy.deepcopy(self.current)
        self.selected_color_id = self.current['id']
        self.selected_shape_id = shape_preset_for(self.current['options'])
        self.current['render_mode'] = self.mode_var.get()
        self._refresh_editor_values()
        self._schedule_gallery()
        self._schedule_preview()
        self.status_var.set('マイテーマを削除しました。')

    def toggle_favorite(self):
        theme_id = self.selected_id
        if theme_id in self.favorites:
            self.favorites.remove(theme_id)
            message = 'お気に入りを解除しました。'
        else:
            self.favorites.add(theme_id)
            message = 'お気に入りに登録しました。'
        try:
            self._save_preferences()
        except OSError as exc:
            messagebox.showerror('保存失敗',str(exc),parent=self.root)
            return
        self._schedule_gallery()
        self.status_var.set(message)

    def import_theme(self):
        filename = filedialog.askopenfilename(parent=self.root, title='JSONテーマを読み込む',
                                              filetypes=[('テーマ設定（JSON）','*.json')])
        if not filename:
            return
        try:
            data = json.loads(Path(filename).read_text(encoding='utf-8'))
            loaded = normalized_theme(data)
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror('読み込めません',str(exc),parent=self.root)
            return
        if self.mode_var.get() == 'standard_ttk' and (loaded.get('requires_custom') or
                 loaded['options'].get('button_shape')=='pill' or loaded['options'].get('slider_shape')=='custom'):
            messagebox.showwarning('描画方式の確認',
                  'このテーマには独自描画部品が含まれます。\n描画方式を変更してから読み込んでください。',parent=self.root)
            return
        if self.dirty and not messagebox.askyesno('編集中の変更',
                     '未保存の変更を破棄して読み込みますか？',parent=self.root):
            return
        # 読み込み時は自作テーマとして未保存の状態で扱う。自動的に既存ファイルを上書きしない。
        loaded['origin'] = 'imported'
        loaded['id'] = 'imported-unsaved'
        loaded['render_mode'] = self.mode_var.get()
        self.current = loaded
        self.selected_id = loaded['id']
        self.selected_color_id = loaded.get('color_preset_id')
        self.selected_shape_id = shape_preset_for(loaded['options'])
        self.dirty = True
        self._refresh_editor_values()
        self._schedule_gallery()
        self._schedule_preview()
        self.status_var.set('JSONテーマを読み込みました。マイテーマとして保存できます。')

    def show_about(self):
        messagebox.showinfo('GUI Design Studio',
            'GUI Design Studio v1.00\n'
            'Python標準ライブラリだけで動くGUIテーマ作成ツールです。\n\n'
            '標準ttk限定ではカスタムCanvas部品を出力しません。\n'
            'OSのテーマによって一部の外観に差が生じます。\n\n'
            f'マイテーマ保存先:\n{self.theme_dir}', parent=self.root)

    def _on_destroy(self, event):
        if event.widget is not self.root:
            return
        for name in ('preview_job', 'gallery_job'):
            job = getattr(self, name, None)
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self, name, None)

    def _close(self):
        if self.dirty and not messagebox.askyesno('未保存の変更',
            '保存していないデザイン変更があります。終了しますか？',parent=self.root):
            return
        self.root.destroy()


def main():
    root = tk.Tk()
    DesignStudio(root)
    root.mainloop()


if __name__ == '__main__':
    main()
