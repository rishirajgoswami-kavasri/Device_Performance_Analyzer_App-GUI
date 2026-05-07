import customtkinter as ctk
import psutil
import platform
import socket
import uuid
import threading
import time
import sys
import requests
from concurrent.futures import ThreadPoolExecutor

# =========================
# OPTIONAL DEPENDENCIES
# =========================

try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

# =========================
# CONFIG
# =========================

APP_NAME = "NEXUS Performance Monitor"
WIDTH = 1180
HEIGHT = 720

UPDATE_INTERVAL = 1
NETWORK_TIMEOUT = 2

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# =========================
# HELPERS
# =========================

def gb(value):
    return round(value / (1024 ** 3), 2)

def mbps(value):
    return round((value * 8) / (1024 ** 2), 2)

def safe_call(func, fallback="N/A"):
    try:
        return func()
    except Exception:
        return fallback

# =========================
# METRIC CARD
# =========================

class MetricCard(ctk.CTkFrame):

    def __init__(self, parent, title):
        super().__init__(
            parent,
            corner_radius=18,
            fg_color="#111827",
            border_width=1,
            border_color="#1F2937"
        )

        self.grid_columnconfigure(0, weight=1)

        self.title = ctk.CTkLabel(
            self,
            text=title,
            font=("Segoe UI Semibold", 15),
            text_color="#9CA3AF"
        )
        self.title.grid(row=0, column=0, padx=18, pady=(14, 4), sticky="w")

        self.value = ctk.CTkLabel(
            self,
            text="--",
            font=("Segoe UI Bold", 30),
            text_color="#F9FAFB"
        )
        self.value.grid(row=1, column=0, padx=18, sticky="w")

        self.subtext = ctk.CTkLabel(
            self,
            text="",
            font=("Segoe UI", 12),
            text_color="#6B7280"
        )
        self.subtext.grid(row=2, column=0, padx=18, pady=(0, 8), sticky="w")

        self.progress = ctk.CTkProgressBar(
            self,
            height=10,
            corner_radius=20
        )
        self.progress.grid(
            row=3,
            column=0,
            padx=18,
            pady=(0, 18),
            sticky="ew"
        )

        self.progress.set(0)

# =========================
# MAIN APP
# =========================

class PerformanceMonitor(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry(f"{WIDTH}x{HEIGHT}")
        self.minsize(1000, 650)

        self.protocol("WM_DELETE_WINDOW", self.close)

        self.executor = ThreadPoolExecutor(max_workers=4)
        self.running = True

        self.last_net = psutil.net_io_counters()
        self.last_time = time.time()

        self.create_ui()

        self.after(100, self.load_static_data)
        self.after(500, self.update_metrics)

    # =========================
    # UI
    # =========================

    def create_ui(self):

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # HEADER

        header = ctk.CTkFrame(
            self,
            height=80,
            fg_color="#0B1120",
            corner_radius=0
        )
        header.grid(row=0, column=0, sticky="ew")

        title = ctk.CTkLabel(
            header,
            text=APP_NAME,
            font=("Segoe UI Bold", 32),
            text_color="#F8FAFC"
        )
        title.pack(side="left", padx=28, pady=18)

        subtitle = ctk.CTkLabel(
            header,
            text="Enterprise System Telemetry Dashboard",
            font=("Segoe UI", 13),
            text_color="#94A3B8"
        )
        subtitle.pack(side="left", pady=(28, 0))

        # MAIN CONTENT

        self.main = ctk.CTkFrame(
            self,
            fg_color="#020617",
            corner_radius=0
        )
        self.main.grid(row=1, column=0, sticky="nsew")

        self.main.grid_columnconfigure((0, 1), weight=1)
        self.main.grid_rowconfigure((0, 1), weight=1)

        # CPU CARD

        self.cpu_card = MetricCard(self.main, "CPU UTILIZATION")
        self.cpu_card.grid(
            row=0,
            column=0,
            padx=18,
            pady=18,
            sticky="nsew"
        )

        # RAM CARD

        self.ram_card = MetricCard(self.main, "MEMORY UTILIZATION")
        self.ram_card.grid(
            row=0,
            column=1,
            padx=18,
            pady=18,
            sticky="nsew"
        )

        # NETWORK CARD

        self.net_card = MetricCard(self.main, "NETWORK THROUGHPUT")
        self.net_card.grid(
            row=1,
            column=0,
            padx=18,
            pady=18,
            sticky="nsew"
        )

        # GPU CARD

        self.gpu_card = MetricCard(self.main, "GPU PERFORMANCE")
        self.gpu_card.grid(
            row=1,
            column=1,
            padx=18,
            pady=18,
            sticky="nsew"
        )

        # SYSTEM INFO

        self.info_frame = ctk.CTkFrame(
            self,
            fg_color="#0F172A",
            corner_radius=16,
            border_width=1,
            border_color="#1E293B"
        )

        self.info_frame.place(
            relx=0.5,
            rely=0.965,
            anchor="s",
            relwidth=0.97,
            height=95
        )

        self.info_label = ctk.CTkLabel(
            self.info_frame,
            text="Loading system metadata...",
            justify="left",
            anchor="w",
            font=("Consolas", 13),
            text_color="#CBD5E1"
        )

        self.info_label.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=12
        )

    # =========================
    # STATIC DATA
    # =========================

    def load_static_data(self):

        system = platform.system()
        release = platform.release()
        machine = platform.machine()

        ip = self.get_ip()
        mac = self.get_mac()

        model = self.get_model()
        gpu = self.get_gpu_name()

        info = (
            f"MODEL: {model}\n"
            f"OS: {system} {release} ({machine})\n"
            f"LOCAL IP: {ip}    |    MAC: {mac}\n"
            f"GPU: {gpu}"
        )

        self.info_label.configure(text=info)

    def get_ip(self):

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "Unavailable"

    def get_mac(self):

        try:
            mac = ':'.join(
                ('%012X' % uuid.getnode())[i:i + 2]
                for i in range(0, 12, 2)
            )
            return mac
        except Exception:
            return "Unavailable"

    def get_model(self):

        if WMI_AVAILABLE and platform.system() == "Windows":
            try:
                c = wmi.WMI()
                return c.Win32_ComputerSystem()[0].Model
            except Exception:
                return "Unavailable"

        return platform.node()

    def get_gpu_name(self):

        if GPU_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    return gpus[0].name
            except Exception:
                pass

        return "Unavailable"

    # =========================
    # METRICS
    # =========================

    def update_metrics(self):

        if not self.running:
            return

        try:
            self.update_cpu()
            self.update_ram()
            self.update_network()
            self.update_gpu()
        except Exception as e:
            print(f"Update Error: {e}")

        self.after(UPDATE_INTERVAL * 1000, self.update_metrics)

    def update_cpu(self):

        cpu = psutil.cpu_percent()

        self.cpu_card.value.configure(text=f"{cpu:.1f}%")
        self.cpu_card.subtext.configure(
            text=f"{psutil.cpu_count(logical=True)} Threads Active"
        )
        self.cpu_card.progress.set(cpu / 100)

    def update_ram(self):

        memory = psutil.virtual_memory()

        used = gb(memory.used)
        total = gb(memory.total)

        self.ram_card.value.configure(
            text=f"{memory.percent:.1f}%"
        )

        self.ram_card.subtext.configure(
            text=f"{used} GB / {total} GB"
        )

        self.ram_card.progress.set(memory.percent / 100)

    def update_network(self):

        current = psutil.net_io_counters()
        now = time.time()

        elapsed = now - self.last_time

        upload = (
            current.bytes_sent - self.last_net.bytes_sent
        ) / elapsed

        download = (
            current.bytes_recv - self.last_net.bytes_recv
        ) / elapsed

        up = mbps(upload)
        down = mbps(download)

        self.net_card.value.configure(
            text=f"{down:.2f} Mbps"
        )

        self.net_card.subtext.configure(
            text=f"↑ {up:.2f} Mbps Upload"
        )

        usage_ratio = min(down / 100, 1)

        self.net_card.progress.set(usage_ratio)

        self.last_net = current
        self.last_time = now

    def update_gpu(self):

        if GPU_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()

                if gpus:

                    gpu = gpus[0]

                    usage = gpu.load * 100

                    self.gpu_card.value.configure(
                        text=f"{usage:.1f}%"
                    )

                    self.gpu_card.subtext.configure(
                        text=(
                            f"{gpu.memoryUsed:.0f}MB / "
                            f"{gpu.memoryTotal:.0f}MB VRAM"
                        )
                    )

                    self.gpu_card.progress.set(usage / 100)

                    return

            except Exception:
                pass

        self.gpu_card.value.configure(text="N/A")
        self.gpu_card.subtext.configure(text="GPU Telemetry Unavailable")
        self.gpu_card.progress.set(0)

    # =========================
    # CLOSE
    # =========================

    def close(self):

        self.running = False

        try:
            self.executor.shutdown(wait=False)
        except Exception:
            pass

        self.destroy()
        sys.exit()

# =========================
# START
# =========================

if __name__ == "__main__":

    app = PerformanceMonitor()
    app.mainloop()
