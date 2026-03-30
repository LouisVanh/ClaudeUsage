import gi, os, json, threading, time, sys, subprocess, importlib, shutil, math, tempfile
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib
from pathlib import Path
from datetime import datetime
import cairo

def ensure_uc():
    try:
        importlib.import_module('undetected_chromedriver')
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "undetected-chromedriver"])
        importlib.import_module('undetected_chromedriver')

def ensure_cloudscraper():
    try:
        importlib.import_module('cloudscraper')
    except ImportError:
        try:
            import setuptools._distutils as distutils
            sys.modules['distutils'] = distutils
        except Exception:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "setuptools"])
            import setuptools._distutils as distutils
            sys.modules['distutils'] = distutils
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cloudscraper"])
        importlib.import_module('cloudscraper')

def chrome_version_main():
    for cmd in ["google-chrome", "chromium", "chromium-browser"]:
        if shutil.which(cmd):
            try:
                out = subprocess.check_output([cmd, "--product-version"], stderr=subprocess.STDOUT).decode().strip()
                return int(out.split(".")[0])
            except Exception:
                continue
    return None

class ClaudeUsageTray:
    def __init__(self):
        self.app_name = "ClaudeUsageTray"
        self.config_dir = Path.home() / '.config' / self.app_name
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / 'config.json'
        self.config = self.load_config()
        self.usage_data = None
        self.polling_active = True
        self.driver = None
        self.login_in_progress = False
        self.indicator = AppIndicator3.Indicator.new(self.app_name, "", AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.menu = Gtk.Menu()
        self.indicator.set_menu(self.menu)
        self.icon_path = str(Path(tempfile.gettempdir()) / "claude_usage_tray_icon.png")
        self.build_menu()
        self.start_polling()
        self.initial_fetch_thread()
        Gtk.main()

    def load_config(self):
        default = {'session_key': None, 'cookie_string': None, 'poll_interval': 60}
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    return {**default, **data}
            except:
                pass
        return default

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def build_menu(self):
        self.menu.foreach(lambda w: self.menu.remove(w))
        five_item = Gtk.MenuItem(label=self.five_line())
        five_item.set_sensitive(False)
        self.menu.append(five_item)
        seven_item = Gtk.MenuItem(label=self.seven_line())
        seven_item.set_sensitive(False)
        self.menu.append(seven_item)
        self.menu.append(Gtk.SeparatorMenuItem())
        refresh_item = Gtk.MenuItem(label="Refresh now")
        refresh_item.connect("activate", lambda *_: self.manual_refresh())
        self.menu.append(refresh_item)
        logout_item = Gtk.MenuItem(label="Logout")
        logout_item.connect("activate", lambda *_: self.logout())
        self.menu.append(logout_item)
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda *_: self.quit_app())
        self.menu.append(quit_item)
        self.menu.show_all()

    def five_line(self):
        if not self.usage_data:
            return "5h: --"
        try:
            from dateutil import parser as date_parser
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dateutil"])
            from dateutil import parser as date_parser
        five = self.usage_data.get('five_hour', {})
        util = five.get('utilization', 0)
        ts = five.get('resets_at')
        hours = "--"
        if ts:
            dt = date_parser.parse(ts)
            now = datetime.now(dt.tzinfo)
            delta = dt - now
            if delta.total_seconds() > 0:
                hours = f"{int(delta.total_seconds()//3600)}h"
            else:
                hours = "soon"
        return f"5h: {util:.0f}% ({hours})"

    def seven_line(self):
        if not self.usage_data:
            return "7d: --"
        try:
            from dateutil import parser as date_parser
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dateutil"])
            from dateutil import parser as date_parser
        seven = self.usage_data.get('seven_day', {})
        util = seven.get('utilization', 0)
        ts = seven.get('resets_at')
        hours = "--"
        if ts:
            dt = date_parser.parse(ts)
            now = datetime.now(dt.tzinfo)
            delta = dt - now
            if delta.total_seconds() > 0:
                hours = f"{int(delta.total_seconds()//3600)}h"
            else:
                hours = "soon"
        return f"7d: {util:.0f}% ({hours})"

    def draw_icon(self):
        size = 64
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        ctx = cairo.Context(surface)
        ctx.set_source_rgba(0,0,0,0)
        ctx.paint()
        def color(util, primary):
            if util>=90:
                return (1,0.27,0.27)
            if util>=70:
                return (1,0.67,0.27)
            return primary
        five = self.usage_data.get('five_hour', {}) if self.usage_data else {}
        seven = self.usage_data.get('seven_day', {}) if self.usage_data else {}
        five_util = five.get('utilization',0)
        seven_util = seven.get('utilization',0)
        weekly_col = color(seven_util,(0.55,0.42,0.72))
        five_col = color(five_util,(0.8,0.47,0.36))
        ctx.set_line_width(8)
        ctx.arc(size/2, size/2, 28, -math.pi/2, -math.pi/2 + 2*math.pi*seven_util/100)
        ctx.set_source_rgb(*weekly_col)
        ctx.stroke()
        ctx.arc(size/2, size/2, 18, 0, 2*math.pi)
        ctx.set_source_rgb(0.12,0.12,0.12)
        ctx.fill()
        ctx.arc(size/2, size/2, 18, -math.pi/2, -math.pi/2 + 2*math.pi*five_util/100)
        ctx.set_source_rgb(*five_col)
        ctx.fill()
        ctx.select_font_face("Segoe UI", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(18)
        text = f"{int(five_util)}"
        xb,yb,w,h,xa,ya = ctx.text_extents(text)
        ctx.set_source_rgb(1,1,1)
        ctx.move_to(size/2 - w/2, size/2 + h/2)
        ctx.show_text(text)
        ctx.set_font_size(12)
        text2 = f"{int(seven_util)}"
        xb,yb,w,h,xa,ya = ctx.text_extents(text2)
        ctx.move_to(size/2 - w/2, size - 6)
        ctx.show_text(text2)
        surface.write_to_png(self.icon_path)
        self.indicator.set_icon_full(self.icon_path, "usage")

    def automated_browser_login(self, status_label):
        ensure_uc()
        try:
            import undetected_chromedriver as uc
            opts = uc.ChromeOptions()
            opts.add_argument('--start-maximized')
            opts.add_argument('--disable-dev-shm-usage')
            opts.add_argument('--no-sandbox')
            version_hint = chrome_version_main()
            try:
                self.driver = uc.Chrome(options=opts, use_subprocess=True, version_main=version_hint)
            except Exception:
                self.driver = uc.Chrome(options=opts, use_subprocess=True)
            GLib.idle_add(status_label.set_text, "Log in to claude.ai...")
            self.driver.get('https://claude.ai')
            time.sleep(3)
            session_key = None
            all_cookies = None
            max_wait = 300
            elapsed = 0
            while elapsed < max_wait and not session_key and self.login_in_progress:
                cookies = self.driver.get_cookies()
                for c in cookies:
                    if c['name'] == 'sessionKey':
                        session_key = c['value']
                        all_cookies = cookies
                        break
                try:
                    _ = self.driver.current_url
                except:
                    break
                time.sleep(2)
                elapsed += 2
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            if session_key:
                self.config['session_key'] = session_key
                if all_cookies:
                    cookie_string = '; '.join([f"{c['name']}={c['value']}" for c in all_cookies])
                    self.config['cookie_string'] = cookie_string
                self.save_config()
                GLib.idle_add(status_label.set_text, "Login successful")
                time.sleep(1)
                self.login_in_progress = False
                GLib.idle_add(self.login_dialog.response, Gtk.ResponseType.OK)
                GLib.idle_add(self.start_polling)
            else:
                GLib.idle_add(status_label.set_text, "Login cancelled/timeout")
                self.login_in_progress = False
        except Exception as e:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            GLib.idle_add(status_label.set_text, f"Error: {str(e)[:40]}")
            self.login_in_progress = False

    def show_login_dialog(self):
        self.login_dialog = Gtk.Dialog(title="Login Required", flags=Gtk.DialogFlags.MODAL)
        self.login_dialog.set_default_size(420,200)
        box = self.login_dialog.get_content_area()
        label = Gtk.Label(label="Sign in to Claude")
        label.set_markup("<span size='16000' foreground='#CC785C'><b>Sign in to Claude</b></span>")
        box.add(label)
        status_label = Gtk.Label(label="A browser window will open for login")
        status_label.set_markup("<span foreground='#999999'>A browser window will open for login</span>")
        box.add(status_label)
        btn = Gtk.Button(label="Sign In")
        btn.get_style_context().add_class("suggested-action")
        box.add(btn)
        cancel = Gtk.Button(label="Cancel")
        box.add(cancel)
        box.show_all()
        def start_login(_):
            if self.login_in_progress:
                return
            self.login_in_progress = True
            btn.set_sensitive(False)
            status_label.set_text("Launching browser...")
            threading.Thread(target=self.automated_browser_login, args=(status_label,), daemon=True).start()
        btn.connect("clicked", start_login)
        cancel.connect("clicked", lambda *_: self.login_dialog.response(Gtk.ResponseType.CANCEL))
        resp = self.login_dialog.run()
        self.login_dialog.destroy()
        if resp != Gtk.ResponseType.OK and not self.config.get('session_key'):
            self.quit_app()

    def fetch_usage_data(self):
        if not self.config.get('session_key'):
            return None
        try:
            ensure_cloudscraper()
            import cloudscraper
            scraper = cloudscraper.create_scraper(browser={'browser':'chrome','platform':'windows','mobile':False})
            cookie_string = self.config.get('cookie_string', f"sessionKey={self.config['session_key']}")
            headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36','Accept':'application/json','Accept-Language':'en-US,en;q=0.9','Referer':'https://claude.ai/chats','Sec-Fetch-Dest':'empty','Sec-Fetch-Mode':'cors','Sec-Fetch-Site':'same-origin','sec-ch-ua':'"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"','sec-ch-ua-mobile':'?0','sec-ch-ua-platform':'"Windows"'}
            for pair in cookie_string.split('; '):
                if '=' in pair:
                    n,v = pair.split('=',1)
                    scraper.cookies.set(n,v,domain='claude.ai')
            orgs = scraper.get('https://claude.ai/api/organizations', headers=headers, timeout=15)
            if orgs.status_code == 200:
                arr = orgs.json()
                if arr:
                    org_id = arr[0].get('uuid')
                    usage = scraper.get(f'https://claude.ai/api/organizations/{org_id}/usage', headers=headers, timeout=15)
                    if usage.status_code == 200:
                        return usage.json()
            elif orgs.status_code == 401:
                GLib.idle_add(self.handle_auth_error)
        except:
            return None
        return None

    def handle_auth_error(self):
        dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.YES_NO, text="Session expired. Log in again?")
        resp = dialog.run()
        dialog.destroy()
        if resp == Gtk.ResponseType.YES:
            self.config['session_key'] = None
            self.save_config()
            self.show_login_dialog()

    def polling_loop(self):
        while self.polling_active:
            data = self.fetch_usage_data()
            if data:
                self.usage_data = data
                GLib.idle_add(self.after_update)
            time.sleep(self.config['poll_interval'])

    def start_polling(self):
        if not self.config.get('session_key'):
            self.show_login_dialog()
            if not self.config.get('session_key'):
                return
        if not getattr(self, 'poll_thread', None):
            self.poll_thread = threading.Thread(target=self.polling_loop, daemon=True)
            self.poll_thread.start()

    def initial_fetch_thread(self):
        def initial():
            time.sleep(0.5)
            data = self.fetch_usage_data()
            if data:
                self.usage_data = data
                GLib.idle_add(self.after_update)
        threading.Thread(target=initial, daemon=True).start()

    def after_update(self):
        self.build_menu()
        if self.usage_data:
            self.draw_icon()

    def manual_refresh(self):
        def r():
            data = self.fetch_usage_data()
            if data:
                self.usage_data = data
                GLib.idle_add(self.after_update)
        threading.Thread(target=r, daemon=True).start()

    def logout(self):
        self.config['session_key'] = None
        self.config['cookie_string'] = None
        self.save_config()
        self.polling_active = False
        self.show_login_dialog()
        if not self.config.get('session_key'):
            self.quit_app()
        else:
            self.polling_active = True
            self.poll_thread = None
            self.start_polling()

    def quit_app(self):
        self.polling_active = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        Gtk.main_quit()

if __name__ == "__main__":
    ClaudeUsageTray()
