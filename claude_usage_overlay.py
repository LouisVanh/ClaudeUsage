import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import requests
from datetime import datetime
from pathlib import Path
import threading
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import webview

class ClaudeUsageBar:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Claude Usage")
        self.root.attributes('-topmost', True)
        self.root.attributes('-transparentcolor', '#000001')
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
        self.login_window = None
        
        # Check if we have auth token
        if not self.config.get('session_key'):
            self.show_login()
        
        # Setup UI
        self.setup_ui()
        self.position_window()
        
        # Start polling in background thread
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
    
    def show_login(self):
        """Show login window with embedded browser"""
        login_win = tk.Toplevel(self.root)
        login_win.title("Login to Claude")
        login_win.geometry("500x300")
        login_win.configure(bg='#1a1a1a')
        login_win.attributes('-topmost', True)
        login_win.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Center
        login_win.update_idletasks()
        x = (login_win.winfo_screenwidth() // 2) - 250
        y = (login_win.winfo_screenheight() // 2) - 150
        login_win.geometry(f'+{x}+{y}')
        
        tk.Label(
            login_win,
            text="Claude Usage Tracker",
            font=('Segoe UI', 16, 'bold'),
            fg='#CC785C',
            bg='#1a1a1a'
        ).pack(pady=(30, 10))
        
        tk.Label(
            login_win,
            text="Click below to sign in with your Claude account",
            font=('Segoe UI', 10),
            fg='#999999',
            bg='#1a1a1a'
        ).pack(pady=(0, 30))
        
        status_label = tk.Label(
            login_win,
            text="",
            font=('Segoe UI', 9),
            fg='#ffaa44',
            bg='#1a1a1a'
        )
        status_label.pack(pady=10)
        
        def start_login():
            login_btn.config(state='disabled', text="Opening browser...")
            status_label.config(text="Please log in to claude.ai in the browser window")
            login_win.update()
            
            # Launch browser-based login
            threading.Thread(target=lambda: self.browser_login(login_win, status_label, login_btn), daemon=True).start()
        
        login_btn = tk.Button(
            login_win,
            text="Sign In with Claude",
            command=start_login,
            bg='#CC785C',
            fg='#ffffff',
            font=('Segoe UI', 11, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=40,
            pady=12
        )
        login_btn.pack(pady=10)
        
        tk.Label(
            login_win,
            text="Your credentials are stored securely on your device",
            font=('Segoe UI', 7),
            fg='#666666',
            bg='#1a1a1a'
        ).pack(pady=(20, 0))
        
        login_win.wait_window()
    
    def browser_login(self, login_win, status_label, login_btn):
        """Open browser window for login and capture session"""
        try:
            # Create a webview window
            self.login_window = webview.create_window(
                'Sign in to Claude',
                'https://claude.ai',
                width=900,
                height=700
            )
            
            # Monitor for cookies
            def check_cookies():
                while self.login_window:
                    try:
                        # Get cookies from webview
                        cookies = self.login_window.get_cookies()
                        
                        # Look for sessionKey
                        for cookie in cookies:
                            if cookie.get('name') == 'sessionKey' and 'claude.ai' in cookie.get('domain', ''):
                                session_key = cookie.get('value')
                                if session_key:
                                    # Found it!
                                    self.config['session_key'] = session_key
                                    self.save_config()
                                    
                                    # Update UI in main thread
                                    login_win.after(0, lambda: [
                                        status_label.config(text="✓ Login successful!", fg='#44ff44'),
                                        login_win.after(1000, login_win.destroy)
                                    ])
                                    
                                    # Close browser
                                    self.login_window.destroy()
                                    self.login_window = None
                                    return
                        
                        time.sleep(1)
                    except:
                        break
            
            # Start cookie monitoring in background
            threading.Thread(target=check_cookies, daemon=True).start()
            
            # Start webview (blocking call)
            webview.start()
            
        except Exception as e:
            login_win.after(0, lambda: [
                status_label.config(text=f"Error: {str(e)}", fg='#ff4444'),
                login_btn.config(state='normal', text="Sign In with Claude")
            ])
    
    def fetch_usage_data(self):
        """Fetch usage data from Claude API"""
        try:
            # Use claude.ai's internal API
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Cookie': f'sessionKey={self.config["session_key"]}',
                'Origin': 'https://claude.ai',
                'Referer': 'https://claude.ai/'
            }
            
            # Try to get account info and usage
            response = requests.get(
                'https://claude.ai/api/organizations',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                orgs = response.json()
                if orgs and len(orgs) > 0:
                    org_id = orgs[0].get('uuid')
                    
                    # Get usage for this org
                    usage_response = requests.get(
                        f'https://claude.ai/api/organizations/{org_id}/usage',
                        headers=headers,
                        timeout=10
                    )
                    
                    if usage_response.status_code == 200:
                        return usage_response.json()
            
            elif response.status_code == 401:
                self.root.after(0, self.handle_auth_error)
                return None
            
            return None
                
        except Exception as e:
            print(f"Error fetching usage: {e}")
            return None
    
    def handle_auth_error(self):
        """Handle authentication errors"""
        if messagebox.askyesno("Session Expired", 
                               "Your session has expired. Would you like to log in again?"):
            self.config['session_key'] = None
            self.save_config()
            self.show_login()
            self.start_polling()
    
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
        threading.Thread(target=lambda: [
            time.sleep(0.5),
            setattr(self, 'usage_data', self.fetch_usage_data()),
            self.root.after(0, self.update_progress)
        ], daemon=True).start()
    
    def setup_ui(self):
        self.main_frame = tk.Frame(
            self.root,
            bg='#1a1a1a',
            relief='flat',
            bd=0
        )
        self.main_frame.pack(fill='both', expand=True, padx=1, pady=1)
        
        self.root.configure(bg='#000001')
        
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
        
        # Parse usage data (structure varies by API response)
        # This is a simplified version - adjust based on actual API response
        try:
            if 'usage_data' in self.usage_data:
                usage_pct = self.usage_data['usage_data'].get('percentage', 0)
                self.usage_label.config(text=f"{usage_pct:.1f}% of limit used")
                
                # Update progress bar
                bar_width = int((usage_pct / 100) * 284)
                self.progress_fill.place(width=bar_width)
                
                # Color based on usage
                if usage_pct >= 90:
                    self.progress_fill.config(bg='#ff4444')
                elif usage_pct >= 70:
                    self.progress_fill.config(bg='#ffaa44')
                else:
                    self.progress_fill.config(bg='#CC785C')
            else:
                self.usage_label.config(text="Usage data available")
        except Exception as e:
            print(f"Error updating progress: {e}")
        
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
        settings_win.geometry("350x250")
        settings_win.attributes('-topmost', True)
        settings_win.configure(bg='#1a1a1a')
        
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
        ).pack(pady=20)
        
        # Logout
        def logout():
            if messagebox.askyesno("Logout", "Log out and clear session?", parent=settings_win):
                self.config['session_key'] = None
                self.save_config()
                settings_win.destroy()
                self.root.quit()
        
        tk.Button(
            settings_win,
            text="Logout",
            command=logout,
            bg='#2a2a2a',
            fg='#888888',
            relief='flat',
            font=('Segoe UI', 8)
        ).pack()
    
    def on_close(self, event=None):
        self.polling_active = False
        if self.login_window:
            try:
                self.login_window.destroy()
            except:
                pass
        self.root.quit()
    
    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = ClaudeUsageBar()
    app.run()