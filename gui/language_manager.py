from gui.tabs.about.translations import FA as ABOUT_FA, EN as ABOUT_EN
from gui.tabs.dashboard.translations import FA as DASH_FA, EN as DASH_EN
from gui.tabs.export.translations import FA as EXP_FA, EN as EXP_EN
from gui.tabs.input.translations import FA as INP_FA, EN as INP_EN
from gui.tabs.rename.translations import FA as REN_FA, EN as REN_EN
from gui.tabs.scanner.translations import FA as SCN_FA, EN as SCN_EN
from gui.tabs.archive.translations import FA as ARC_FA, EN as ARC_EN

class LanguageManager:

    current_lang = "en"

    BASE_TEXTS = {
        "en": {
            "app_title": "🚀 LuciNet",
            "btn_dark": "🌙 Dark Mode",
            "btn_light": "☀️ Light Mode",
            "tab_dashboard": "📊 Dashboard",
            "tab_input": "📥 Input",
            "tab_archive": "🗄️ Archive",
            "tab_scanner": "📡 Scanner",
            "tab_rename": "✏️ Rename",
            "tab_export": "📤 Export",
            "tab_about": "ℹ️ About",
        },
        "fa": {
            "app_title": "🚀 لوسی نت",
            "btn_dark": "🌙 حالت تاریک",
            "btn_light": "☀️ حالت روشن",
            "tab_dashboard": "📊 داشبورد",
            "tab_input": "📥 ورودی",
            "tab_archive": "🗄️ آرشیو",
            "tab_scanner": "📡 اسکنر",
            "tab_rename": "✏️ تغییر نام",
            "tab_export": "📤 خروجی",
            "tab_about": "ℹ️ درباره برنامه",
        },
    }

    TEXTS = {
        "en": {
            **BASE_TEXTS["en"],
            **ABOUT_EN,
            **DASH_EN,
            **EXP_EN,
            **INP_EN,
            **REN_EN,
            **SCN_EN,
            **ARC_EN,
        },
        "fa": {
            **BASE_TEXTS["fa"],
            **ABOUT_FA,
            **DASH_FA,
            **EXP_FA,
            **INP_FA,
            **REN_FA,
            **SCN_FA,
            **ARC_FA,
        },
    }

    @classmethod
    def tr(cls, key):

        return cls.TEXTS.get(cls.current_lang, {}).get(key, key)

    @classmethod
    def toggle_language(cls):

        cls.current_lang = "fa" if cls.current_lang == "en" else "en"
        return cls.current_lang
