"""GUI Design Studio で使うテーマ適用ランタイム（Python標準ライブラリのみ）。

スタイルを適用するアプリは ttk ウィジェットに style="Primary.TButton" 等を指定できます。
標準ttk限定モードでは Canvas ベースの部品は生成しません。
"""
import tkinter as tk
import hashlib
import copy
from tkinter import ttk


def resolve_theme(theme=None):
    if theme is not None:
        return theme
    return globals().get('THEME', {})


def _get(theme, key, default):
    return theme.get(key, default)


def _install_check_indicator(root, style, style_name, shape, foreground,
                             background, border, size=16):
    """Set a small tick or X through a ttk image element (not a Canvas widget)."""
    holder = root._root()
    cache = getattr(holder, '_gui_studio_indicator_cache', None)
    if cache is None:
        cache = {}
        holder._gui_studio_indicator_cache = cache
    size = max(12, min(24, int(size)))
    key = (shape, foreground, background, border, size)
    if key not in cache:
        digest = hashlib.sha256(repr(key).encode('utf-8')).hexdigest()[:14]
        element = 'GDSCheck' + digest + '.indicator'
        images = []
        for selected in (False, True):
            im = tk.PhotoImage(master=holder, width=size, height=size)
            im.put(background, to=(0, 0, size, size))
            im.put(border, to=(1, 1, size-1, size-1))
            im.put(background, to=(2, 2, size-2, size-2))
            if selected:
                pixels = set()
                if shape == 'cross':
                    for i in range(4, 12):
                        for d in (-1, 0, 1):
                            pixels.update(((i, i+d), (15-i, i+d)))
                else:
                    for i in range(3, 8):
                        for d in (-1, 0, 1):
                            pixels.add((i, i+3+d))
                    for i in range(7, 13):
                        for d in (-1, 0, 1):
                            pixels.add((i, 17-i+d))
                for x, y in pixels:
                    tx = round(x * size / 16)
                    ty = round(y * size / 16)
                    thickness = max(1, size // 16)
                    if 2 <= tx < size-2 and 2 <= ty < size-2:
                        im.put(foreground, to=(tx, ty, min(size-2, tx+thickness), min(size-2, ty+thickness)))
            images.append(im)
        if element not in style.element_names():
            style.element_create(element, 'image', images[0], ('selected', images[1]))
        cache[key] = element, images  # Keep PhotoImage refs alive.
    element = cache[key][0]

    def swap_indicators(layout):
        out = []
        for name, opts in layout:
            info = dict(opts or {})
            if 'children' in info:
                info['children'] = swap_indicators(info['children'])
            if name.endswith('.indicator'):
                name = element
            out.append((name, info))
        return out
    style.layout(style_name, swap_indicators(style.layout('TCheckbutton')))



def _install_flat_scrollbar_thumb(root, style, thumb_color, active_color, style_prefix=''):
    """ttkの画像要素だけで横線のないつまみを作る（Canvas部品は不要）。

    Windows/OSのテーマは標準要素の見た目が異なるため、フラット表示は
    ttk.Style.layoutでthumb要素だけを差し替える。既存のスクロール操作は維持する。
    """
    holder = root._root()
    cache = getattr(holder, '_gds_flat_scrollbar_images', None)
    if cache is None:
        cache = {}
        holder._gds_flat_scrollbar_images = cache
    key = (thumb_color, active_color)
    if key not in cache:
        digest = hashlib.sha256(repr(key).encode('utf-8')).hexdigest()[:14]
        # ttk.Scrollbar は要素名の末尾「.thumb」を手掛かりに、
        # 表示割合からつまみの長さ・移動可能範囲を計算する。
        # この接尾辞がないと画像がレール全体に伸びてスクロールできなくなる。
        element = f'GDSFlatThumb{digest}.thumb'
        normal = tk.PhotoImage(master=holder, width=14, height=26)
        normal.put(thumb_color, to=(0, 0, 14, 26))
        active = tk.PhotoImage(master=holder, width=14, height=26)
        active.put(active_color, to=(0, 0, 14, 26))
        if element not in style.element_names():
            style.element_create(element, 'image', normal, ('active', active),
                                 border=(2, 2, 2, 2), sticky='nswe')
        cache[key] = (element, normal, active)
    thumb_element = cache[key][0]

    native = getattr(holder, '_gds_native_scroll_layouts', None)
    if native is None:
        native = {name: copy.deepcopy(style.layout(name)) for name in
                  ('Vertical.TScrollbar', 'Horizontal.TScrollbar')}
        holder._gds_native_scroll_layouts = native

    def replace_thumb(layout):
        result = []
        for name, options in layout:
            options = dict(options or {})
            if 'children' in options:
                options['children'] = replace_thumb(options['children'])
            if name.endswith('.thumb'):
                name = thumb_element
            result.append((name, options))
        return result

    for direction in ('Vertical', 'Horizontal'):
        base_style = f'{direction}.TScrollbar'
        names = [f'{style_prefix}.{base_style}' if style_prefix else base_style]
        if style_prefix:
            # ttk.Scrollbar may prepend the orientation to an explicit style name.
            names.append(f'{direction}.{style_prefix}.{base_style}')
        for name in names:
            style.layout(name, replace_thumb(native[base_style]))


def _restore_scrollbar_layout(root, style, style_prefix=''):
    """フラットから標準を選択した場合に、OS/Tkの元の要素へ戻す。"""
    holder = root._root()
    native = getattr(holder, '_gds_native_scroll_layouts', None)
    if native is None:
        native = {name: copy.deepcopy(style.layout(name)) for name in
                  ('Vertical.TScrollbar', 'Horizontal.TScrollbar')}
        holder._gds_native_scroll_layouts = native
    for direction in ('Vertical', 'Horizontal'):
        base_style = f'{direction}.TScrollbar'
        names = [f'{style_prefix}.{base_style}' if style_prefix else base_style]
        if style_prefix:
            names.append(f'{direction}.{style_prefix}.{base_style}')
        for name in names:
            style.layout(name, copy.deepcopy(native[base_style]))


def apply_theme(root, theme=None, *, style_prefix=""):
    """既存のTk/ttkアプリにテーマを適用し、ttk.Styleを返す。"""
    t = resolve_theme(theme)
    colors = t.get('colors', {})
    opts = t.get('options', {})
    c = lambda name, default: colors.get(name, default)
    v = lambda name, default: opts.get(name, default)
    density = v('density', 'normal')
    scale = {'compact': 0.75, 'normal': 1.0, 'spacious': 1.35}.get(density, 1.0)
    pad = lambda x: max(1, round(x * scale))
    font_family = v('font_family', 'Yu Gothic UI')
    font_size = int(v('font_size', 10))
    font = (font_family, font_size, v('font_weight', 'normal'))
    title_font = (font_family, int(v('title_size', 17)), v('title_weight', 'bold'))
    section_font = (font_family, int(v('section_size', 11)), v('section_weight', 'bold'))
    bg = c('background', '#F2F6FB')
    surface = c('surface', '#FFFFFF')
    surface_alt = c('surface_alt', '#E7EEF8')
    text = c('text', '#23344B')
    muted = c('muted', '#62758A')
    border = c('border', '#B9CADD')
    accent = c('accent', '#1765C7')
    hover = c('accent_hover', '#12519D')
    accent_text = c('accent_text', '#FFFFFF')
    field_bg = c('field_background', '#FFFFFF')
    select = c('selection', '#CDE1FF')
    success = c('success', '#387958')
    warning = c('warning', '#B47928')
    danger = c('danger', '#B84B50')
    # Editor/preview use a namespace so live preview never repaints the studio UI.
    # Exported standalone themes still use their normal ttk style names.
    if not style_prefix:
        root.configure(bg=bg)
    style = ttk.Style(root)
    if not style_prefix and 'clam' in style.theme_names():
        style.theme_use('clam')
    sn = lambda name: f'{style_prefix}.{name}' if style_prefix else name
    # 'OS標準' に戻せるよう、独自画像要素の適用前に元のレイアウトを保持する。
    holder = root._root()
    if not hasattr(holder, '_gds_native_check_layout'):
        holder._gds_native_check_layout = copy.deepcopy(style.layout('TCheckbutton'))
    frame_border = int(v('frame_border', 0))
    button_border = int(v('button_border', 1))
    input_border = int(v('input_border', 1))
    button_x = pad(int(v('button_padding_x', 14)))
    button_y = pad(int(v('button_padding_y', 8)))
    input_x = pad(int(v('input_padding_x', 8)))
    input_y = pad(int(v('input_padding_y', 6)))
    row_height = pad(int(v('row_height', 27)))
    button_style = v('button_style', 'raised')
    button_font = (font_family, font_size, v('button_text_weight', 'normal'))
    label_padding = (pad(int(v('label_padding_x', 0))), pad(int(v('label_padding_y', 0))))
    relief = {'flat': 'flat', 'raised': 'raised', 'outline': 'solid'}.get(button_style, 'raised')

    style.configure(sn('TFrame'), background=bg)
    style.configure(sn('App.TFrame'), background=bg)
    style.configure(sn('Card.TFrame'), background=surface, borderwidth=frame_border,
                    relief=v('frame_relief','solid') if frame_border else 'flat',
                    bordercolor=c(v('frame_color_role','border'),border))
    style.configure(sn('Alt.TFrame'), background=surface_alt)
    style.configure(sn('TLabel'), background=bg, foreground=text, font=font, padding=label_padding)
    style.configure(sn('Card.TLabel'), background=surface, foreground=text, font=font, padding=label_padding)
    style.configure(sn('Muted.TLabel'), background=bg, foreground=muted,
                    font=(font_family, int(v('muted_font_size',font_size)), v('font_weight','normal')),
                    padding=label_padding)
    style.configure(sn('Title.TLabel'), background=bg, foreground=c(v('title_color_role','text'),text),
                    font=title_font, padding=label_padding)
    style.configure(sn('Section.TLabel'), background=bg, foreground=c(v('section_color_role','text'),text),
                    font=section_font, padding=label_padding)
    style.configure(sn('Status.TLabel'), background=surface_alt, foreground=muted,
                    font=(font_family, int(v('status_font_size',font_size)), 'normal'),
                    padding=label_padding)
    style.configure(sn('Good.TLabel'), background=bg, foreground=success, font=font)
    style.configure(sn('Warning.TLabel'), background=bg, foreground=warning, font=font)

    style.configure(sn('TLabelframe'), background=bg, foreground=text,
                    bordercolor=c(v('frame_color_role','border'),border),
                    borderwidth=max(1, frame_border), relief=v('frame_relief','solid'),
                    padding=pad(int(v('group_padding', 10))))
    style.configure(sn('TLabelframe.Label'), background=bg, foreground=text, font=section_font)
    style.configure(sn('Card.TLabelframe'), background=surface, foreground=text,
                    bordercolor=c(v('frame_color_role','border'),border),
                    borderwidth=max(1, frame_border), relief=v('frame_relief','solid'),
                    padding=pad(int(v('group_padding', 10))))
    style.configure(sn('Card.TLabelframe.Label'), background=surface, foreground=text, font=section_font)

    style.configure(sn('TButton'), background=surface_alt, foreground=text, font=button_font,
                    padding=(button_x, button_y), relief=relief,
                    borderwidth=button_border, bordercolor=border)
    style.map(sn('TButton'), background=[('disabled', c(v('button_disabled_role','border'),border)),
                                      ('pressed', c(v('button_pressed_role','accent_hover'),hover)),
                                      ('active', c(v('button_hover_role','accent_hover'),hover))],
              foreground=[('disabled', muted), ('active', text)],
              relief=[('pressed', 'sunken')])
    style.configure(sn('Primary.TButton'), background=accent, foreground=accent_text, font=button_font,
                    padding=(button_x, button_y), relief=relief,
                    borderwidth=button_border, bordercolor=accent)
    style.map(sn('Primary.TButton'), background=[('disabled', c(v('button_disabled_role','border'),border)),
                                              ('pressed', c(v('button_pressed_role','accent_hover'),hover)),
                                              ('active', c(v('button_hover_role','accent_hover'),hover))],
              foreground=[('disabled', muted), ('active', accent_text)])
    style.configure(sn('Secondary.TButton'), background=surface, foreground=accent, font=button_font,
                    padding=(button_x, button_y), relief=relief,
                    borderwidth=max(1, button_border), bordercolor=accent)
    style.map(sn('Secondary.TButton'), background=[('active', c(v('button_hover_role','accent_hover'),hover)),
                                                    ('pressed', c(v('button_pressed_role','accent_hover'),hover))])
    style.configure(sn('Danger.TButton'), background=danger, foreground='#FFFFFF', font=button_font,
                    padding=(button_x, button_y), relief=relief, borderwidth=button_border)
    style.map(sn('Danger.TButton'), background=[('active', danger), ('pressed', danger)])

    input_font = (font_family, font_size, v('input_text_weight','normal'))
    style.configure(sn('TEntry'), font=input_font, foreground=text, fieldbackground=field_bg,
                    selectbackground=c(v('input_selection_role','selection'), select),
                    padding=(input_x, input_y), borderwidth=input_border, bordercolor=border,
                    insertcolor=text)
    style.map(sn('TEntry'), bordercolor=[('focus', c(v('input_focus_role','accent'), accent))],
              fieldbackground=[('disabled', c(v('input_disabled_bg_role','surface_alt'), surface_alt))])
    style.configure(sn('TCombobox'), font=input_font, foreground=text, fieldbackground=field_bg,
                    background=surface_alt, selectbackground=c(v('input_selection_role','selection'),select),
                    selectforeground=text, arrowsize=int(v('input_arrow_size',13)),
                    padding=(input_x, input_y), borderwidth=input_border,
                    bordercolor=border)
    # clamのreadonly状態でOSのデフォルト背景に戻り、文字が読めなくなるのを防ぐ。
    style.map(sn('TCombobox'), bordercolor=[('focus', accent)],
              fieldbackground=[('disabled', c(v('input_disabled_bg_role','surface_alt'), surface_alt)),
                               ('readonly', c(v('input_readonly_bg_role','field_background'),field_bg))],
              foreground=[('disabled', muted), ('readonly', text)],
              selectforeground=[('readonly', text)],
              selectbackground=[('readonly', c(v('input_readonly_bg_role','field_background'),field_bg))])
    style.configure(sn('TSpinbox'), font=input_font, foreground=text, fieldbackground=field_bg,
                    padding=(input_x, input_y), borderwidth=input_border)
    # チェック・ラジオはttk標準部品のまま文字色・太さ・余白を調整。
    # indicatorcolorはclamで対応する範囲のみ反映され、OSごとの差はあり得る。
    choice_fg = accent if v('choice_label_color', 'text') == 'accent' else text
    choice_weight = v('choice_font_weight', 'normal')
    choice_font = (font_family, int(v('choice_font_size', font_size)), choice_weight)
    choice_pad = (pad(int(v('choice_padding_x', 3))),
                  pad(int(v('choice_padding_y', 4))))
    indicator_map = ([('selected', accent)] if v('choice_indicator_color','default') == 'accent'
                     else [])
    for name, parent_bg in (('TCheckbutton', bg), ('TRadiobutton', bg),
                            ('Card.TCheckbutton', surface), ('Card.TRadiobutton', surface)):
        style.configure(sn(name), background=parent_bg, foreground=choice_fg,
                        font=choice_font, padding=choice_pad)
        style.map(sn(name), background=[('active', c(v('choice_active_bg_role','surface'), surface))],
                  foreground=[('disabled', c(v('choice_disabled_color_role','muted'), muted))],
                  indicatorcolor=indicator_map)
    style.configure(sn('TScale'), background=bg,
                    troughcolor=c(v('slider_track_color_role', 'surface_alt'), surface_alt),
                    bordercolor=border, borderwidth=int(v('slider_trough_border',1)),
                    slidercolor=c(v('slider_thumb_color_role','surface'), surface),
                    sliderlength=int(v('slider_thumb_size', 16)),
                    sliderthickness=int(v('slider_thumb_size', 16)))
    style.map(sn('TScale'), background=[('active', c(v('slider_active_role','accent'),accent))])
    style.configure(sn('Horizontal.TProgressbar'), background=c(v('progress_color_role','accent'), accent),
                    troughcolor=c(v('progress_trough_role','surface_alt'),surface_alt),
                    bordercolor=border, borderwidth=int(v('progress_border',1)),
                    thickness=int(v('progress_height', 13)))
    for name in ('Vertical.TScrollbar','Horizontal.TScrollbar'):
        style.configure(sn(name), background=c(v('scrollbar_thumb_role','surface_alt'),surface_alt),
                        troughcolor=c(v('scrollbar_trough_role','background'),bg),
                        arrowcolor=c(v('scrollbar_arrow_role','text'),text),
                        bordercolor=border, borderwidth=int(v('scrollbar_border',1)),
                        relief=v('scrollbar_relief','flat'), width=int(v('scrollbar_width', 14)))
        style.map(sn(name), background=[('active', c(v('scrollbar_active_role','selection'),select))])
    style.configure(sn('Treeview'), background=surface, fieldbackground=surface,
                    foreground=text, font=font, rowheight=row_height,
                    bordercolor=border, borderwidth=int(v('tree_border',1)))
    style.map(sn('Treeview'), background=[('selected', c(v('tree_selected_bg_role','selection'),select))],
              foreground=[('selected', c(v('tree_selection_text_role','text'), text))])
    style.configure(sn('Treeview.Heading'), background=surface_alt, foreground=text,
                    font=(font_family, int(v('section_size',11)), v('tree_heading_weight','bold')),
                    padding=(pad(int(v('tree_heading_padding_x',7))), pad(int(v('tree_heading_padding_y',5)))),
                    bordercolor=border)
    style.map(sn('Treeview.Heading'), background=[('active', select)])
    style.configure(sn('TNotebook'), background=bg, bordercolor=border,
                    borderwidth=int(v('notebook_border',1)))
    style.configure(sn('TNotebook.Tab'), background=surface_alt, foreground=text,
                    font=(font_family,font_size,v('tab_weight','normal')),
                    padding=(pad(int(v('tab_padding_x', 13))),
                                       pad(int(v('tab_padding_y', 7)))))
    style.map(sn('TNotebook.Tab'), background=[('selected', c(v('tab_selected_bg_role','surface'),surface)),
                                                     ('active', c(v('tab_active_role','selection'),select))],
              foreground=[('selected', c(v('tab_selected_text_role','accent'),accent))])

    # ttk.Scale / Progressbar / Scrollbar prepend their orientation internally
    # when given a custom style. Give those resolved names real layouts.
    if style_prefix:
        for custom, original, base_style in (
            ('Horizontal.' + sn('TScale'), 'Horizontal.TScale', sn('TScale')),
            ('Vertical.' + sn('TScale'), 'Vertical.TScale', sn('TScale')),
            ('Horizontal.' + sn('TProgressbar'), 'Horizontal.TProgressbar', sn('Horizontal.TProgressbar')),
            ('Vertical.' + sn('TScrollbar'), 'Vertical.TScrollbar', sn('Vertical.TScrollbar')),
            ('Horizontal.' + sn('TScrollbar'), 'Horizontal.TScrollbar', sn('Horizontal.TScrollbar')),
        ):
            style.layout(custom, style.layout(original))
            style.configure(custom, **style.configure(base_style))
            style.map(custom, **style.map(base_style))

    # フラット表示はttkのthumb画像要素を使用し、リストのスクロール機能は標準のまま。
    # 画像は同じTkルート内でキャッシュするため、プレビュー更新ごとに複製しない。
    if v('scrollbar_appearance', 'flat') == 'flat':
        _install_flat_scrollbar_thumb(root, style,
            c(v('scrollbar_thumb_role','surface_alt'), surface_alt),
            c(v('scrollbar_active_role','selection'), select), style_prefix)
    else:
        _restore_scrollbar_layout(root, style, style_prefix)

    # Standard ttk.Checkbutton with a selectable symbol. Only the small indicator
    # is supplied as a cached PhotoImage element; no Canvas widget is created.
    indicator_shape = v('choice_indicator_shape', 'check')
    if indicator_shape in ('check', 'cross'):
        for target, back in (('TCheckbutton', bg), ('Card.TCheckbutton', surface)):
            indicator_color = accent if v('choice_indicator_color', 'default') == 'accent' else text
            _install_check_indicator(root, style, sn(target), indicator_shape,
                                     indicator_color, back, border, v('choice_indicator_size',16))
    else:
        # 既に適用した画像要素から切替えても、本来のOS/Tkテーマ要素へ復元する。
        for target in ('TCheckbutton', 'Card.TCheckbutton'):
            style.layout(sn(target), copy.deepcopy(holder._gds_native_check_layout))

    # スタジオ自体の操作UI。濃色テーマでも編集用のプルダウン文字を常に読めるようにする。
    # プレビューの通常TComboboxには手を加えず、テーマの見た目を確認できるようにする。
    if style_prefix:
        return style
    editor_fg = '#20354E'
    editor_bg = '#FFFFFF'
    editor_border = '#8DAAC8'
    style.configure(sn('StudioEditor.TCombobox'), foreground=editor_fg,
                    fieldbackground=editor_bg, background='#E5EEF8',
                    selectforeground=editor_fg, selectbackground=editor_bg,
                    arrowcolor=editor_fg, bordercolor=editor_border)
    style.map(sn('StudioEditor.TCombobox'),
              foreground=[('disabled', '#6B7785'), ('readonly', editor_fg)],
              fieldbackground=[('disabled', '#F0F2F5'), ('readonly', editor_bg)],
              background=[('readonly', '#E5EEF8')],
              selectforeground=[('readonly', editor_fg)],
              selectbackground=[('readonly', editor_bg)])
    style.configure(sn('StudioEditor.TSpinbox'), foreground=editor_fg,
                    fieldbackground=editor_bg, background='#E5EEF8',
                    bordercolor=editor_border)
    style.map(sn('StudioEditor.TSpinbox'),
              foreground=[('disabled', '#6B7785')],
              fieldbackground=[('disabled', '#F0F2F5')])
    return style


def _rounded_rect(canvas, x1, y1, x2, y2, radius, **kw):
    """角丸四角形をCanvasへ描画。標準ttk限定モードでは呼ばない。"""
    r = max(0, min(int(radius), (x2 - x1) / 2, (y2 - y1) / 2))
    if r <= 1:
        return canvas.create_rectangle(x1, y1, x2, y2, **kw)
    return canvas.create_polygon(
        x1 + r, y1, x2-r, y1, x2, y1, x2, y1+r,
        x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
        x1, y2, x1, y2-r, x1, y1+r, x1, y1,
        smooth=True, splinesteps=12, **kw)


class CanvasActionButton(tk.Canvas):
    """独自描画のボタン。標準ttk限定モードでは使用しない。"""
    def __init__(self, master, text='実行', command=None, theme=None, width=140, height=38):
        self.theme = resolve_theme(theme)
        col = self.theme.get('colors', {})
        self.colors = col
        self.caption = text
        self.command = command
        self.hover = False
        self.down = False
        super().__init__(master, height=height, width=width,
                         highlightthickness=0, bd=0,
                         bg=col.get('background', '#F2F6FB'),
                         cursor='hand2', takefocus=1)
        self.bind('<Configure>', lambda e: self._draw())
        self.bind('<Enter>', self._enter)
        self.bind('<Leave>', self._leave)
        self.bind('<ButtonPress-1>', self._press)
        self.bind('<ButtonRelease-1>', self._release)
        self.bind('<Return>', lambda e: self._invoke())
        self.bind('<space>', lambda e: self._invoke())
        self._draw()

    def _enter(self, _event):
        self.hover = True
        self._draw()

    def _leave(self, _event):
        self.hover = False
        self.down = False
        self._draw()

    def _press(self, _event):
        self.focus_set()
        self.down = True
        self._draw()

    def _release(self, event):
        was_pressed = self.down
        self.down = False
        self._draw()
        if was_pressed and 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self._invoke()

    def _invoke(self):
        if self.command:
            self.command()

    def _draw(self):
        self.delete('all')
        w, h = max(25, self.winfo_width()), max(20, self.winfo_height())
        c = self.colors
        opts = self.theme.get('options', {})
        role = opts.get('button_pressed_role' if self.down else 'button_hover_role', 'accent_hover')
        fill = c.get(role, '#12519D') if self.hover or self.down else c.get('accent', '#1765C7')
        radius = int(opts.get('corner_radius', 10))
        _rounded_rect(self, 2, 2, w - 2, h - 2, radius, fill=fill, outline=fill)
        self.create_text(w / 2, h / 2, text=self.caption,
                         fill=c.get('accent_text', '#FFFFFF'),
                         font=(opts.get('font_family', 'Yu Gothic UI'),
                               int(opts.get('font_size', 10)), opts.get('button_text_weight', 'normal')))


class CanvasValueSlider(tk.Canvas):
    """簡易カスタムスライダー。標準ttk限定モードでは使用しない。"""
    def __init__(self, master, theme=None, variable=None, width=230, height=34,
                 from_=0, to=100, command=None):
        self.theme = resolve_theme(theme)
        self.variable = variable or tk.DoubleVar(master=master, value=50)
        self.minimum = float(from_)
        self.maximum = float(to)
        self.command = command
        c = self.theme.get('colors', {})
        super().__init__(master, width=width, height=height, bd=0, highlightthickness=0,
                         bg=c.get('background', '#F2F6FB'), takefocus=1,
                         cursor='hand2')
        self.bind('<Configure>', lambda e: self._draw())
        self.bind('<Button-1>', self._change)
        self.bind('<B1-Motion>', self._change)
        self.bind('<Left>', lambda e: self._step(-1))
        self.bind('<Right>', lambda e: self._step(1))
        self.variable.trace_add('write', lambda *_: self._draw())
        self._draw()

    def _step(self, amount):
        self.variable.set(max(self.minimum, min(self.maximum, self.variable.get() + amount)))
        if self.command:
            self.command(self.variable.get())

    def _change(self, event):
        self.focus_set()
        w = max(45, self.winfo_width())
        v = (event.x - 14) / max(1, (w - 28))
        self.variable.set(round(self.minimum + min(1, max(0, v)) * (self.maximum - self.minimum)))
        if self.command:
            self.command(self.variable.get())

    def _draw(self):
        self.delete('all')
        w, h = max(45, self.winfo_width()), max(22, self.winfo_height())
        c = self.theme.get('colors', {})
        x1, x2, y = 14, w - 14, h / 2
        value = float(self.variable.get())
        frac = (value - self.minimum) / max(1e-9, self.maximum - self.minimum)
        frac = max(0, min(1, frac))
        x = x1 + (x2 - x1) * frac
        opts = self.theme.get('options', {})
        self.create_line(x1, y, x2, y,
                         fill=c.get(opts.get('slider_track_color_role','surface_alt'),'#E7EEF8'), width=8,
                         capstyle='round')
        self.create_line(x1, y, x, y, fill=c.get(opts.get('slider_active_role','accent'),'#1765C7'), width=8,
                         capstyle='round')
        size = int(self.theme.get('options', {}).get('slider_thumb_size', 16))
        self.create_oval(x-size/2, y-size/2, x+size/2, y+size/2,
                         fill=c.get(opts.get('slider_thumb_color_role','surface'),'#FFFFFF'),
                         outline=c.get('accent', '#1765C7'), width=2)


def make_action_button(parent, text, command, theme=None, **kwargs):
    """標準ttk限定なら常にttk.Button。その他では指定したカスタム形状だけ独自描画。"""
    t = resolve_theme(theme)
    mode = t.get('render_mode', 'standard_ttk')
    choice = t.get('options', {}).get('button_shape', 'standard')
    if mode != 'standard_ttk' and (mode == 'design' or choice == 'pill'):
        return CanvasActionButton(parent, text=text, command=command, theme=t,
                                  width=kwargs.get('width', max(80,int(t.get('options',{}).get('button_width_chars',12))*10)),
                                  height=kwargs.get('height', 38))
    return ttk.Button(parent, text=text, command=command,
                      width=int(t.get('options',{}).get('button_width_chars',12)),
                      style=kwargs.get('ttk_style', 'Primary.TButton'))


def make_value_slider(parent, variable, theme=None, **kwargs):
    """標準ttk限定なら常にttk.Scaleを返す。"""
    t = resolve_theme(theme)
    mode = t.get('render_mode', 'standard_ttk')
    choice = t.get('options', {}).get('slider_shape', 'standard')
    if mode != 'standard_ttk' and (mode == 'design' or choice == 'custom'):
        return CanvasValueSlider(parent, theme=t, variable=variable, width=kwargs.get('width', 230))
    return ttk.Scale(parent, from_=0, to=100, variable=variable,
                     orient='horizontal', style=kwargs.get('ttk_style', 'TScale'))
