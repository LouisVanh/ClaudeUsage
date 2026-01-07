import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

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
        
        # Check if logged in
        if not self.config.get('logged_in'):
            self.show_login()
        
        # Setup UI
        self.setup_ui()
        self.position_window()
        
        # Start updates
        self.update_progress()
        self.schedule_update()
        
    def load_config(self):
        default = {
            'position': {'x': 20, 'y': 80},
            'opacity': 0.9,
            'logged_in': False,
            'api_key': '',
            'current_usage': 0,
            'usage_limit': 100,
            'reset_time': None,
            'plan_type': 'free'  # free, pro, team
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
        login_win = tk.Toplevel(self.root)
        login_win.title("Login to Claude")
        login_win.geometry("400x300")
        login_win.configure(bg='#1a1a1a')
        login_win.attributes('-topmost', True)
        
        # Center window
        login_win.update_idletasks()
        x = (login_win.winfo_screenwidth() // 2) - (400 // 2)
        y = (login_win.winfo_screenheight() // 2) - (300 // 2)
        login_win.geometry(f'+{x}+{y}')
        
        tk.Label(
            login_win,
            text="Claude Usage Tracker",
            font=('Segoe UI', 16, 'bold'),
            fg='#CC785C',
            bg='#1a1a1a'
        ).pack(pady=(20, 10))
        
        tk.Label(
            login_win,
            text="Enter your Claude session details",
            font=('Segoe UI', 9),
            fg='#999999',
            bg='#1a1a1a'
        ).pack(pady=(0, 20))
        
        # Plan type
        tk.Label(
            login_win,
            text="Plan Type:",
            font=('Segoe UI', 9),
            fg='#cccccc',
            bg='#1a1a1a'
        ).pack(pady=(10, 5))
        
        plan_var = tk.StringVar(value='free')
        plan_frame = tk.Frame(login_win, bg='#1a1a1a')
        plan_frame.pack()
        
        for plan in [('Free', 'free'), ('Pro', 'pro'), ('Team', 'team')]:
            tk.Radiobutton(
                plan_frame,
                text=plan[0],
                variable=plan_var,
                value=plan[1],
                bg='#1a1a1a',
                fg='#cccccc',
                selectcolor='#2a2a2a',
                font=('Segoe UI', 9)
            ).pack(side='left', padx=10)
        
        # Current usage
        tk.Label(
            login_win,
            text="Current Messages Used:",
            font=('Segoe UI', 9),
            fg='#cccccc',
            bg='#1a1a1a'
        ).pack(pady=(15, 5))
        
        usage_entry = tk.Entry(
            login_win,
            font=('Segoe UI', 10),
            bg='#2a2a2a',
            fg='#ffffff',
            insertbackground='#ffffff',
            relief='flat',
            width=15
        )
        usage_entry.pack()
        usage_entry.insert(0, "0")
        
        def login():
            plan = plan_var.get()
            try:
                usage = int(usage_entry.get())
            except:
                messagebox.showerror("Error", "Please enter a valid number")
                return
            
            # Set limits based on plan
            limits = {
                'free': 50,      # Free tier gets ~50 messages per 5 hours
                'pro': 500,      # Pro gets ~500 messages per 5 hours  
                'team': 1000     # Team gets higher limits
            }
            
            self.config['logged_in'] = True
            self.config['plan_type'] = plan
            self.config['current_usage'] = usage
            self.config['usage_limit'] = limits[plan]
            
            # Set reset time (5 hours from now for most plans)
            reset_hours = 5
            self.config['reset_time'] = (datetime.now() + timedelta(hours=reset_hours)).isoformat()
            
            self.save_config()
            login_win.destroy()
        
        tk.Button(
            login_win,
            text="Start Tracking",
            command=login,
            bg='#CC785C',
            fg='#ffffff',
            font=('Segoe UI', 10, 'bold'),
            relief='flat',
            cursor='hand2',
            padx=30,
            pady=8
        ).pack(pady=20)
        
        login_win.wait_window()
    
    def setup_ui(self):
        # Main container with Claude's color scheme
        self.main_frame = tk.Frame(
            self.root,
            bg='#1a1a1a',
            relief='flat',
            bd=0
        )
        self.main_frame.pack(fill='both', expand=True, padx=1, pady=1)
        
        self.root.configure(bg='#000001')
        
        # Header bar
        self.header = tk.Frame(self.main_frame, bg='#2a2a2a', height=28)
        self.header.pack(fill='x', padx=6, pady=(6, 0))
        self.header.pack_propagate(False)
        
        # Claude icon/title
        self.title_label = tk.Label(
            self.header,
            text="Claude",
            font=('Segoe UI', 9, 'bold'),
            fg='#CC785C',
            bg='#2a2a2a',
            cursor='hand2'
        )
        self.title_label.pack(side='left', padx=8, pady=4)
        
        # Bind dragging
        self.header.bind('<Button-1>', self.start_drag)
        self.header.bind('<B1-Motion>', self.on_drag)
        self.header.bind('<ButtonRelease-1>', self.stop_drag)
        self.title_label.bind('<Button-1>', self.start_drag)
        self.title_label.bind('<B1-Motion>', self.on_drag)
        
        # Buttons
        btn_frame = tk.Frame(self.header, bg='#2a2a2a')
        btn_frame.pack(side='right')
        
        # Increment button
        self.inc_btn = tk.Label(
            btn_frame,
            text="+",
            font=('Segoe UI', 11, 'bold'),
            fg='#888888',
            bg='#2a2a2a',
            cursor='hand2',
            padx=4
        )
        self.inc_btn.pack(side='left', padx=2)
        self.inc_btn.bind('<Button-1>', self.increment_usage)
        self.inc_btn.bind('<Enter>', lambda e: self.inc_btn.config(fg='#CC785C'))
        self.inc_btn.bind('<Leave>', lambda e: self.inc_btn.config(fg='#888888'))
        
        # Settings button
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
        
        # Close button
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
        self.close_btn.bind('<Button-1>', lambda e: self.root.quit())
        self.close_btn.bind('<Enter>', lambda e: self.close_btn.config(fg='#ff4444'))
        self.close_btn.bind('<Leave>', lambda e: self.close_btn.config(fg='#888888'))
        
        # Progress bar container
        progress_container = tk.Frame(self.main_frame, bg='#1a1a1a')
        progress_container.pack(fill='x', padx=8, pady=8)
        
        # Usage text
        self.usage_label = tk.Label(
            progress_container,
            text="0 / 100 messages",
            font=('Segoe UI', 8),
            fg='#888888',
            bg='#1a1a1a',
            anchor='w'
        )
        self.usage_label.pack(fill='x', pady=(0, 4))
        
        # Progress bar background
        progress_bg = tk.Frame(progress_container, bg='#2a2a2a', height=8)
        progress_bg.pack(fill='x')
        progress_bg.pack_propagate(False)
        
        # Progress bar fill (Claude's orange/copper color)
        self.progress_fill = tk.Frame(progress_bg, bg='#CC785C', height=8)
        self.progress_fill.place(x=0, y=0, relheight=1, width=0)
        
        # Reset timer
        self.reset_label = tk.Label(
            progress_container,
            text="Resets in: --:--:--",
            font=('Segoe UI', 7),
            fg='#666666',
            bg='#1a1a1a',
            anchor='w'
        )
        self.reset_label.pack(fill='x', pady=(4, 0))
        
        # Set opacity
        self.root.attributes('-alpha', self.config['opacity'])
        
        # Set initial width
        self.root.geometry('280x100')
    
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
    
    def increment_usage(self, event=None):
        self.config['current_usage'] += 1
        
        # Check if limit reached
        if self.config['current_usage'] >= self.config['usage_limit']:
            self.config['current_usage'] = self.config['usage_limit']
        
        self.save_config()
        self.update_progress()
    
    def update_progress(self):
        usage = self.config['current_usage']
        limit = self.config['usage_limit']
        
        # Check if we need to reset
        if self.config['reset_time']:
            reset_time = datetime.fromisoformat(self.config['reset_time'])
            if datetime.now() >= reset_time:
                self.config['current_usage'] = 0
                usage = 0
                # Set next reset time
                reset_hours = 5
                self.config['reset_time'] = (datetime.now() + timedelta(hours=reset_hours)).isoformat()
                self.save_config()
        
        # Update progress bar
        percentage = (usage / limit) * 100
        bar_width = int((percentage / 100) * 264)  # 264 is approx width
        self.progress_fill.place(width=bar_width)
        
        # Change color based on usage
        if percentage >= 90:
            self.progress_fill.config(bg='#ff4444')  # Red when almost full
        elif percentage >= 70:
            self.progress_fill.config(bg='#ffaa44')  # Orange
        else:
            self.progress_fill.config(bg='#CC785C')  # Claude's copper
        
        # Update text
        self.usage_label.config(text=f"{usage} / {limit} messages ({percentage:.0f}%)")
        
        # Update reset timer
        if self.config['reset_time']:
            reset_time = datetime.fromisoformat(self.config['reset_time'])
            time_left = reset_time - datetime.now()
            
            if time_left.total_seconds() > 0:
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                seconds = int(time_left.total_seconds() % 60)
                self.reset_label.config(text=f"Resets in: {hours:02d}:{minutes:02d}:{seconds:02d}")
            else:
                self.reset_label.config(text="Resetting...")
    
    def schedule_update(self):
        self.update_progress()
        self.root.after(1000, self.schedule_update)  # Update every second
    
    def show_settings(self, event=None):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("300x280")
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
            length=200
        )
        opacity_slider.pack()
        
        # Manual adjustment
        tk.Label(
            settings_win,
            text="Adjust Usage:",
            font=('Segoe UI', 9),
            fg='#cccccc',
            bg='#1a1a1a'
        ).pack(pady=(15, 5))
        
        adjust_frame = tk.Frame(settings_win, bg='#1a1a1a')
        adjust_frame.pack()
        
        usage_var = tk.IntVar(value=self.config['current_usage'])
        usage_spinbox = tk.Spinbox(
            adjust_frame,
            from_=0,
            to=self.config['usage_limit'],
            textvariable=usage_var,
            font=('Segoe UI', 10),
            bg='#2a2a2a',
            fg='#ffffff',
            width=10
        )
        usage_spinbox.pack()
        
        # Reset button
        def reset_usage():
            if messagebox.askyesno("Reset", "Reset usage to 0?", parent=settings_win):
                self.config['current_usage'] = 0
                usage_var.set(0)
                self.save_config()
                self.update_progress()
        
        tk.Button(
            settings_win,
            text="Reset Usage",
            command=reset_usage,
            bg='#ff4444',
            fg='#ffffff',
            relief='flat',
            font=('Segoe UI', 9)
        ).pack(pady=10)
        
        # Save
        def save_settings():
            self.config['opacity'] = opacity_var.get()
            self.config['current_usage'] = usage_var.get()
            self.root.attributes('-alpha', self.config['opacity'])
            self.save_config()
            self.update_progress()
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
            if messagebox.askyesno("Logout", "This will clear all data. Continue?", parent=settings_win):
                self.config['logged_in'] = False
                self.config['current_usage'] = 0
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
    
    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = ClaudeUsageBar()
    app.run()