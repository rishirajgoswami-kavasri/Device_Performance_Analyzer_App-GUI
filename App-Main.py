import customtkinter as ctk
import psutil
import platform
import socket
import uuid
import time
import threading
from collections import deque
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# =========================
# OPTIONAL GPU SUPPORT
# =========================

try:
    import GPUtil
    GPU_AVAILABLE = True
except:
    GPU_AVAILABLE = False

# =========================
# APP CONFIG
# =========================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 950

UPDATE_MS = 500
GRAPH_POINTS = 60

# =========================
# COLORS
# =========================

BG = "#070B14"
CARD = "#111827"

CPU_COLOR = "#00F5FF"
RAM_COLOR = "#FF3EF7"
NET_COLOR = "#00FF85"
GPU_COLOR = "#FFB800"

TEXT = "#F9FAFB"
SUBTEXT = "#94A3B8"

# =========================
# HELPERS
# =========================

def gb(value):
    return round(value / (1024 ** 3), 2)

def mbps(value):
    return round((value * 8) / (1024 ** 2), 2)

# =========================
# MAIN APP
# =========================

class NexusMonitor(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Device_Performance_Analyzer_App-GUI")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.configure(fg_color=BG)

        # =========================
        # DATA BUFFERS
        # =========================

        self.cpu_history = deque([0] * GRAPH_POINTS, maxlen=GRAPH_POINTS)
        self.ram_history = deque([0] * GRAPH_POINTS, maxlen=GRAPH_POINTS)
        self.net_history = deque([0] * GRAPH_POINTS, maxlen=GRAPH_POINTS)
        self.gpu_history = deque([0] * GRAPH_POINTS, maxlen=GRAPH_POINTS)

        self.last_net = psutil.net_io_counters()
        self.last_time = time.time()

        # =========================
        # UI
        # =========================

        self.build_ui()

        # =========================
        # START
        # =========================

        self.after(100, self.update_dashboard)

    # =========================
    # UI
    # =========================

    def build_ui(self):

        self.grid_columnconfigure((0,1), weight=1)
        self.grid_rowconfigure((1,2), weight=1)

        # HEADER

        header = ctk.CTkFrame(
            self,
            fg_color="#0B1220",
            corner_radius=0,
            height=90
        )

        header.grid(row=0, column=0, columnspan=2, sticky="ew")

        title = ctk.CTkLabel(
            header,
            text="Device_Performance_Analyzer_App-GUI",
            font=("Segoe UI Bold", 30),
            text_color=TEXT
        )

        title.pack(side="left", padx=30, pady=20)

        subtitle = ctk.CTkLabel(
            header,
            text="2026 Enterprise Performance Intelligence Dashboard",
            font=("Segoe UI", 14),
            text_color=SUBTEXT
        )

        subtitle.pack(side="left", pady=(35,0))

        # =========================
        # METRIC CARDS
        # =========================

        self.cpu_card = self.create_card(1,0,"CPU UTILIZATION",CPU_COLOR)
        self.ram_card = self.create_card(1,1,"MEMORY UTILIZATION",RAM_COLOR)
        self.net_card = self.create_card(2,0,"NETWORK THROUGHPUT",NET_COLOR)
        self.gpu_card = self.create_card(2,1,"GPU PERFORMANCE",GPU_COLOR)

        # =========================
        # FOOTER
        # =========================

        footer = ctk.CTkFrame(
            self,
            fg_color="#0B1220",
            corner_radius=0,
            height=42
        )

        footer.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew"
        )

        footer.grid_columnconfigure(0, weight=1)

        footer_label = ctk.CTkLabel(
            footer,
            text=(
                "Developed by Rishiraj Goswami, CEH & CCNP     |     "
                "Copyright © 2026 | All rights reserved by KAVASRI"
            ),
            font=("Segoe UI", 12),
            text_color="#94A3B8"
        )

        footer_label.grid(
            row=0,
            column=0,
            pady=10
        )

    # =========================
    # CARD
    # =========================

    def create_card(self,row,col,title,color):

        card = ctk.CTkFrame(
            self,
            fg_color=CARD,
            corner_radius=24,
            border_width=1,
            border_color="#1E293B"
        )

        card.grid(
            row=row,
            column=col,
            padx=18,
            pady=18,
            sticky="nsew"
        )

        title_label = ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI Semibold",16),
            text_color=color
        )

        title_label.pack(anchor="w", padx=20, pady=(18,0))

        value_label = ctk.CTkLabel(
            card,
            text="0%",
            font=("Segoe UI Bold",42),
            text_color=TEXT
        )

        value_label.pack(anchor="w", padx=20)

        detail_label = ctk.CTkLabel(
            card,
            text="Loading...",
            font=("Segoe UI",13),
            text_color=SUBTEXT
        )

        detail_label.pack(anchor="w", padx=20)

        # GRAPH

        fig = Figure(
            figsize=(5,2),
            dpi=100,
            facecolor=CARD
        )

        ax = fig.add_subplot(111)

        ax.set_facecolor(CARD)

        ax.tick_params(left=False,bottom=False,labelleft=False,labelbottom=False)

        for spine in ax.spines.values():
            spine.set_visible(False)

        line, = ax.plot([], [], color=color, linewidth=3)

        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        return {
            "card": card,
            "value": value_label,
            "detail": detail_label,
            "fig": fig,
            "ax": ax,
            "line": line,
            "canvas": canvas
        }

    # =========================
    # UPDATE
    # =========================

    def update_dashboard(self):

        # CPU

        cpu = psutil.cpu_percent(interval=None)
        self.cpu_history.append(cpu)

        self.cpu_card["value"].configure(text=f"{cpu:.1f}%")
        self.cpu_card["detail"].configure(
            text=f"{psutil.cpu_count()} Threads Active"
        )

        self.update_graph(
            self.cpu_card,
            self.cpu_history
        )

        # RAM

        ram = psutil.virtual_memory()
        ram_percent = ram.percent

        self.ram_history.append(ram_percent)

        self.ram_card["value"].configure(
            text=f"{ram_percent:.1f}%"
        )

        self.ram_card["detail"].configure(
            text=f"{gb(ram.used)} GB / {gb(ram.total)} GB"
        )

        self.update_graph(
            self.ram_card,
            self.ram_history
        )

        # NETWORK

        current = psutil.net_io_counters()
        now = time.time()

        elapsed = now - self.last_time

        upload = (
            current.bytes_sent - self.last_net.bytes_sent
        ) / elapsed

        download = (
            current.bytes_recv - self.last_net.bytes_recv
        ) / elapsed

        down_mbps = mbps(download)
        up_mbps = mbps(upload)

        self.net_history.append(down_mbps)

        self.net_card["value"].configure(
            text=f"{down_mbps:.2f} Mbps"
        )

        self.net_card["detail"].configure(
            text=f"↑ {up_mbps:.2f} Mbps Upload"
        )

        self.update_graph(
            self.net_card,
            self.net_history
        )

        self.last_net = current
        self.last_time = now

        # GPU

        gpu_usage = 0

        if GPU_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()

                if gpus:
                    gpu = gpus[0]
                    gpu_usage = gpu.load * 100

                    self.gpu_card["detail"].configure(
                        text=f"{gpu.memoryUsed:.0f}MB / {gpu.memoryTotal:.0f}MB VRAM"
                    )

            except:
                pass

        self.gpu_history.append(gpu_usage)

        self.gpu_card["value"].configure(
            text=f"{gpu_usage:.1f}%"
        )

        self.update_graph(
            self.gpu_card,
            self.gpu_history
        )

        self.after(UPDATE_MS, self.update_dashboard)

    # =========================
    # GRAPH ENGINE
    # =========================

    def update_graph(self, card, data):

        ax = card["ax"]
        line = card["line"]

        ax.clear()

        ax.set_facecolor(CARD)

        ax.tick_params(
            left=False,
            bottom=False,
            labelleft=False,
            labelbottom=False
        )

        for spine in ax.spines.values():
            spine.set_visible(False)

        color = line.get_color()

        ax.plot(
            list(data),
            color=color,
            linewidth=3
        )

        ax.fill_between(
            range(len(data)),
            list(data),
            alpha=0.25,
            color=color
        )

        ax.set_ylim(0, max(max(data)+10,100))

        card["canvas"].draw()

# =========================
# START
# =========================

if __name__ == "__main__":

    app = NexusMonitor()
    app.mainloop()
