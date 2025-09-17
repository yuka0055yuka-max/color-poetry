import ui
import photos
import datetime
import console
import hashlib

# 定数
DEFAULT_FONT_SIZE = 24
PADDING = 20
LINE_SPACING = 10

# --- 色生成ロジック(視認性向上版)---
def get_dynamic_color(char, is_dark_bg):
    """文字のハッシュから色を生成するが、背景とのコントラストを考慮する"""
    h = hashlib.md5(char.encode('utf-8')).hexdigest()
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)

    # ダークモードの場合は、ある程度明るい色を保証する
    if is_dark_bg:
        # RGBの最大値を128以上に、合計値を384以上に調整して暗すぎる色を避ける
        while max(r, g, b) < 128 or (r + g + b) < 384:
            r = (r + 50) % 256
            g = (g + 30) % 256
            b = (b + 70) % 256
    # ライトモードの場合は、ある程度暗い色を保証する
    else:
        # RGBの最小値を128以下に、合計値を384以下に調整して明るすぎる色を避ける
        while min(r, g, b) > 128 or (r + g + b) > 384:
            r = (r - 50) % 256
            g = (g - 30) % 256
            b = (b - 70) % 256
            
    return (r/255, g/255, b/255) # uiモジュールは0-1のタプルを好む

# --- 画像生成・保存ロジック(背景色描画の問題を修正)---
def create_image_from_view(view):
    """
    ViewからImageオブジェクトを生成する。
    【重要】最初に背景色で塗りつぶすことで、背景が透明になる問題を解決。
    """
    with ui.ImageContext(view.width, view.height) as ctx:
        # 1. Viewの背景色でコンテキスト全体を塗りつぶす
        ui.set_color(view.bg_color)
        ui.fill_rect(0, 0, view.width, view.height)
        
        # 2. Viewのコンテンツ(サブビュー)を描画する
        view.draw_snapshot()
        
        return ctx.get_image()

# --- メインのUIクラス ---
class ArtTextView(ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg_color = 'white'
        
        # --- UIコントロールの作成 ---
        # テキスト入力欄
        self.textfield = ui.TextField(frame=(10, 10, self.width - 120, 40), flex='W')
        self.textfield.placeholder = 'ここに文字を入力してね'
        self.textfield.clear_button_mode = 'while_editing'
        self.textfield.action = self.update_preview
        self.add_subview(self.textfield)

        # 保存ボタン
        save_btn = ui.Button(title='保存', frame=(self.width - 100, 10, 90, 40), flex='L')
        save_btn.action = self.save_action
        save_btn.background_color = '#4CAF50'
        save_btn.tint_color = 'white'
        self.add_subview(save_btn)

        # フォントサイズラベルとスライダー
        font_label = ui.Label(text='フォントサイズ:', frame=(10, 60, 120, 30))
        self.add_subview(font_label)
        self.font_slider = ui.Slider(frame=(130, 60, self.width - 140, 30), flex='W')
        self.font_slider.value = 0.3
        self.font_slider.action = self.update_preview
        self.add_subview(self.font_slider)

        # 背景色切り替え
        bg_label = ui.Label(text='背景:', frame=(10, 100, 50, 30))
        self.add_subview(bg_label)
        self.bg_segment = ui.SegmentedControl(frame=(70, 100, 150, 30))
        self.bg_segment.segments = ['ライト', 'ダーク']
        self.bg_segment.selected_index = 0
        self.bg_segment.action = self.update_preview
        self.add_subview(self.bg_segment)

        # プレビューエリア用のスクロールビュー
        self.scroll_view = ui.ScrollView(frame=(10, 140, self.width - 20, self.height - 150), flex='WH')
        self.scroll_view.background_color = '#F0F0F0'
        self.scroll_view.border_width = 1
        self.scroll_view.border_color = '#CCCCCC'
        self.add_subview(self.scroll_view)
        
        # プレビュー用のView(スクロールビューの中身)
        self.preview_view = ui.View(frame=(0, 0, self.scroll_view.width, 0))
        self.preview_view.flex = 'W'
        self.scroll_view.add_subview(self.preview_view)
        
        # 初期プレビューの更新
        self.update_preview(None)

    def update_preview(self, sender):
        """プレビューエリアを現在の設定で再描画する"""
        # --- 設定値の取得 ---
        text = self.textfield.text
        # スライダーの値(0-1)を適切なフォントサイズ(12-72)に変換
        font_size = 12 + (self.font_slider.value * 60)
        is_dark_bg = self.bg_segment.selected_index == 1
        
        # 背景色を設定
        bg_color_val = '#222222' if is_dark_bg else '#FFFFFF'
        self.preview_view.bg_color = bg_color_val
        
        # --- プレビュー内の古いラベルを全て削除 ---
        for subview in self.preview_view.subviews[:]:
            self.preview_view.remove_subview(subview)
        
        if not text:
            return # テキストが空なら何もしない

        # --- テキストの描画と自動折り返し ---
        x, y = PADDING, PADDING
        for char in text:
            if char == '\n': # 改行文字に対応
                x = PADDING
                y += font_size + LINE_SPACING
                continue

            char_width, _ = ui.measure_string(char, font=('_system', font_size))
            
            # 右端に達したら改行
            if x + char_width > self.preview_view.width - PADDING:
                x = PADDING
                y += font_size + LINE_SPACING
                
            label = ui.Label(frame=(x, y, char_width, font_size))
            label.text = char
            label.font = ('<System>', font_size)
            label.text_color = get_dynamic_color(char, is_dark_bg)
            
            self.preview_view.add_subview(label)
            x += char_width

        # --- ViewとScrollViewの高さを内容に合わせて調整 ---
        final_height = y + font_size + PADDING
        self.preview_view.frame = (0, 0, self.preview_view.width, final_height)
        self.scroll_view.content_size = (self.preview_view.width, final_height)

    def save_action(self, sender):
        """プレビューを画像として保存する"""
        if not self.textfield.text:
            console.hud_alert('テキストが入力されていません', 'error', 1.0)
            return
            
        # プレビューViewから画像データを生成
        image = create_image_from_view(self.preview_view)
        
        # 写真ライブラリに保存
        photos.save_image(image)
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        console.hud_alert(f"保存完了: art_text_{timestamp}.png", 'success', 1.5)

# --- アプリの実行 ---
if __name__ == '__main__':
    main_view = ArtTextView(name='Art Text Generator', frame=(0, 0, 600, 700))
    main_view.present('sheet')
