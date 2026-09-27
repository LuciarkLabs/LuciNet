
from gui.tabs.about.translations import FA as ABOUT_FA, EN as ABOUT_EN
from gui.tabs.dashboard.translations import FA as DASH_FA, EN as DASH_EN
from gui.tabs.export.translations import FA as EXP_FA, EN as EXP_EN
from gui.tabs.rename.translations import FA as REN_FA, EN as REN_EN
from gui.tabs.scanner.translations import FA as SCN_FA, EN as SCN_EN
from gui.tabs.archive.translations import FA as ARC_FA, EN as ARC_EN
from gui.tabs.connect.translations import (
    FA as CONN_FA,
    EN as CONN_EN,
)


class LanguageManager:
    current_lang = "en"

    BASE_TEXTS = {
        "en": {
            "app_title": "🚀 LuciNet",
            "btn_dark": "🌙 Dark Mode",
            "btn_light": "☀️ Light Mode",
            "tab_connect": "🔌 Connect",
            "tab_dashboard": "📊 Dashboard",
            "tab_input": "📥 Input",
            "tab_archive": "🗄️ Archive",
            "tab_scanner": "📡 Scanner",
            "tab_rename": "✏️ Rename",
            "tab_export": "📤 Export",
            "tab_about": "ℹ️ About",
            "menu_servers": "📥 Input , Export",
            "menu_action_input": "➕ Import Configs",
            "menu_action_export": "📤 Export",
            "menu_tools": "Tools",
            "menu_action_scanner": "⚡ Advanced Scanner",
            "menu_action_rename": "✏️ Rename Tools",
            "menu_action_dashboard": "📊 Dashboard",
            "menu_help": "Help",
            "menu_action_about": "ℹ️ About",
            "tray_open": "Open LuciNet",
            "tray_quit": "Quit",
            "tray_connect": "Connect",
            "tray_disconnect": "Disconnect",
            "tray_msg_connected": "Connection established successfully!",
            "tray_msg_disconnected": "Connection closed.",
            "tray_msg_minimized": "App is running in the background.",
            "tray_status_connected": "LuciNet - Connected 🟢",
            "tray_status_disconnected": "LuciNet - Disconnected 🔴",
            "sub_import_title": "Import Subscription",
            "sub_import_prompt": "Subscription link(s) found!\nWhich archive should they be placed in?\n\n(Note: If you want a new archive, type its name here)",
            "menu_import_clipboard": "📋 Import from Clipboard",
            "menu_import_file": "📄 Import from Text File",
            "menu_add_manual": "➕ Add Custom Configuration",
            "msg_error": "Error",
            "msg_clipboard_empty": "Your clipboard is empty!",
            "msg_select_file": "Select Config File",
            "msg_file_read_err": "Error reading file:\n{err}",
            "msg_no_valid_config": "No standard config or link found in the text!\nMake sure the copied text is valid.",
            "msg_parser_err_title": "Parser Error",
            "msg_parser_err_body": "Configs were found but the parser engine could not read them!",
            "msg_parser_err_details": "\n\nParser error details:\n",
            "msg_db_save_err": "Error saving to database:\n{err}",
            "msg_import_success_title": "Import Successful",
            "msg_import_success_configs": "✅ {count} configs saved in archive '{group}'.\n",
            "msg_import_success_subs": "🔗 {count} subscription links registered.\n",
            "msg_dev_title": "In Development",
            "msg_dev_body": "The manual config creation window will be added in future updates.",
        },
        "fa": {
            "app_title": "🚀 لوسی نت",
            "btn_dark": "🌙 حالت تاریک",
            "btn_light": "☀️ حالت روشن",
            "tab_connect": "🔌 اتصال",
            "tab_dashboard": "📊 داشبورد",
            "tab_input": "📥 ورودی",
            "tab_archive": "🗄️ آرشیو",
            "tab_scanner": "📡 اسکنر",
            "tab_rename": "✏️ تغییر نام",
            "tab_export": "📤 خروجی",
            "tab_about": "ℹ️ درباره برنامه",
            "menu_servers": "📥 ورود کانفیگ و خروجی گرفتن",
            "menu_action_input": "➕ وارد کردن کانفیگ",
            "menu_action_export": "📤 خروجی گرفتن",
            "menu_tools": "ابزارها",
            "menu_action_scanner": "⚡ اسکنر پیشرفته",
            "menu_action_rename": "✏️ ویرایش و تغییر نام",
            "menu_action_dashboard": "📊 داشبورد آماری",
            "menu_help": "راهنما",
            "menu_action_about": "ℹ️ درباره ما",
            "tray_open": "باز کردن لوسی‌نت",
            "tray_quit": "خروج از برنامه",
            "tray_connect": "اتصال",
            "tray_disconnect": "قطع اتصال",
            "tray_msg_connected": "اتصال با موفقیت برقرار شد!",
            "tray_msg_disconnected": "اتصال قطع شد.",
            "tray_msg_minimized": "برنامه در پس‌زمینه در حال اجراست.",
            "tray_status_connected": "لوسی‌نت - متصل 🟢",
            "tray_status_disconnected": "لوسی‌نت - قطع 🔴",
            "sub_import_title": "وارد کردن سابسکریپشن",
            "sub_import_prompt": "لینک سابسکریپشن پیدا شد!\nدر کدام آرشیو قرار بگیرد؟\n\n(نکته: اگر می‌خواهید آرشیو جدید باشد، نام آن را اینجا تایپ کنید)",
            "menu_import_clipboard": "📋 ایمپورت از کلیپ‌بورد",
            "menu_import_file": "📄 ایمپورت از فایل متنی",
            "menu_add_manual": "➕ ساخت کانفیگ دستی",
            "msg_error": "خطا",
            "msg_clipboard_empty": "کلیپ‌بورد شما خالی است!",
            "msg_select_file": "انتخاب فایل کانفیگ",
            "msg_file_read_err": "خطا در خواندن فایل:\n{err}",
            "msg_no_valid_config": "هیچ کانفیگ یا لینکِ استانداردی در متن پیدا نشد!\nمطمئن شوید متن کپی شده معتبر است.",
            "msg_parser_err_title": "خطا در پارسر",
            "msg_parser_err_body": "کانفیگ‌ها پیدا شدند اما موتور پارسر نتوانست آن‌ها را بخواند!",
            "msg_parser_err_details": "\n\nجزئیات خطای پارسر:\n",
            "msg_db_save_err": "خطا در ذخیره‌سازی دیتابیس:\n{err}",
            "msg_import_success_title": "ایمپورت موفق",
            "msg_import_success_configs": "✅ {count} کانفیگ در آرشیو '{group}' ذخیره شد.\n",
            "msg_import_success_subs": "🔗 {count} لینک سابسکریپشن ثبت شد.\n",
            "msg_dev_title": "در حال توسعه",
            "msg_dev_body": "پنجره ساخت دستی کانفیگ در آپدیت‌های بعدی اضافه می‌شود.",
        },
    }

    TEXTS = {
        "en": {
            **BASE_TEXTS["en"],
            **ABOUT_EN,
            **DASH_EN,
            **EXP_EN,
            **REN_EN,
            **SCN_EN,
            **ARC_EN,
            **CONN_EN,
        },
        "fa": {
            **BASE_TEXTS["fa"],
            **ABOUT_FA,
            **DASH_FA,
            **EXP_FA,
            **REN_FA,
            **SCN_FA,
            **ARC_FA,
            **CONN_FA,
        },
    }

    @classmethod
    def tr(cls, key):
        """متد ترجمه: کلمه معادل را بر اساس زبان فعلی برمی‌گرداند"""
        return cls.TEXTS.get(cls.current_lang, {}).get(key, key)

    @classmethod
    def toggle_language(cls):
        """تغییر دهنده زبان"""
        cls.current_lang = "fa" if cls.current_lang == "en" else "en"
        return cls.current_lang
