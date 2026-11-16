"""サンプルテーマの使用例（実行: python examples/demo.py）。"""
import tkinter as tk
from tkinter import ttk
from urban_theme import apply_theme, make_action_button

root = tk.Tk()
root.title('GUI Design Studio - サンプル')
root.geometry('350x220')
apply_theme(root)
content = ttk.Frame(root, padding=20)
content.pack(fill='both', expand=True)
ttk.Label(content, text='GUI Design Studio', style='Title.TLabel').pack(anchor='w')
ttk.Label(content, text='テーマの見本です。').pack(anchor='w', pady=12)
ttk.Entry(content).pack(fill='x', pady=(0,8))
make_action_button(content, '保存', lambda: print('clicked')).pack(anchor='e')
root.mainloop()
