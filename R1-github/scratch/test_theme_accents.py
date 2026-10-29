import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ui_theme

def test_all_themes():
    print("Testing theme accent colors and contrast calculations:\n")
    for key, label, swatch in ui_theme.VARIANT_LABELS:
        theme_data = ui_theme.DARK_VARIANTS[key]
        accent = theme_data.get("accent")
        on_accent = ui_theme.get_readable_text_color(accent)
        ctx = ui_theme.get_theme_accent_context(key)
        print(f"Theme: {label:<10} | Accent: {accent} | Text on Accent: {on_accent} | Is Light: {ctx['is_light']}")

if __name__ == "__main__":
    test_all_themes()
