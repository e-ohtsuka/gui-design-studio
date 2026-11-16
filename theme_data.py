"""GUI Design Studio のテーマ定義。組み込みテーマは編集しても原本を書き換えない。"""
import copy
import json
import os
import re
import tempfile
import uuid
from pathlib import Path


COLOR_FIELDS = [
    ('background', 'ウィンドウ背景'),
    ('surface', 'パネル背景'),
    ('surface_alt', '副パネル・通常ボタン'),
    ('accent', '主アクセント'),
    ('accent_hover', 'ボタンのホバー色'),
    ('accent_text', 'アクセント上の文字'),
    ('text', '本文文字'),
    ('muted', '補助文字'),
    ('border', '枠線'),
    ('field_background', '入力欄背景'),
    ('selection', '選択状態の背景'),
    ('success', '成功・正常'),
    ('warning', '注意'),
    ('danger', '危険・削除'),
]

DEFAULT_OPTIONS = {
    'density': 'normal',
    'button_style': 'raised',
    'button_shape': 'standard',
    'slider_shape': 'standard',
    'corner_radius': 10,
    'frame_border': 1,
    'group_padding': 10,
    'panel_padding': 14,
    'control_gap': 9,
    'section_gap': 15,
    'button_padding_x': 14,
    'button_padding_y': 8,
    'button_border': 1,
    'input_padding_x': 8,
    'input_padding_y': 6,
    'input_border': 1,
    'choice_label_color': 'text',
    'choice_font_weight': 'normal',
    'choice_indicator_color': 'default',
    'choice_indicator_shape': 'check',
    'choice_padding_x': 3,
    'choice_padding_y': 4,
    'choice_font_size': 10,
    'font_family': 'Yu Gothic UI',
    'font_size': 10,
    'font_weight': 'normal',
    'title_weight': 'bold',
    'section_weight': 'bold',
    'title_size': 17,
    'section_size': 11,
    'row_height': 27,
    'tree_heading_weight': 'bold',
    'tree_selection_text_role': 'text',
    'slider_thumb_size': 16,
    'scrollbar_width': 14,
    'progress_height': 13,
    'progress_color_role': 'accent',
    'slider_track_color_role': 'surface_alt',
    'input_focus_role': 'accent',
    'tab_padding_x': 13,
    'tab_padding_y': 7,
    'tab_selected_text_role': 'accent',
    'frame_relief': 'solid',
    'frame_color_role': 'border',
    'label_padding_x': 0,
    'label_padding_y': 0,
    'button_hover_role': 'accent_hover',
    'button_pressed_role': 'accent_hover',
    'button_disabled_role': 'border',
    'button_text_weight': 'normal',
    'button_width_chars': 12,
    'input_text_weight': 'normal',
    'input_selection_role': 'selection',
    'input_disabled_bg_role': 'surface_alt',
    'input_readonly_bg_role': 'field_background',
    'input_arrow_size': 13,
    'choice_indicator_size': 16,
    'choice_active_bg_role': 'surface',
    'choice_disabled_color_role': 'muted',
    'slider_thumb_color_role': 'surface',
    'slider_trough_border': 1,
    'slider_active_role': 'accent',
    'scrollbar_appearance': 'flat',
    'scrollbar_thumb_role': 'border',
    'scrollbar_trough_role': 'background',
    'scrollbar_active_role': 'selection',
    'scrollbar_arrow_role': 'text',
    'scrollbar_border': 1,
    'scrollbar_relief': 'flat',
    'progress_trough_role': 'surface_alt',
    'progress_border': 1,
    'muted_font_size': 10,
    'status_font_size': 10,
    'title_color_role': 'text',
    'section_color_role': 'text',
    'tree_border': 1,
    'tree_heading_padding_x': 7,
    'tree_heading_padding_y': 5,
    'tree_selected_bg_role': 'selection',
    'tab_active_role': 'selection',
    'tab_selected_bg_role': 'surface',
    'tab_weight': 'normal',
    'notebook_border': 1,
}

# 「配色のみ一括変更」用。各役割を持つ色をまとめて切り替える。
PALETTES = {
    'ブルー': ['#F0F5FB','#FFFFFF','#E6EFFB','#246BC4','#1453A1','#FFFFFF','#253A53','#61758E','#BED0E5','#FFFFFF','#D4E5FF','#36835F','#B88332','#BE5057'],
    'グリーン': ['#EFF4EC','#FFFFFF','#E2EDD9','#48775A','#365E45','#FFFFFF','#344838','#66796C','#BBCDB9','#FFFFFF','#D5E9D7','#387958','#B48335','#B95655'],
    'ティール': ['#EDF7F7','#FFFFFF','#DAEFEE','#1C8792','#12636C','#FFFFFF','#224750','#5A7A7D','#B5D5D5','#FFFFFF','#C6E9E8','#28836D','#AD7B2B','#BC5555'],
    'バイオレット': ['#F5F1FA','#FFFFFF','#EBE2F5','#7353AA','#5B3D8F','#FFFFFF','#332C4A','#797089','#D3C5E3','#FFFFFF','#E5DAF5','#4B846E','#AF8034','#B55262'],
    'アンバー': ['#FBF5EA','#FFFFFF','#F5E8D4','#B47726','#8D581B','#FFFFFF','#59442D','#82705B','#DFCEAD','#FFFFFF','#F5E1BE','#568468','#A56E28','#AE504B'],
    'モノクロ': ['#F1F2F3','#FFFFFF','#E2E4E7','#505A66','#343C47','#FFFFFF','#282F37','#69717C','#C2C8CF','#FFFFFF','#D5DAE0','#3A8060','#AA7B2A','#A8444B'],
}

# 暗色系も配色を役割ごとに管理し、すべての部品へ一括で反映する。
PALETTES.update({
    'ダークブルー': ['#191F29','#252D39','#343F4C','#508BCC','#3975B8','#FFFFFF','#E4EBF4','#A8B5C4','#526174','#232B38','#3A5F85','#54AD8B','#D1A05A','#D8787B'],
    'ダークグリーン': ['#1B2520','#26352C','#35473B','#6C9F77','#548360','#101A13','#E6F0E6','#B6C9B9','#4A6652','#233028','#3A6547','#7DB791','#D3A564','#D17B7B'],
    'チャコール': ['#222326','#2F3135','#414349','#A68B69','#8B7355','#171717','#EEEAE3','#B9B7B2','#5A5D64','#2B2D31','#5E5D59','#7DAD93','#D1A263','#CE8181'],
})



def base_colors():
    return dict(zip((key for key, _ in COLOR_FIELDS), PALETTES['ブルー']))


def theme(name, family='ブルー', *, description='', bg_override=None,
          option_override=None, requires_custom=False, theme_id=None):
    colors = dict(zip((key for key, _ in COLOR_FIELDS), PALETTES[family]))
    if bg_override:
        colors.update(bg_override)
    options = copy.deepcopy(DEFAULT_OPTIONS)
    if option_override:
        options.update(option_override)
    return {
        'schema_version': 1, 'id': theme_id or name.lower().replace(' ', '-'),
        'name': name, 'description': description, 'origin': 'built_in',
        'palette_family': family, 'render_mode': 'standard_ttk',
        'requires_custom': requires_custom,
        'colors': colors, 'options': options,
    }


BUILTINS = [
    theme('Urban', 'ブルー', description='都市的なブルーグレー。業務ツールに', option_override={'density':'compact','button_style':'flat'}),
    theme('Forest', 'グリーン', description='落ち着いた自然色。業務アプリ向け'),
    theme('Azure', 'ブルー', description='明るく爽やかなブルー', bg_override={'accent':'#1765C7','accent_hover':'#104E9C','surface_alt':'#DBEBFA'}),
    theme('Atelier', 'アンバー', description='温かい紙と木の印象', bg_override={'accent':'#A56B43','accent_hover':'#845335'}),
    theme('Chrome風', 'ブルー', description='明るくフラットなブラウザ風（独自解釈）', option_override={'button_style':'flat', 'density':'normal'}, bg_override={'background':'#F3F4F6','surface_alt':'#E8EDF3','accent':'#1A73E8'}),
    theme('Studio Dark', 'ティール', description='青緑の操作ボタンを備えたチャコール系作業画面', bg_override={'background':'#202429','surface':'#2E343A','surface_alt':'#3C444B','accent':'#4B9F92','accent_hover':'#357F75','accent_text':'#FFFFFF','text':'#E9ECEC','muted':'#AFBDC1','border':'#536067','field_background':'#293037','selection':'#3D675F'}),
    theme('Photoshop風', 'ブルー', description='高密度・暗色の編集ソフト風（独自解釈）', bg_override={'background':'#242424','surface':'#363636','surface_alt':'#484848','accent':'#4C91D9','accent_hover':'#3471B8','text':'#F2F2F2','muted':'#BDBDBD','border':'#595959','field_background':'#303030','selection':'#345C84'},option_override={'density':'compact','button_style':'flat'}),
    theme('Midnight', 'バイオレット', description='深夜の青紫', bg_override={'background':'#1E2335','surface':'#2A3045','surface_alt':'#39445C','accent':'#9678DF','accent_hover':'#7A5CC2','text':'#F0F0F7','muted':'#B7BED4','border':'#515976','field_background':'#262C40','selection':'#4E4A78'}),
    theme('Ocean', 'ティール', description='水色と深い青緑'),
    theme('Sakura', 'バイオレット', description='淡い桜色', bg_override={'background':'#FCF1F5','surface_alt':'#F8E5ED','accent':'#BF587C','accent_hover':'#9E3E65'}),
    theme('Sandstone', 'アンバー', description='温かな砂色と控えめな輪郭',option_override={'button_style':'flat'}),
    theme('Slate', 'モノクロ', description='抑制されたモノトーン'),
    theme('Mint', 'グリーン', description='軽快なミント', bg_override={'background':'#EEF9F3','accent':'#24947E','accent_hover':'#19725E'}),
    theme('Industrial', 'モノクロ', description='直線的な工業デザイン',option_override={'frame_border':2,'button_style':'outline','density':'compact'}),
    theme('Autumn', 'アンバー', description='秋の琥珀色'),
    # 以下は各種アプリの「作業環境としての雰囲気」を着想源にした独自配色。
    # 製品の公式カラーや画面を正確に再現するテーマではない。
    theme('Store Holiday Blue', 'ブルー', description='store-holiday-calendar v1.12のUI色を継承',
          bg_override={'background':'#F3F7FD','surface':'#FFFFFF','surface_alt':'#E1EEFF',
                       'accent':'#1765C7','accent_hover':'#114F9E','accent_text':'#FFFFFF',
                       'text':'#182C4E','muted':'#667A94','border':'#BDD0E7',
                       'field_background':'#FFFFFF','selection':'#CFE6FF'},
          option_override={'button_style':'raised','title_size':18,'section_size':12,'button_padding_x':13}),
    theme('Code Night', 'ダークブルー', description='コードエディター風、濃紺と青い操作色',
          option_override={'density':'compact','button_style':'flat'}),
    theme('Carbon', 'チャコール', description='黒に近い無彩色、低彩度のブロンズボタン',
          bg_override={'accent':'#8D939B','accent_hover':'#747B83','accent_text':'#16191C'}),
    theme('Obsidian', 'チャコール', description='深い黒と控えめなスレートブルー',
          bg_override={'background':'#171A1F','surface':'#242930','surface_alt':'#323942',
                       'accent':'#7089A6','accent_hover':'#546E8A','accent_text':'#10151B',
                       'text':'#E4E8ED','muted':'#A5B0BD','border':'#485361','field_background':'#20252C','selection':'#536376'}),
    theme('Graphite', 'チャコール', description='マットな灰黒色、控えめな金属調',
          bg_override={'accent':'#8F9AA6','accent_hover':'#747E88','accent_text':'#111720',
                       'background':'#26282B','surface':'#34373C','field_background':'#2D3034'},
          option_override={'button_style':'outline'}),
    theme('Noir', 'チャコール', description='モノクロ中心の静かなダークUI',
          bg_override={'background':'#161616','surface':'#222222','surface_alt':'#303030',
                       'accent':'#CBCBCB','accent_hover':'#ABABAB','accent_text':'#222222',
                       'text':'#F0F0F0','muted':'#B4B4B4','border':'#494949','field_background':'#1F1F1F','selection':'#545454'},
          option_override={'button_style':'flat'}),
    theme('Night Forest', 'ダークグリーン', description='深い森のような低彩度グリーン'),
    theme('Deep Ocean', 'ダークブルー', description='紺と深海ティールの組み合わせ',
          bg_override={'background':'#14242C','surface':'#1F333C','surface_alt':'#304A54',
                       'accent':'#4C9EA9','accent_hover':'#37818D','text':'#E3F2F2',
                       'muted':'#A0C1C5','border':'#47616B','field_background':'#1A3038','selection':'#346A74'}),
    theme('Aubergine Night', 'バイオレット', description='落ち着いた紫褐色のクリエイティブUI',
          bg_override={'background':'#25212B','surface':'#322D39','surface_alt':'#403A48',
                       'accent':'#9D87BB','accent_hover':'#806BA1','accent_text':'#191320',
                       'text':'#ECE7F1','muted':'#BAB2C5','border':'#605669','field_background':'#292530','selection':'#554762'}),
    theme('Copper Night', 'チャコール', description='ダークグレーに銅色アクセント',
          bg_override={'accent':'#B47D60','accent_hover':'#916048','accent_text':'#141414'},
          option_override={'button_style':'flat'}),
    theme('Nordic Night', 'ダークブルー', description='柔らかい北欧風の青灰色',
          bg_override={'background':'#252D38','surface':'#313C49','surface_alt':'#405061',
                       'accent':'#8EB3CF','accent_hover':'#7198B6','accent_text':'#12202D',
                       'text':'#ECF0F5','muted':'#BCCAD5','border':'#59697A','field_background':'#2B3542','selection':'#496A83'}),
    theme('Ink Slate', 'チャコール', description='夜の執筆ツールを意識した落ち着いた黒青',
          bg_override={'background':'#1F242B','surface':'#2C333D','surface_alt':'#3B4652',
                       'accent':'#7399B4','accent_hover':'#587D97','accent_text':'#0C1821',
                       'text':'#E6E8EB','muted':'#B3C0CB','border':'#526171','field_background':'#252C34','selection':'#485E73'}),
    theme('Quiet Sand', 'アンバー', description='ノートアプリ風の静かな暖色',
          bg_override={'background':'#F7F5F0','surface':'#FFFEFC','surface_alt':'#EEEBE5',
                       'accent':'#867966','accent_hover':'#6A5E50','text':'#393D41','muted':'#74777A',
                       'border':'#D5D0C7','field_background':'#FFFFFF','selection':'#DDD7CB'},
          option_override={'button_style':'flat'}),
    theme('Minimal Paper', 'モノクロ', description='文書・メモアプリ風の軽い白黒',
          bg_override={'background':'#F8F9FA','surface':'#FFFFFF','surface_alt':'#EFF1F3',
                       'accent':'#45556B','accent_hover':'#303E51','text':'#252A31',
                       'muted':'#6D7782','border':'#D9DFE5'},
          option_override={'button_style':'flat','density':'spacious'}),
    theme('Dashboard Navy', 'ダークブルー', description='分析ダッシュボード風の紺色UI',
          bg_override={'background':'#151E2D','surface':'#232F42','surface_alt':'#32425A',
                       'accent':'#6A9FD5','accent_hover':'#5182B6','text':'#E9F0FA',
                       'muted':'#B5C7DB','border':'#465C77','field_background':'#1B283A','selection':'#41678D'},
          option_override={'density':'compact','button_style':'flat'}),
    theme('Terracotta', 'アンバー', description='陶器の落ち着いた暖色',
          bg_override={'background':'#FAF3F0','surface':'#FFFAF7','surface_alt':'#F0DDD5',
                       'accent':'#A95F4F','accent_hover':'#8A4A3F','text':'#4F3934','muted':'#80655D',
                       'border':'#DDC3BA','selection':'#EFC4B5'}),
    theme('Pine Mist', 'グリーン', description='深緑と白霧色の業務アプリ向け配色',
          bg_override={'background':'#EAF0EC','surface':'#FFFFFF','surface_alt':'#DCE7DE',
                       'accent':'#356A5E','accent_hover':'#275548','text':'#29423D','muted':'#648078',
                       'border':'#BACEC5','selection':'#C7DDD0'}),
    theme('Quiet Indigo', 'バイオレット', description='抑えた藍色、静かなソフトウェアUI',
          bg_override={'background':'#F0F1F8','surface':'#FFFFFF','surface_alt':'#E1E4F0',
                       'accent':'#545E8C','accent_hover':'#404A70','text':'#303652','muted':'#717895',
                       'border':'#C1C7DB','selection':'#CFD7ED'}),
    theme('Warm Charcoal', 'チャコール', description='暗色に柔らかいゴールドブラウン',
          bg_override={'background':'#292724','surface':'#35322F','surface_alt':'#45413C',
                       'accent':'#AB9377','accent_hover':'#8C795F','accent_text':'#201B15',
                       'text':'#F0EAE3','muted':'#C0B8AD','border':'#5B554D','field_background':'#2C2925','selection':'#5E5449'}),
    theme('Terminal Green', 'ダークグリーン', description='端末画面をイメージした落ち着いた緑',
          bg_override={'background':'#151E1B','surface':'#202B26','surface_alt':'#2F3F35',
                       'accent':'#7FBA8F','accent_hover':'#649C76','accent_text':'#152318',
                       'text':'#DAEFDE','muted':'#A9C3B0','border':'#445B4A','field_background':'#19241F','selection':'#476B51'},
          option_override={'density':'compact'}),
    theme('Custom Glass', 'ティール', description='角丸の独自描画部品を含む',requires_custom=True,option_override={'button_shape':'pill','slider_shape':'custom','corner_radius':18}),
]


def custom_dir():
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA') or (Path.home()/'AppData'/'Local'))
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME') or (Path.home()/'.config'))
    return base/'GUI-Design-Studio'


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # 同じディレクトリで一時ファイルを作り、正常に書けた後だけ置換する。
    fd, temp = tempfile.mkstemp(prefix='.theme-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def validate_theme(data):
    if not isinstance(data, dict):
        raise ValueError('テーマデータが辞書形式ではありません')
    if data.get('schema_version') != 1:
        raise ValueError('対応していないテーマ形式です（schema_versionは1のみ）')
    if not isinstance(data.get('name'), str) or not data['name'].strip():
        raise ValueError('テーマ名が不正です')
    cols = data.get('colors')
    if not isinstance(cols, dict):
        raise ValueError('配色情報が見つかりません')
    for key, _label in COLOR_FIELDS:
        value = cols.get(key)
        if not isinstance(value, str) or not re.fullmatch(r'#[0-9A-Fa-f]{6}', value):
            raise ValueError(f'色の形式が不正です: {key}')
    opts = data.get('options')
    if not isinstance(opts, dict):
        raise ValueError('部品設定が見つかりません')
    for key, default in DEFAULT_OPTIONS.items():
        value = opts.get(key)
        if isinstance(default, int):
            if type(value) is not int or not 0 <= value <= 120:
                raise ValueError(f'設定値が不正です: {key}')
        elif not isinstance(value, str) or not value.strip():
            raise ValueError(f'設定値が不正です: {key}')
    if opts['density'] not in ('compact','normal','spacious'):
        raise ValueError('画面密度が不正です')
    if opts['button_style'] not in ('flat','raised','outline'):
        raise ValueError('ボタンの立体感が不正です')
    if opts['button_shape'] not in ('standard','pill'):
        raise ValueError('ボタン形状が不正です')
    if opts['slider_shape'] not in ('standard','custom'):
        raise ValueError('スライダー形状が不正です')
    if opts['scrollbar_appearance'] not in ('standard', 'flat'):
        raise ValueError('スクロールバー形状が不正です')
    if opts['choice_indicator_shape'] not in ('system', 'check', 'cross'):
        raise ValueError('チェックマーク形状が不正です')
    if opts['choice_label_color'] not in ('text', 'accent'):
        raise ValueError('選択部品の文字色が不正です')
    if opts['choice_font_weight'] not in ('normal', 'bold'):
        raise ValueError('選択部品の文字の太さが不正です')
    if opts['choice_indicator_color'] not in ('default', 'accent'):
        raise ValueError('選択マーク色が不正です')
    allowed_roles = {
        'font_weight': ('normal', 'bold'),
        'title_weight': ('normal', 'bold'),
        'section_weight': ('normal', 'bold'),
        'tree_heading_weight': ('normal', 'bold'),
        'tree_selection_text_role': ('text', 'accent_text'),
        'progress_color_role': ('accent', 'success', 'warning'),
        'slider_track_color_role': ('surface_alt', 'border'),
        'input_focus_role': ('accent', 'border'),
        'tab_selected_text_role': ('accent', 'text'),
        'frame_relief': ('flat', 'solid', 'groove', 'ridge'),
        'frame_color_role': ('border', 'accent', 'surface_alt'),
        'button_hover_role': ('accent_hover', 'selection', 'surface_alt'),
        'button_pressed_role': ('accent_hover', 'selection', 'border'),
        'button_disabled_role': ('border', 'surface_alt'),
        'button_text_weight': ('normal', 'bold'),
        'input_text_weight': ('normal', 'bold'),
        'input_selection_role': ('selection', 'accent'),
        'input_disabled_bg_role': ('surface_alt', 'background'),
        'input_readonly_bg_role': ('field_background', 'surface_alt'),
        'choice_active_bg_role': ('surface', 'surface_alt'),
        'choice_disabled_color_role': ('muted', 'border'),
        'slider_thumb_color_role': ('surface', 'accent', 'surface_alt'),
        'slider_active_role': ('accent', 'accent_hover', 'selection'),
        'scrollbar_thumb_role': ('surface_alt', 'border', 'accent'),
        'scrollbar_trough_role': ('background', 'surface', 'surface_alt'),
        'scrollbar_active_role': ('selection', 'accent', 'accent_hover'),
        'scrollbar_arrow_role': ('text', 'muted', 'accent'),
        'scrollbar_relief': ('flat', 'raised', 'sunken'),
        'progress_trough_role': ('surface_alt', 'background', 'border'),
        'title_color_role': ('text', 'accent'),
        'section_color_role': ('text', 'accent'),
        'tree_selected_bg_role': ('selection', 'accent', 'surface_alt'),
        'tab_active_role': ('selection', 'surface_alt', 'accent'),
        'tab_selected_bg_role': ('surface', 'background', 'surface_alt'),
        'tab_weight': ('normal', 'bold'),
    }
    for key, permitted in allowed_roles.items():
        if opts[key] not in permitted:
            raise ValueError(f'設定値が不正です: {key}')
    if data.get('render_mode', 'standard_ttk') not in ('standard_ttk','hybrid','design'):
        raise ValueError('描画方式が不正です')
    return True


def normalized_theme(data, *, name=None):
    """過去の形式や必要なフィールドを補い、既知の設定だけに整理する。"""
    d = copy.deepcopy(data)
    colors = base_colors()
    colors.update({k:v for k,v in d.get('colors', {}).items() if k in colors})
    opts = copy.deepcopy(DEFAULT_OPTIONS)
    saved_options = d.get('options', {})
    opts.update({k:v for k,v in saved_options.items() if k in opts})
    # v0.7以前のマイテーマは「旧来の標準スクロールバー」を維持する。
    # 新規テーマだけは、横線のないフラット表示を初期値にする。
    if 'scrollbar_appearance' not in saved_options:
        opts['scrollbar_appearance'] = 'standard'
    d['colors'] = colors
    d['options'] = opts
    d['name'] = name or d.get('name', 'New Theme')
    d['schema_version'] = 1
    d.setdefault('render_mode', 'standard_ttk')
    d.setdefault('description', '')
    d.setdefault('palette_family', 'カスタム')
    d.setdefault('requires_custom', False)
    validate_theme(d)
    return d


def load_custom_themes(directory=None):
    directory = Path(directory) if directory else custom_dir()/'themes'
    result = []
    if directory.exists():
        for path in sorted(directory.glob('*.json')):
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                # v0.1から保存されているテーマは新しい設定項目を補って読み込む。
                data = normalized_theme(data)
                if data.get('origin') == 'custom' and data.get('id') == path.stem:
                    result.append(data)
            except (OSError, ValueError, KeyError, TypeError):
                continue
    return result


def new_custom_theme(current, name):
    candidate = normalized_theme(current, name=name.strip())
    candidate.update({'id': uuid.uuid4().hex, 'origin':'custom','name':name.strip()})
    return candidate
