import os
import platform
import json
import socket
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta

import psutil
import GPUtil
import getpass
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, messagebox

APP_TITLE = "PC Dashboard"
REFRESH_MS = 1000  # mise à jour chaque seconde
HISTORY_LEN = 60   # 60 points pour le graphe CPU (≈60 s)

def human_bytes(n: float) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if n < 1024.0:
            return f"{n:,.1f} {unit}".replace(',', ' ')
        n /= 1024.0
    return f"{n:.1f} PB"

def human_bits_per_s(n: float) -> str:
    bps = n * 8
    for unit in ["b/s", "Kb/s", "Mb/s", "Gb/s", "Tb/s"]:
        if bps < 1000:
            return f"{bps:,.0f} {unit}".replace(',', ' ')
        bps /= 1000.0
    return f"{bps:.1f} Pb/s"

def get_uptime() -> str:
    boot = datetime.fromtimestamp(psutil.boot_time())
    delta = datetime.now() - boot
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} j")
    if hours:
        parts.append(f"{hours} h")
    parts.append(f"{minutes} min")
    return ' '.join(parts)

def run_command(cmd_list):
    try:
        subprocess.Popen(cmd_list)
    except Exception as e:
        messagebox.showerror("Erreur", f"Impossible d'exécuter la commande :\n{e}")

def confirm_and_run(action_name: str, cmd_list):
    if not messagebox.askyesno("Confirmation", f"Êtes-vous sûr de vouloir {action_name} ?"):
        return
    run_command(cmd_list)

def action_restart():
    sysname = platform.system()
    if sysname == 'Windows':
        confirm_and_run("redémarrer", ["shutdown", "/r", "/t", "0"])
    elif sysname == 'Linux':
        confirm_and_run("redémarrer", ["systemctl", "reboot"])
    elif sysname == 'Darwin':
        confirm_and_run("redémarrer", ["osascript", "-e", 'tell app "System Events" to restart'])

def action_shutdown():
    sysname = platform.system()
    if sysname == 'Windows':
        confirm_and_run("éteindre", ["shutdown", "/s", "/t", "0"])
    elif sysname == 'Linux':
        confirm_and_run("éteindre", ["systemctl", "poweroff"])
    elif sysname == 'Darwin':
        confirm_and_run("éteindre", ["osascript", "-e", 'tell app "System Events" to shut down'])

def action_logout():
    sysname = platform.system()
    if sysname == 'Windows':
        confirm_and_run("fermer la session", ["shutdown", "/l"])
    elif sysname == 'Linux':
        if shutil.which("loginctl"):
            confirm_and_run("fermer la session", ["loginctl", "terminate-user", getpass.getuser()])
        elif shutil.which("gnome-session-quit"):
            confirm_and_run("fermer la session", ["gnome-session-quit", "--logout", "--no-prompt"])
        else:
            messagebox.showinfo("Info", "Commande de déconnexion non trouvée pour cet environnement.")
    elif sysname == 'Darwin':
        confirm_and_run("fermer la session", ["osascript", "-e", 'tell app "System Events" to log out'])

def action_sleep():
    sysname = platform.system()
    if sysname == 'Windows':
        confirm_and_run("mettre en veille", ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
    elif sysname == 'Linux':
        confirm_and_run("mettre en veille", ["systemctl", "suspend"])
    elif sysname == 'Darwin':
        confirm_and_run("mettre en veille", ["pmset", "sleepnow"])

def action_lock():
    sysname = platform.system()
    if sysname == 'Windows':
        run_command(["rundll32.exe", "user32.dll,LockWorkStation"])
    elif sysname == 'Linux':
        for locker in ("loginctl", "xdg-screensaver", "gnome-screensaver-command", "xlock", "i3lock"):
            if shutil.which(locker):
                if locker == "loginctl":
                    run_command(["loginctl", "lock-session"]) 
                elif locker == "xdg-screensaver":
                    run_command(["xdg-screensaver", "lock"])
                elif locker == "gnome-screensaver-command":
                    run_command(["gnome-screensaver-command", "--lock"])
                else:
                    run_command([locker])
                return
        messagebox.showinfo("Info", "Aucun utilitaire de verrouillage d'écran trouvé.")
    elif sysname == 'Darwin':
        run_command(["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"])

def action_task_manager():
    sysname = platform.system()
    if sysname == 'Windows':
        run_command(["taskmgr"])
    elif sysname == 'Linux':
        for tm in ("gnome-system-monitor", "ksysguard", "htop", "top"):
            if shutil.which(tm):
                run_command([tm])
                return
        messagebox.showinfo("Info", "Aucun moniteur système trouvé (essayez d'installer gnome-system-monitor / htop).")
    elif sysname == 'Darwin':
        run_command(["open", "-a", "Activity Monitor"])
        
def motherboard_run(cmd, shell=False):
    try:
        out = subprocess.check_output(cmd, shell=shell, stderr=subprocess.DEVNULL)
        return out.decode("utf-8")
    except Exception:
        return ""
    
def motherboard_cleanup(v):
    if not v:
        return None
    v = v.strip().strip('"').strip()
    return v or None

def get_motherboard_info():
    system = platform.system().lower()
    info = {}
    if system == "windows":
        ps = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_BaseBoard | "
            "Select-Object Product, Manufacturer, SerialNumber, Version | "
            "ConvertTo-Json -Compress"
        ]
        out = motherboard_run(ps)
        try:
            obj = json.loads(out)
            if isinstance(obj, list):
                obj = obj[0] if obj else {}
            info = {
                "manufacturer": motherboard_cleanup(obj.get("Manufacturer")),
                "product": motherboard_cleanup(obj.get("Product")),
                "version": motherboard_cleanup(obj.get("Version")),
                "serial": motherboard_cleanup(obj.get("SerialNumber")),
            }
        except Exception:
            pass
    elif system == "linux":
        base = "/sys/class/dmi/id"
        fields = {
            "manufacturer": "board_vendor",
            "product": "board_name",
            "version": "board_version",
            "serial": "board_serial",
        }
        for k, f in fields.items():
            try:
                with open(os.path.join(base, f), "r", errors="ignore") as fh:
                    info[k] = motherboard_cleanup(fh.read())
            except Exception:
                pass
    elif system == "darwin":
        board_id = None
        for line in motherboard_run(["ioreg", "-l"]).splitlines():
            if "board-id" in line:
                parts = line.split("=", 1)
                if len(parts) == 2:
                    board_id = parts[1].strip().strip('<>" ')
                    break
        info = {"manufacturer": "Apple", "product": board_id}
    return {k: v for k, v in info.items() if v}
        
def get_pc_info() -> str:
    uname = platform.uname()
    try:
        hostname = platform.node()
    except:
        hostname = "N/A"
    cpu_count = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()
    freq_text = f"{cpu_freq.current:.0f} MHz" if cpu_freq else "N/A"
    
    info = (
        f"Nom PC: {hostname}\n"
        f"Système: {uname.system} {uname.release} ({uname.machine})\n"
        f"Cœurs CPU: {cpu_count}\n"
        f"Fréquence CPU: {freq_text}"
    )
    
    info += "\n----------------------"

    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu_text = ", ".join([g.name for g in gpus])
            info += f"\nGPU: {gpu_text}"
    except:
        pass
    
    cm = get_motherboard_info()
    if cm:
        parts = []
        if cm.get("manufacturer"):
            parts.append(cm["manufacturer"])
        if cm.get("product"):
            parts.append(cm["product"])
        if cm.get("version"):
            parts.append(f"v{cm['version']}")
        # if cm.get("serial"):
        #     parts.append(f"SN:{cm['serial']}")
        info += "\nCarte mère: " + " | ".join(parts)
    
    return info

class Dashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        # self.attributes('-fullscreen', True)
        self.state("zoomed")
        self.resizable(False, False)
        self.configure(bg="#0b1220")

        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
        style.configure("TFrame", background="#0b1220")
        style.configure("TLabel", background="#0b1220", foreground="#e5e7eb", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
        style.configure("TLabelframe", background="#0b1220", foreground="#9ca3af")
        style.configure("TLabelframe.Label", background="#0b1220", foreground="#9ca3af")
        style.configure("Horizontal.TProgressbar", troughcolor="#111827", background="#60a5fa", bordercolor="#111827", lightcolor="#60a5fa", darkcolor="#60a5fa")
        style.map("TButton", foreground=[('active', '#111827')])
        style.configure("Action.TButton",
                        font=("Segoe UI", 10, "bold"),
                        foreground="#e5e7eb",
                        background="#1f2937",
                        borderwidth=0,
                        focusthickness=0,
                        padding=8)
        style.map("Action.TButton",
                  background=[("active", "#2563eb"), ("pressed", "#1d4ed8")],
                  foreground=[("active", "#f9fafb")])

        self.cpu_hist = [0] * HISTORY_LEN
        self.net_prev = psutil.net_io_counters()
        self.net_prev_time = time.time()

        self._build()
        self.after(200, self.refresh)

    def _build(self):
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)

        container.rowconfigure(0, weight=1)
        container.rowconfigure(1, weight=0)
        container.columnconfigure(0, weight=1)

        content = ttk.Frame(container)
        content.grid(row=0, column=0, sticky="nsew")

        top = ttk.Frame(content)
        top.pack(fill=tk.X, padx=14, pady=(12, 6))
        
        info_frame = ttk.Labelframe(content, text="Infos PC")
        info_frame.pack(fill="x", padx=14, pady=(6,6))
        self.pc_info_label = tk.Label(info_frame, text=get_pc_info(), justify="left", bg="#0b1220", fg="#e5e7eb", font=("Segoe UI", 10))
        self.pc_info_label.pack(anchor="w", padx=8, pady=4)

        sysinfo = ttk.Label(top, text=self._sys_info_text(), style="Header.TLabel")
        sysinfo.pack(side=tk.LEFT)

        uptime = ttk.Label(top, text=f"Uptime: {get_uptime()}")
        uptime.pack(side=tk.RIGHT)
        self.uptime_label = uptime

        grid = ttk.Frame(content)
        grid.pack(fill=tk.BOTH, expand=True, padx=14, pady=6)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        cpu_frame = ttk.Labelframe(grid, text="CPU")
        cpu_frame.columnconfigure(1, weight=1)
        cpu_frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        grid.rowconfigure(0, weight=1)

        self.cpu_total_label = ttk.Label(cpu_frame, text="Global: 0%")
        self.cpu_total_label.grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=4)

        self.core_bars = []
        for i in range(psutil.cpu_count(logical=True)):
            label = ttk.Label(cpu_frame, text=f"Cœur {i+1}")
            label.grid(row=i+1, column=0, sticky="w", padx=(8,4), pady=2)

            bar = ttk.Progressbar(cpu_frame, maximum=100, style="Horizontal.TProgressbar")
            bar.grid(row=i+1, column=1, sticky="ew", padx=(0,8), pady=2)
            self.core_bars.append(bar)

        self.cpu_canvas = tk.Canvas(cpu_frame, height=100, bg="#0b1220", highlightthickness=0)
        self.cpu_canvas.grid(row=psutil.cpu_count(logical=True)+1, column=0, columnspan=2, sticky="ew", padx=8, pady=8)

        sys_frame = ttk.Labelframe(grid, text="Système")
        sys_frame.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)

        self.ram_bar = ttk.Progressbar(sys_frame, maximum=100, style="Horizontal.TProgressbar")
        self.ram_bar.pack(fill="x", padx=8, pady=(4,0))
        self.ram_label = ttk.Label(sys_frame, text="")
        self.ram_label.pack(anchor="w", padx=8, pady=(0,4))

        self.disk_bar = ttk.Progressbar(sys_frame, maximum=100, style="Horizontal.TProgressbar")
        self.disk_bar.pack(fill="x", padx=8, pady=(4,0))
        self.disk_label = ttk.Label(sys_frame, text="")
        self.disk_label.pack(anchor="w", padx=8, pady=(0,4))

        self.net_label = ttk.Label(sys_frame, text="Up: 0 | Down: 0")
        self.net_label.pack(anchor="w", padx=8, pady=4)

        self.temp_label = ttk.Label(sys_frame, text="Températures: N/A")
        self.temp_label.pack(anchor="w", padx=8, pady=4)

        self.battery_label = ttk.Label(sys_frame, text="Batterie: N/A")
        self.battery_label.pack(anchor="w", padx=8, pady=4)

        actions = ttk.Labelframe(container, text="Actions système")
        actions.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))

        btns = [
            ("Redémarrer", action_restart),
            ("Éteindre", action_shutdown),
            ("Fermer session", action_logout),
            ("Mettre en veille", action_sleep),
            ("Verrouiller", action_lock),
            ("Gestionnaire de tâches", action_task_manager),
        ]

        cols = 3
        for i, (label, fn) in enumerate(btns):
            row = i // cols
            col = i % cols
            b = ttk.Button(actions, text=label, command=fn, style="Action.TButton")
            b.grid(row=row, column=col, padx=6, pady=6, sticky="ew")
            actions.columnconfigure(col, weight=1)

    def _sys_info_text(self) -> str:
        uname = platform.uname()
        # return f"{uname.system} {uname.release} • {uname.machine} • Python {platform.python_version()}"
        return f"{uname.system} {uname.release} • {uname.machine}"

    def refresh(self):
        try:
            self.uptime_label.config(text=f"Uptime: {get_uptime()}")
            self.pc_info_label.config(text=get_pc_info())

            cpu_total = psutil.cpu_percent(interval=None)
            per_core = psutil.cpu_percent(interval=None, percpu=True)
            self.cpu_total_label.config(text=f"Global: {cpu_total:.0f}%")
            for bar, val in zip(self.core_bars, per_core):
                bar['value'] = val

            self.cpu_hist.append(cpu_total)
            if len(self.cpu_hist) > HISTORY_LEN:
                self.cpu_hist.pop(0)
            self._draw_cpu_graph()

            vm = psutil.virtual_memory()
            self.ram_bar['value'] = vm.percent
            self.ram_label.config(text=f"{human_bytes(vm.used)} / {human_bytes(vm.total)} ({vm.percent:.0f}%)")

            usage = psutil.disk_usage(os.path.abspath(os.sep))
            pct = usage.percent
            self.disk_bar['value'] = pct
            self.disk_label.config(text=f"{human_bytes(usage.used)} / {human_bytes(usage.total)} ({pct:.0f}%)")

            now = time.time()
            cur = psutil.net_io_counters()
            dt = max(now - self.net_prev_time, 1e-6)
            up_bps = (cur.bytes_sent - self.net_prev.bytes_sent) / dt
            down_bps = (cur.bytes_recv - self.net_prev.bytes_recv) / dt
            self.net_prev, self.net_prev_time = cur, now
            self.net_label.config(text=f"Up: {human_bits_per_s(up_bps)}  |  Down: {human_bits_per_s(down_bps)}")

            temps = []
            if hasattr(psutil, 'sensors_temperatures'):
                try:
                    t = psutil.sensors_temperatures(fahrenheit=False)
                    for name, entries in t.items():
                        for e in entries:
                            if e.current is not None:
                                temps.append(f"{name}:{getattr(e, 'label', '') or e.device or ''} {e.current:.0f}°C")
                except Exception:
                    pass
            self.temp_label.config(text=", ".join(temps) if temps else "N/A")

            batt_text = "N/A"
            if hasattr(psutil, 'sensors_battery'):
                try:
                    b = psutil.sensors_battery()
                    if b is not None:
                        status = "en charge" if b.power_plugged else "sur batterie"
                        batt_text = f"{b.percent:.0f}% ({status})"
                except Exception:
                    pass
            self.battery_label.config(text=batt_text)

        except Exception as e:
            sys.stderr.write(f"Erreur rafraîchissement: {e}\n")

        finally:
            self.after(REFRESH_MS, self.refresh)

    def _draw_cpu_graph(self):
        c = self.cpu_canvas
        c.delete("all")
        w = c.winfo_width() or c.winfo_reqwidth()
        h = c.winfo_height() or c.winfo_reqheight()
        margin = 8
        
        c.create_rectangle(margin, margin, w - margin, h - margin, outline="#1f2937")

        for pct in (25, 50, 75):
            y = margin + (h - 2*margin) * (1 - pct/100)
            c.create_line(margin, y, w - margin, y, fill="#1f2937")
            c.create_text(margin + 18, y - 8, text=f"{pct}%", anchor="w", fill="#6b7280", font=("Segoe UI", 8))
        
        if not self.cpu_hist:
            return

        points = []
        n = len(self.cpu_hist)
        for i, val in enumerate(self.cpu_hist):
            x = margin + (w - 2*margin) * (i / max(1, HISTORY_LEN - 1))
            y = margin + (h - 2*margin) * (1 - val/100)
            points.append((x, y))

        for i in range(1, len(points)):
            val = self.cpu_hist[i]
            r = int(255 * val / 100)
            g = int(255 * (1 - val / 100))
            color = f"#{r:02x}{g:02x}00"
            c.create_line(points[i-1][0], points[i-1][1], points[i][0], points[i][1], fill=color, width=2)

        x, y = points[-1]
        c.create_oval(x-3, y-3, x+3, y+3, fill="#93c5fd", outline="")

if __name__ == "__main__":
    try:
        app = Dashboard()
        app.mainloop()
    except Exception as e:
        import traceback
        with open("error.log", "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())