# File-Searchへのテーマ適用（連携例）

GUI Design Studioで「Urban」「アウトライン」「標準ttk限定」を選択し、`design_theme.json` と `design_theme.py` を出力しました。

## 適用方法

1. File-Search本体のPythonコードの横に `design_theme.py` を配置。
2. `from design_theme import apply_theme, THEME` でテーマを読み込み、Tk rootを作成した後に `apply_theme(root)` を実行。
3. 既存のTkウィジェットを必要に応じてttkへ置き換え、背景色・Treeviewの選択色などを調整。
4. 検索、ファイルコピー、連番付与、cfg保存はテーマとは別のアプリ機能として回帰テストを行う。

## 設計上の注意

- `design_theme.json` はデータであり、単体では画面を書き換えません。
- `design_theme.py` はttkスタイルの設定を行います。独自のスタイル名を使う箇所はFile-Search側で指定します。
- 自動変換ではないため、元アプリが多くの`tk.Button`などを使う場合、別途画面部品を変更することがあります。
- File-Searchで追加したTab往復や同名ファイルの上書き確認は、Studioから出力したテーマの機能ではありません。
- 実際の業務ファイル／cfgをGitHubへ公開しないでください。

## 確認済みの内容

- Urbanテーマ適用版の表示と通常操作：利用者がWindowsで確認
- 自動テスト：Linux仮想GUIで実施
- 同名ファイルの上書き確認機能：公開候補版で追加。Windowsでの確認は別途必要
