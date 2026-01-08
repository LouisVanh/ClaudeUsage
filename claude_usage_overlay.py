import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import requests
from datetime import datetime
from pathlib import Path
import threading
import time
import sys

class ClaudeUsageBar:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Claude Usage")
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        
        # Paths
        self.app_data_dir = Path(os.getenv('APPDATA')) / 'ClaudeUsageBar'
        self.app_data_dir.mkdir(exist_ok=True)
        self.config_file = self.app_data_dir / 'config.json'
        
        # Load config
        self.config = self.load_config()
        
        # State
        self.dragging = False
        self.drag_x = 0
        self.drag_y = 0
        self.usage_data = None
        self.polling_active = True
        self.driver = None
        self.login_in_progress = False
        
        # Setup UI
        self.setup_ui()
        self.position_window()
        
        # Check if we have auth token
        if not self.config.get('session_key'):
            self.root.after(500, self.show_login_dialog)
        else:
            self.start_polling()
        
    def load_config(self):
        default = {
            'position': {'x': 20, 'y': 80},
            'opacity': 0.9,
            'session_key': None,
            'poll_interval': 60
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    return {**default, **loaded}
            except:
                pass
        
        return default
    
    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def show_login_dialog(self):
        """Show login dialog"""
        self.login_dialog = tk.Toplevel(self.root)
        self.login_dialog.title("Login Required")
        self.login_dialog.geometry("420x200")
        self.login_dialog.configure(bg='#1a1a1a')
        self.login_dialog.attributes('-topmost', True)
        self.login_dialog.protocol("WM_DELETE_WINDOW", self.on_login_dialog_close)
        
        # Center
        self.login_dialog.update_idletasks()
        x = (self.login_dialog.winfo_screenwidth() // 2) - 210
        y = (self.login_dialog.winfo_screenheight() // 2) - 100
        self.login_dialog.geometry(f'+{x}+{y}')
        
        tk.Label(
            self.login_dialog,
            text="🔐 Sign in to Claude",
            font=('Segoe UI', 16, 'bold'),
            fg='#CC785C',
            bg='#1a1a1a'
        ).pack(pady=(25, 10))
        
        self.status_label = tk.Label(
            self.login_dialog,
            text="A browser window will open for login",
            font=('Segoe UI', 9),
            fg='#999999',
            bg='#1a1a1a'
        )
        self.status_label.pack(pady=10)
        
        def start_login():
            if self.login_in_progress:
                return
                
            self.login_button.config(state='disabled', text="Opening browser...")
            self.status_label.config(text="Launching browser...", fg='#ffaa44')
            self.login_dialog.update()
            
            # Launch browser in background thread
            self.login_in_progress = True
            threading.Thread(
                target=self.automated_browser_login,
                daemon=True
            ).start()
        
        self.login_button = tk.Button(
            self.login_dialog,
            text="Sign In",
            command=start_login,
            bg='#CC785C',
            fg='#ffffff',
            font=('Segoe UI', 11, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=50,
            pady=12
        )
        self.login_button.pack(pady=15)
        
        # Cancel button
        cancel_btn = tk.Button(
            self.login_dialog,
            text="Cancel",
            command=self.on_login_dialog_close,
            bg='#3a3a3a',
            fg='#cccccc',
            font=('Segoe UI', 9),
            relief='flat',
            cursor='hand2',
            padx=30,
            pady=6
        )
        cancel_btn.pack()
    
    def on_login_dialog_close(self):
        """Handle login dialog close"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        
        self.login_in_progress = False
        
        if hasattr(self, 'login_dialog'):
            try:
                self.login_dialog.destroy()
            except:
                pass
        
        # If no session key, quit the app
        if not self.config.get('session_key'):
            self.root.quit()
    
    def automated_browser_login(self):
        """Open browser with undetected-chromedriver to bypass Cloudflare"""
        try:
            # Import undetected_chromedriver
            try:
                import undetected_chromedriver as uc
            except ImportError:
                self.root.after(0, lambda: [
                    self.status_label.config(
                        text="Installing undetected-chromedriver...",
                        fg='#ffaa44'
                    )
                ])
                # Try to install it
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "undetected-chromedriver"])
                import undetected_chromedriver as uc
            
            self.root.after(0, lambda: self.status_label.config(
                text="Starting browser (bypassing Cloudflare)...",
                fg='#ffaa44'
            ))
            
            # Create undetected Chrome driver
            options = uc.ChromeOptions()
            options.add_argument('--start-maximized')
            
            try:
                self.driver = uc.Chrome(options=options, use_subprocess=True)
            except Exception as e:
                self.root.after(0, lambda: [
                    self.status_label.config(
                        text=f"Browser error: {str(e)[:40]}",
                        fg='#ff4444'
                    ),
                    self.login_button.config(state='normal', text="Sign In")
                ])
                self.login_in_progress = False
                return
            
            # Navigate to Claude
            self.root.after(0, lambda: self.status_label.config(
                text="Please log in to claude.ai in the browser...",
                fg='#ffaa44'
            ))
            
            self.driver.get('https://claude.ai')
            
            # Give it a moment to load
            time.sleep(3)
            
            # Wait for user to log in
            session_key = None
            all_cookies = None
            max_wait = 300  # 5 minutes
            elapsed = 0
            
            print("Waiting for sessionKey cookie...")
            
            while elapsed < max_wait and not session_key and self.login_in_progress:
                try:
                    # Check cookies
                    cookies = self.driver.get_cookies()
                    print(f"[{elapsed}s] Checking cookies... Found {len(cookies)} cookies")
                    
                    # Print all cookie names for debugging
                    cookie_names = [c['name'] for c in cookies]
                    print(f"Cookie names: {cookie_names}")
                    
                    for cookie in cookies:
                        if cookie['name'] == 'sessionKey':
                            session_key = cookie['value']
                            all_cookies = cookies  # Save ALL cookies
                            print(f"✓ Found sessionKey: {session_key[:20]}...")
                            print(f"Captured {len(all_cookies)} total cookies")
                            break
                    
                    if session_key:
                        break
                    
                    # Check if browser was closed by user
                    try:
                        url = self.driver.current_url
                        print(f"Current URL: {url}")
                    except Exception as url_error:
                        print(f"Browser closed by user: {url_error}")
                        break
                    
                    time.sleep(2)
                    elapsed += 2
                    
                except Exception as e:
                    print(f"Error checking cookies: {e}")
                    import traceback
                    traceback.print_exc()
                    break
            
            print(f"Cookie check loop ended. Session key found: {session_key is not None}")
            
            # Close browser
            if self.driver:
                try:
                    print("Closing browser...")
                    self.driver.quit()
                    print("Browser closed successfully")
                except Exception as quit_error:
                    print(f"Error closing browser: {quit_error}")
                finally:
                    self.driver = None
            
            if session_key:
                # Success! Save session key AND all cookies
                print(f"Saving session key: {session_key[:20]}...")
                self.config['session_key'] = session_key
                
                # Save all cookies as a cookie string
                if all_cookies:
                    cookie_string = '; '.join([f"{c['name']}={c['value']}" for c in all_cookies])
                    self.config['cookie_string'] = cookie_string
                    print(f"Saved {len(all_cookies)} cookies")
                
                self.save_config()
                print("Config saved!")
                
                self.root.after(0, lambda: [
                    self.status_label.config(text="✓ Login successful!", fg='#44ff44'),
                ])
                
                # Close dialog and start polling
                time.sleep(1)
                self.root.after(0, lambda: [
                    self.login_dialog.destroy() if hasattr(self, 'login_dialog') else None,
                    self.start_polling()
                ])
                print("Starting polling...")
            else:
                # Timeout or closed
                print("No session key found - login cancelled or timeout")
                self.root.after(0, lambda: [
                    self.status_label.config(text="Login cancelled or timeout. Try again.", fg='#ff4444'),
                    self.login_button.config(state='normal', text="Sign In")
                ])
            
            self.login_in_progress = False
            print("Login process complete")
        
        except Exception as e:
            print(f"Login error: {e}")
            import traceback
            traceback.print_exc()
            
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            
            self.root.after(0, lambda: [
                self.status_label.config(text=f"Error: {str(e)[:40]}", fg='#ff4444'),
                self.login_button.config(state='normal', text="Sign In")
            ])
            self.login_in_progress = False
    
    def fetch_usage_data(self):
        """Fetch usage data from Claude API using requests with cloudflare bypass"""
        if not self.config.get('session_key'):
            print("No session key available")
            return None
            
        try:
            # Use cloudscraper to bypass Cloudflare
            try:
                import cloudscraper
            except ImportError:
                print("Installing cloudscraper...")
                import subprocess
                import sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "cloudscraper"])
                import cloudscraper
            
            # Create a scraper that bypasses Cloudflare
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'mobile': False
                }
            )
            
            # Use full cookie string if available
            cookie_string = self.config.get('cookie_string', f'sessionKey={self.config["session_key"]}')
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://claude.ai/chats',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
            }
            
            # Set cookies
            for cookie_pair in cookie_string.split('; '):
                if '=' in cookie_pair:
                    name, value = cookie_pair.split('=', 1)
                    scraper.cookies.set(name, value, domain='claude.ai')
            
            print("Fetching organizations with cloudscraper...")
            # Get organizations
            response = scraper.get(
                'https://claude.ai/api/organizations',
                headers=headers,
                timeout=15
            )
            
            print(f"Organizations response: {response.status_code}")
            
            if response.status_code == 200:
                orgs = response.json()
                print(f"Found {len(orgs)} organizations")
                
                if orgs and len(orgs) > 0:
                    org_id = orgs[0].get('uuid')
                    print(f"Using org: {org_id}")
                    
                    # Get usage
                    print("Fetching usage data...")
                    usage_response = scraper.get(
                        f'https://claude.ai/api/organizations/{org_id}/usage',
                        headers=headers,
                        timeout=15
                    )
                    
                    print(f"Usage response: {usage_response.status_code}")
                    
                    if usage_response.status_code == 200:
                        usage_data = usage_response.json()
                        print(f"Usage data: {usage_data}")
                        return usage_data
            
            elif response.status_code == 401:
                print("Session expired (401)")
                self.root.after(0, self.handle_auth_error)
                return None
            elif response.status_code == 403:
                print("Forbidden (403)")
                print(f"Response snippet: {response.text[:500]}")
                return None
            
            print("No usage data available")
            return None
                
        except Exception as e:
            print(f"Error fetching usage: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def handle_auth_error(self):
        """Handle authentication errors"""
        if messagebox.askyesno("Session Expired", 
                               "Your session has expired. Would you like to log in again?"):
            self.config['session_key'] = None
            self.save_config()
            self.show_login_dialog()
    
    def polling_loop(self):
        """Background thread for polling API"""
        while self.polling_active:
            data = self.fetch_usage_data()
            if data:
                self.usage_data = data
                self.root.after(0, self.update_progress)
            
            time.sleep(self.config['poll_interval'])
    
    def start_polling(self):
        """Start background polling thread"""
        self.polling_active = True
        poll_thread = threading.Thread(target=self.polling_loop, daemon=True)
        poll_thread.start()
        
        # Initial fetch
        def initial_fetch():
            time.sleep(0.5)
            data = self.fetch_usage_data()
            if data:
                self.usage_data = data
                self.root.after(0, self.update_progress)
        
        threading.Thread(target=initial_fetch, daemon=True).start()
    
    def setup_ui(self):
        self.main_frame = tk.Frame(
            self.root,
            bg='#1a1a1a',
            relief='flat',
            bd=0
        )
        self.main_frame.pack(fill='both', expand=True, padx=1, pady=1)
        
        self.root.configure(bg='#1a1a1a')
        
        # Header
        self.header = tk.Frame(self.main_frame, bg='#2a2a2a', height=28)
        self.header.pack(fill='x', padx=6, pady=(6, 0))
        self.header.pack_propagate(False)
        
        self.title_label = tk.Label(
            self.header,
            text="Claude Usage",
            font=('Segoe UI', 9, 'bold'),
            fg='#CC785C',
            bg='#2a2a2a',
            cursor='hand2'
        )
        self.title_label.pack(side='left', padx=8, pady=4)
        
        # Dragging
        for widget in [self.header, self.title_label]:
            widget.bind('<Button-1>', self.start_drag)
            widget.bind('<B1-Motion>', self.on_drag)
            widget.bind('<ButtonRelease-1>', self.stop_drag)
        
        # Buttons
        btn_frame = tk.Frame(self.header, bg='#2a2a2a')
        btn_frame.pack(side='right')
        
        # Refresh
        self.refresh_btn = tk.Label(
            btn_frame,
            text="⟳",
            font=('Segoe UI', 11, 'bold'),
            fg='#888888',
            bg='#2a2a2a',
            cursor='hand2',
            padx=4
        )
        self.refresh_btn.pack(side='left', padx=2)
        self.refresh_btn.bind('<Button-1>', self.manual_refresh)
        self.refresh_btn.bind('<Enter>', lambda e: self.refresh_btn.config(fg='#CC785C'))
        self.refresh_btn.bind('<Leave>', lambda e: self.refresh_btn.config(fg='#888888'))
        
        # Settings
        self.settings_btn = tk.Label(
            btn_frame,
            text="⚙",
            font=('Segoe UI', 10),
            fg='#888888',
            bg='#2a2a2a',
            cursor='hand2',
            padx=4
        )
        self.settings_btn.pack(side='left', padx=2)
        self.settings_btn.bind('<Button-1>', self.show_settings)
        self.settings_btn.bind('<Enter>', lambda e: self.settings_btn.config(fg='#ffffff'))
        self.settings_btn.bind('<Leave>', lambda e: self.settings_btn.config(fg='#888888'))
        
        # Close
        self.close_btn = tk.Label(
            btn_frame,
            text="×",
            font=('Segoe UI', 13, 'bold'),
            fg='#888888',
            bg='#2a2a2a',
            cursor='hand2',
            padx=4
        )
        self.close_btn.pack(side='left', padx=2)
        self.close_btn.bind('<Button-1>', self.on_close)
        self.close_btn.bind('<Enter>', lambda e: self.close_btn.config(fg='#ff4444'))
        self.close_btn.bind('<Leave>', lambda e: self.close_btn.config(fg='#888888'))
        
        # Content
        content = tk.Frame(self.main_frame, bg='#1a1a1a')
        content.pack(fill='x', padx=8, pady=8)
        
        # Usage section
        tk.Label(
            content,
            text="Current Usage",
            font=('Segoe UI', 8, 'bold'),
            fg='#888888',
            bg='#1a1a1a',
            anchor='w'
        ).pack(fill='x', pady=(0, 2))
        
        self.usage_label = tk.Label(
            content,
            text="Loading...",
            font=('Segoe UI', 9),
            fg='#cccccc',
            bg='#1a1a1a',
            anchor='w'
        )
        self.usage_label.pack(fill='x', pady=(0, 2))
        
        # Progress bar
        progress_bg = tk.Frame(content, bg='#2a2a2a', height=12)
        progress_bg.pack(fill='x', pady=(0, 4))
        progress_bg.pack_propagate(False)
        
        self.progress_fill = tk.Frame(progress_bg, bg='#CC785C', height=12)
        self.progress_fill.place(x=0, y=0, relheight=1, width=0)
        
        self.reset_label = tk.Label(
            content,
            text="Next reset: --:--:--",
            font=('Segoe UI', 7),
            fg='#666666',
            bg='#1a1a1a',
            anchor='w'
        )
        self.reset_label.pack(fill='x')
        
        # Set opacity
        self.root.attributes('-alpha', self.config['opacity'])
        self.root.geometry('300x140')
    
    def start_drag(self, event):
        self.dragging = True
        self.drag_x = event.x_root - self.root.winfo_x()
        self.drag_y = event.y_root - self.root.winfo_y()
    
    def on_drag(self, event):
        if self.dragging:
            x = event.x_root - self.drag_x
            y = event.y_root - self.drag_y
            self.root.geometry(f'+{x}+{y}')
    
    def stop_drag(self, event):
        if self.dragging:
            self.dragging = False
            self.config['position']['x'] = self.root.winfo_x()
            self.config['position']['y'] = self.root.winfo_y()
            self.save_config()
    
    def position_window(self):
        self.root.update_idletasks()
        x = self.config['position']['x']
        y = self.config['position']['y']
        self.root.geometry(f'+{x}+{y}')
    
    def update_progress(self):
        """Update UI with latest usage data"""
        if not self.usage_data:
            return
        
        try:
            # Extract 5-hour usage
            five_hour = self.usage_data.get('five_hour', {})
            utilization = five_hour.get('utilization', 0.0)
            resets_at = five_hour.get('resets_at')
            
            # Display usage
            self.usage_label.config(text=f"{utilization:.1f}% of limit used")
            
            # Update progress bar
            bar_width = int((utilization / 100) * 284)
            self.progress_fill.place(width=bar_width)
            
            # Color based on usage
            if utilization >= 90:
                self.progress_fill.config(bg='#ff4444')
            elif utilization >= 70:
                self.progress_fill.config(bg='#ffaa44')
            else:
                self.progress_fill.config(bg='#CC785C')
            
            # Update reset timer
            if resets_at:
                try:
                    from dateutil import parser
                    reset_time = parser.parse(resets_at)
                    now = datetime.now(reset_time.tzinfo)
                    time_left = reset_time - now
                    
                    if time_left.total_seconds() > 0:
                        hours = int(time_left.total_seconds() // 3600)
                        minutes = int((time_left.total_seconds() % 3600) // 60)
                        seconds = int(time_left.total_seconds() % 60)
                        self.reset_label.config(text=f"Resets in: {hours:02d}:{minutes:02d}:{seconds:02d}")
                    else:
                        self.reset_label.config(text="Resetting soon...")
                except:
                    self.reset_label.config(text=f"Resets at: {resets_at}")
            else:
                # No active limit period
                if utilization == 0:
                    self.reset_label.config(text="No usage in current period")
                else:
                    self.reset_label.config(text="Resets: Not available")
                
        except Exception as e:
            print(f"Error updating progress: {e}")
            import traceback
            traceback.print_exc()
            self.usage_label.config(text="Error displaying usage")
        
        # Schedule next update
        self.root.after(1000, self.update_progress)
    
    def manual_refresh(self, event=None):
        """Manually trigger refresh"""
        def refresh():
            data = self.fetch_usage_data()
            if data:
                self.usage_data = data
                self.root.after(0, self.update_progress)
        
        threading.Thread(target=refresh, daemon=True).start()
    
    def show_settings(self, event=None):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("350x320")
        settings_win.attributes('-topmost', True)
        settings_win.configure(bg='#1a1a1a')
        
        # Account info
        tk.Label(
            settings_win,
            text="Account",
            font=('Segoe UI', 9, 'bold'),
            fg='#888888',
            bg='#1a1a1a'
        ).pack(pady=(15, 5))
        
        # Show session key snippet
        session_key = self.config.get('session_key', 'Not logged in')
        display_key = f"{session_key[:15]}..." if len(session_key) > 15 else session_key
        
        tk.Label(
            settings_win,
            text=f"Session: {display_key}",
            font=('Segoe UI', 8),
            fg='#666666',
            bg='#1a1a1a'
        ).pack()
        
        # Opacity
        tk.Label(
            settings_win,
            text="Opacity:",
            font=('Segoe UI', 9),
            fg='#cccccc',
            bg='#1a1a1a'
        ).pack(pady=(15, 5))
        
        opacity_var = tk.DoubleVar(value=self.config['opacity'])
        opacity_slider = ttk.Scale(
            settings_win,
            from_=0.3,
            to=1.0,
            variable=opacity_var,
            orient='horizontal',
            length=250
        )
        opacity_slider.pack()
        
        # Poll interval
        tk.Label(
            settings_win,
            text="Update Interval (seconds):",
            font=('Segoe UI', 9),
            fg='#cccccc',
            bg='#1a1a1a'
        ).pack(pady=(15, 5))
        
        interval_var = tk.IntVar(value=self.config['poll_interval'])
        interval_spinbox = tk.Spinbox(
            settings_win,
            from_=10,
            to=300,
            textvariable=interval_var,
            font=('Segoe UI', 10),
            bg='#2a2a2a',
            fg='#ffffff',
            width=10
        )
        interval_spinbox.pack()
        
        # Save
        def save_settings():
            self.config['opacity'] = opacity_var.get()
            self.config['poll_interval'] = interval_var.get()
            self.root.attributes('-alpha', self.config['opacity'])
            self.save_config()
            settings_win.destroy()
        
        tk.Button(
            settings_win,
            text="Save Settings",
            command=save_settings,
            bg='#CC785C',
            fg='#ffffff',
            relief='flat',
            font=('Segoe UI', 9, 'bold'),
            padx=20,
            pady=6
        ).pack(pady=15)
        
        # Logout
        def logout():
            if messagebox.askyesno("Logout", "Log out and clear session?", parent=settings_win):
                self.config['session_key'] = None
                self.config['cookie_string'] = None
                self.save_config()
                settings_win.destroy()
                messagebox.showinfo("Logged Out", "Please restart the app to log in again.")
                self.root.quit()
        
        tk.Button(
            settings_win,
            text="🚪 Logout & Clear Session",
            command=logout,
            bg='#3a3a3a',
            fg='#ff8888',
            relief='flat',
            font=('Segoe UI', 9),
            padx=20,
            pady=6
        ).pack()
    
    def on_close(self, event=None):
        self.polling_active = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.root.quit()
    
    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = ClaudeUsageBar()
    app.run()