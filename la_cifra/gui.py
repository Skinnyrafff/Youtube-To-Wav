"""Interfaz gráfica de LA CIFRA DOWNLOADER."""
import queue
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from . import APP_NAME, __version__, updater
from .core import DEFAULT_QUALITY, MP3_BITRATES, WAV_BITS, Downloader, fetch_preview
from .paths import asset, load_config, save_config, user_folders
from .winutil import IS_WINDOWS, paint_title_bar, reveal_in_explorer, set_app_id

# Paleta (tomada de los logos de LA CIFRA): interfaz siempre negra
BG = "#1A1714"
CARD = "#24201C"
SURFACE = "#2E2924"
LINE = "#3A332C"
INPUT = "#14110F"
TEXT = "#EFE7D8"
MUTED = "#A89A84"
BEIGE = "#D3C4AA"
BROWN = "#6B5A45"
ERROR = "#F2836B"

PRIMARY = dict(fg_color=BEIGE, hover_color=TEXT, text_color=BG)
SECONDARY = dict(fg_color=LINE, hover_color="#4A4138", text_color=TEXT)
ENTRY = dict(fg_color=INPUT, border_color=LINE, text_color=TEXT, placeholder_text_color="#7A6E5E")
MENU = dict(fg_color=LINE, button_color="#4A4138", button_hover_color=BROWN, text_color=TEXT,
            dropdown_fg_color=SURFACE, dropdown_hover_color=LINE, dropdown_text_color=TEXT)

THUMB_SIZE = (192, 108)
DOWNLOAD_WEIGHT = 0.7  # la barra usa 0–70 % para descargar y 70–100 % para convertir
OTHER_FOLDER = "Otra carpeta..."


def fit_thumbnail(image: Image.Image) -> Image.Image:
    """Recorta al centro a 16:9 para que todas las portadas queden iguales."""
    w, h = image.size
    target = THUMB_SIZE[0] / THUMB_SIZE[1]
    if w / h > target:
        new_w = int(h * target)
        image = image.crop(((w - new_w) // 2, 0, (w + new_w) // 2, h))
    else:
        new_h = int(w / target)
        image = image.crop((0, (h - new_h) // 2, w, (h + new_h) // 2))
    return image.convert("RGB")


def style_window(window):
    window.configure(fg_color=BG)
    window.after(50, lambda: paint_title_bar(window, BG, TEXT))
    ico = asset("icon.ico")
    if IS_WINDOWS and ico.exists():
        window.iconbitmap(str(ico))
        # CTk pone su ícono propio a los ~200 ms; lo pisamos después
        window.after(250, lambda: window.iconbitmap(str(ico)))
    elif asset("icon.png").exists():
        from PIL import ImageTk
        window._icon_photo = ImageTk.PhotoImage(Image.open(asset("icon.png")))
        window.iconphoto(True, window._icon_photo)


# --- Ventana de logs ---

class LogWindow(ctk.CTkToplevel):
    def __init__(self, master, lines: list[str]):
        super().__init__(master)
        self.title(f"{APP_NAME} {__version__} · Logs")
        self.geometry("720x420")
        style_window(self)

        self.text = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=12), wrap="word",
                                   fg_color=INPUT, text_color=TEXT, border_color=LINE, border_width=1)
        self.text.pack(fill="both", expand=True, padx=12, pady=(12, 8))

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(bar, text="Copiar", width=90, command=self._copy, **SECONDARY).pack(side="left")
        ctk.CTkButton(bar, text="Limpiar", width=90, command=master.clear_logs,
                      **SECONDARY).pack(side="left", padx=8)
        ctk.CTkButton(bar, text="Cerrar", width=90, command=self.destroy, **PRIMARY).pack(side="right")

        for line in lines:
            self.append(line)
        self.after(150, self.lift)

    def append(self, line: str):
        self.text.configure(state="normal")
        self.text.insert("end", line + "\n")
        self.text.see("end")
        self.text.configure(state="disabled")

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.text.get("1.0", "end"))


# --- Ventana principal ---

class App(ctk.CTk):
    def __init__(self):
        set_app_id("LaCifra.Downloader")
        ctk.set_appearance_mode("dark")
        super().__init__()
        self.title(APP_NAME)
        self.geometry("640x710")
        self.minsize(560, 710)
        style_window(self)

        self.events: queue.Queue = queue.Queue()
        self.downloader: Downloader | None = None
        self.logs: list[str] = []
        self.log_window: LogWindow | None = None
        self.last_file: str | None = None
        self._revealed_dir: Path | None = None
        self._active_fmt = "WAV"

        # Destino recordado
        self.config_data = load_config()
        self.custom_dirs = [Path(p) for p in self.config_data.get("custom_dirs", []) if Path(p).is_dir()]
        saved = self.config_data.get("out_dir")
        folders = user_folders()
        if saved and Path(saved).is_dir():
            self.out_dir = Path(saved)
        else:
            self.out_dir = folders[0][1] if folders else Path.home()

        # Actualizaciones
        self.release: updater.Release | None = None
        self.updating = False

        self._build()
        self.after(100, self._poll_events)
        self.after(2500, lambda: self.check_updates(silent=True))

    # --- Construcción ---

    def _build(self):
        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=24, pady=(20, 12))

        # Encabezado
        header = ctk.CTkFrame(root, fg_color="transparent")
        header.pack(fill="x")
        if asset("logo.png").exists():
            logo = Image.open(asset("logo.png"))
            h = 44
            self._logo_img = ctk.CTkImage(dark_image=logo, light_image=logo,
                                          size=(round(logo.width * h / logo.height), h))
            ctk.CTkLabel(header, text="", image=self._logo_img).pack(side="left")
            ctk.CTkLabel(header, text="DOWNLOADER", text_color=MUTED,
                         font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=(12, 0), pady=(14, 0))
        else:
            ctk.CTkLabel(header, text=APP_NAME, text_color=TEXT,
                         font=ctk.CTkFont(size=26, weight="bold")).pack(side="left")
        ctk.CTkButton(header, text="Ver logs", width=90, command=self.show_logs,
                      **SECONDARY).pack(side="right")
        ctk.CTkLabel(root, text="Pega un enlace de YouTube y descarga el audio.",
                     text_color=MUTED).pack(anchor="w", pady=(8, 14))

        card = ctk.CTkFrame(root, fg_color=CARD, corner_radius=12)
        card.pack(fill="x")

        # URL
        self._section_label(card, "URL").pack(anchor="w", padx=16, pady=(14, 4))
        url_row = ctk.CTkFrame(card, fg_color="transparent")
        url_row.pack(fill="x", padx=16)
        self.url_entry = ctk.CTkEntry(url_row, height=40, placeholder_text="https://www.youtube.com/watch?v=...",
                                      **ENTRY)
        self.url_entry.pack(side="left", fill="x", expand=True)
        self.url_entry.bind("<Return>", lambda _e: self.start())
        self.url_entry.bind("<KeyRelease>", lambda _e: self._schedule_preview())
        ctk.CTkButton(url_row, text="Pegar", width=72, height=40, command=self._paste,
                      **SECONDARY).pack(side="left", padx=(8, 0))

        # Vista previa (oculta hasta que haya un enlace)
        self.preview = ctk.CTkFrame(card, fg_color=SURFACE, corner_radius=10)
        self.preview_anchor = url_row
        self.thumb = ctk.CTkLabel(self.preview, text="", width=THUMB_SIZE[0], height=THUMB_SIZE[1],
                                  fg_color=LINE, corner_radius=8)
        self.thumb.pack(side="left", padx=10, pady=10)
        info = ctk.CTkFrame(self.preview, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=10)
        self.preview_title = ctk.CTkLabel(info, text="", anchor="w", justify="left", wraplength=270,
                                          text_color=TEXT, font=ctk.CTkFont(size=14, weight="bold"))
        self.preview_title.pack(fill="x", anchor="w")
        self.preview_author = ctk.CTkLabel(info, text="", anchor="w", text_color=MUTED)
        self.preview_author.pack(fill="x", anchor="w", pady=(2, 0))
        self._preview_job = None
        self._preview_url = ""
        self._preview_token = 0
        self._preview_pil = None

        # Formato + bits
        opts = ctk.CTkFrame(card, fg_color="transparent")
        opts.pack(fill="x", padx=16, pady=(14, 0))
        self._section_label(opts, "Formato").grid(row=0, column=0, sticky="w")
        self.fmt_var = ctk.StringVar(value="WAV")
        ctk.CTkSegmentedButton(opts, values=["WAV", "MP3"], variable=self.fmt_var, height=34,
                               fg_color=SURFACE, unselected_color=SURFACE, unselected_hover_color=LINE,
                               selected_color=BROWN, selected_hover_color="#7D6A52", text_color=TEXT,
                               command=self._on_format_change).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.bits_label = self._section_label(opts, "Profundidad de bits")
        self.bits_label.grid(row=0, column=1, sticky="w", padx=(20, 0))
        self.bits_var = ctk.StringVar(value=DEFAULT_QUALITY["wav"])
        self.bits_menu = ctk.CTkOptionMenu(opts, values=list(WAV_BITS), variable=self.bits_var, height=34,
                                           width=170, **MENU)
        self.bits_menu.grid(row=1, column=1, sticky="w", padx=(20, 0), pady=(4, 0))

        # Destino
        self._section_label(card, "Destino").pack(anchor="w", padx=16, pady=(14, 4))
        self.folder_var = ctk.StringVar()
        self.folder_menu = ctk.CTkOptionMenu(card, variable=self.folder_var, height=36, values=[""],
                                             dynamic_resizing=False, anchor="w", command=self._on_folder_pick,
                                             **MENU)
        self.folder_menu.pack(fill="x", padx=16, pady=(0, 16))
        self._refresh_folder_menu()

        # Descargar
        self.main_button = ctk.CTkButton(root, text="Descargar", height=46, corner_radius=10,
                                         font=ctk.CTkFont(size=15, weight="bold"),
                                         command=self.start, **PRIMARY)
        self.main_button.pack(fill="x", pady=(16, 14))

        # Barra de carga
        self.progress = ctk.CTkProgressBar(root, height=10, progress_color=BEIGE, fg_color=LINE)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(6, 6))

        status_row = ctk.CTkFrame(root, fg_color="transparent")
        status_row.pack(fill="x")
        self.status_label = ctk.CTkLabel(status_row, text="Listo.", text_color=MUTED, anchor="w",
                                         justify="left", wraplength=420)
        self.status_label.pack(side="left", fill="x", expand=True)
        self.open_button = ctk.CTkButton(status_row, text="Abrir carpeta", width=110,
                                         command=self._open_folder, **SECONDARY)

        # Pie: versión y actualizaciones
        footer = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=44)
        footer.pack(fill="x", side="bottom")
        ctk.CTkLabel(footer, text=f"Versión {__version__}", text_color=MUTED,
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(24, 0), pady=8)
        self.update_button = ctk.CTkButton(footer, text="Buscar actualización", width=170, height=28,
                                           command=self.on_update_click, **SECONDARY)
        self.update_button.pack(side="right", padx=(0, 24), pady=8)
        self.update_label = ctk.CTkLabel(footer, text="", text_color=MUTED, font=ctk.CTkFont(size=12))
        self.update_label.pack(side="right", padx=12)

    def _section_label(self, parent, text):
        return ctk.CTkLabel(parent, text=text, text_color=MUTED, font=ctk.CTkFont(size=12, weight="bold"))

    # --- Opciones ---

    def _on_format_change(self, fmt: str):
        if fmt == "MP3":
            self.bits_label.configure(text="Bitrate")
            self.bits_menu.configure(values=list(MP3_BITRATES))
        else:
            self.bits_label.configure(text="Profundidad de bits")
            self.bits_menu.configure(values=list(WAV_BITS))
        self.bits_var.set(DEFAULT_QUALITY[fmt.lower()])

    def _paste(self):
        try:
            text = self.clipboard_get().strip()
        except Exception:  # noqa: BLE001
            return
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, text)
        self._schedule_preview(delay=0)

    # --- Vista previa ---

    def _schedule_preview(self, delay: int = 500):
        if self._preview_job:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(delay, self._load_preview)

    def _load_preview(self):
        self._preview_job = None
        url = self.url_entry.get().strip()
        if url == self._preview_url:
            return
        self._preview_url = url
        self._preview_token += 1
        self._preview_pil = None
        token = self._preview_token

        if not url.startswith(("http://", "https://", "www.", "youtu")):
            self.preview.pack_forget()
            return

        self._show_preview("Cargando vista previa...", "", None)

        def worker():
            try:
                title, author, image = fetch_preview(url)
                if image is not None:
                    image = fit_thumbnail(image)
                self.events.put(("preview", token, title, author, image))
            except Exception as e:  # noqa: BLE001
                self.events.put(("log", f"Vista previa no disponible: {e}"))
                self.events.put(("preview", token, None, None, None))

        threading.Thread(target=worker, daemon=True).start()

    def _show_preview(self, title: str, author: str, image):
        self.preview_title.configure(text=title)
        self.preview_author.configure(text=author)
        if image is not None:
            self._thumb_img = ctk.CTkImage(light_image=image, dark_image=image, size=THUMB_SIZE)
            self.thumb.configure(image=self._thumb_img, fg_color="transparent")
        else:
            self._thumb_img = None
            self.thumb.configure(image="", fg_color=LINE)
        if not self.preview.winfo_ismapped():
            self.preview.pack(fill="x", padx=16, pady=(10, 0), after=self.preview_anchor)

    # --- Destino ---

    def _refresh_folder_menu(self):
        """Arma el menú: carpetas del usuario, las elegidas antes y 'Otra carpeta...'."""
        self._folder_options: dict[str, Path] = {}
        entries = user_folders() + [(p.name or str(p), p) for p in self.custom_dirs]
        if not any(p == self.out_dir for _, p in entries):
            entries.append((self.out_dir.name or str(self.out_dir), self.out_dir))
        for name, path in entries:
            if path not in self._folder_options.values():
                self._folder_options[f"{name}   ·   {path}"] = path
        self.folder_menu.configure(values=[*self._folder_options, OTHER_FOLDER])
        self.folder_var.set(next(label for label, p in self._folder_options.items() if p == self.out_dir))

    def _on_folder_pick(self, label: str):
        if label == OTHER_FOLDER:
            chosen = filedialog.askdirectory(parent=self, title="Elige la carpeta de destino",
                                             initialdir=self.out_dir if self.out_dir.exists() else Path.home())
            if chosen:
                path = Path(chosen)
                if path not in self.custom_dirs and path not in [p for _, p in user_folders()]:
                    self.custom_dirs = [path, *self.custom_dirs][:5]
                self.out_dir = path
        else:
            self.out_dir = self._folder_options[label]
        self._refresh_folder_menu()
        self.config_data.update(out_dir=str(self.out_dir), custom_dirs=[str(p) for p in self.custom_dirs])
        save_config(self.config_data)

    def _open_folder(self):
        self.out_dir.mkdir(parents=True, exist_ok=True)
        file = self.last_file if self.last_file and Path(self.last_file).exists() else None
        folder = Path(file).parent if file else self.out_dir
        try:
            reveal_in_explorer(file, folder, self._revealed_dir)
            self._revealed_dir = folder
        except Exception as e:  # noqa: BLE001
            self._add_log(f"No se pudo abrir la carpeta: {e}")

    # --- Logs ---

    def show_logs(self):
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.focus()
            self.log_window.lift()
        else:
            self.log_window = LogWindow(self, self.logs)

    def clear_logs(self):
        self.logs.clear()
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.clear()

    def _add_log(self, msg: str):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        self.logs.append(line)
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.append(line)

    # --- Descarga ---

    def _set_status(self, text: str, error: bool = False):
        self.status_label.configure(text=text, text_color=ERROR if error else MUTED)

    def _set_busy(self, busy: bool):
        if busy:
            self.main_button.configure(text="Cancelar", command=self.cancel, **SECONDARY)
            self.url_entry.configure(state="disabled")
            self.open_button.pack_forget()
        else:
            self.main_button.configure(text="Descargar", command=self.start, state="normal", **PRIMARY)
            self.url_entry.configure(state="normal")
            self.progress.stop()
            self.progress.configure(mode="determinate")

    def start(self):
        if self.downloader or self.updating:
            return
        url = self.url_entry.get().strip()
        if not url:
            self._set_status("Primero pega un enlace de YouTube.", error=True)
            self.url_entry.focus()
            return

        self.progress.set(0)
        self.last_file = None
        self._set_busy(True)
        self._set_status("Iniciando...")
        self._add_log("─" * 40)

        self._active_fmt = self.fmt_var.get()
        self.downloader = Downloader(self.events.put)
        threading.Thread(target=self.downloader.run,
                         args=(url, self.out_dir, self._active_fmt.lower(), self.bits_var.get()),
                         daemon=True).start()

    def cancel(self):
        if self.downloader:
            self.downloader.cancel_requested = True
            self.main_button.configure(text="Cancelando...", state="disabled")

    # --- Actualizaciones ---

    def check_updates(self, silent: bool = False):
        if not silent:
            self.update_button.configure(state="disabled")
            self.update_label.configure(text="Buscando...", text_color=MUTED)

        def worker():
            try:
                self.events.put(("update_info", silent, updater.latest_release(), None))
            except Exception as e:  # noqa: BLE001
                self.events.put(("update_info", silent, None, e))

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_info(self, silent: bool, release, error):
        self.update_button.configure(state="normal")
        if error:
            self._add_log(f"No se pudo buscar actualizaciones: {error}")
            if not silent:
                self.update_label.configure(text="Sin conexión con GitHub.", text_color=ERROR)
            return
        if release and updater.is_newer(release.version):
            self.release = release
            self.update_label.configure(text="Hay una versión nueva", text_color=BEIGE)
            self.update_button.configure(text=f"Actualizar a {release.version}", **PRIMARY)
            if not silent:
                self.on_update_click()
        elif not silent:
            self.update_label.configure(text="Tienes la última versión.", text_color=MUTED)

    def on_update_click(self):
        if self.updating:
            return
        if not self.release:
            self.check_updates()
            return

        release = self.release
        notes = release.notes[:600] + ("..." if len(release.notes) > 600 else "")
        if not updater.can_self_update() or not release.installer_url:
            if messagebox.askyesno(APP_NAME, f"Hay una versión nueva ({release.version}).\n\n"
                                   "¿Abrir la página de descarga?", parent=self):
                webbrowser.open(release.page_url)
            return
        if self.downloader:
            messagebox.showinfo(APP_NAME, "Espera a que termine la descarga actual para actualizar.", parent=self)
            return
        question = f"Hay una versión nueva: {release.version} (tienes {__version__}).\n\n"
        if notes:
            question += f"Novedades:\n{notes}\n\n"
        question += "¿Descargar e instalar ahora? La app se cerrará y volverá a abrirse sola."
        if not messagebox.askyesno(APP_NAME, question, parent=self):
            return

        self.updating = True
        self.main_button.configure(state="disabled")
        self.update_button.configure(state="disabled", text="Actualizando...")
        self.progress.set(0)
        self._set_status("Descargando actualización...")
        self._add_log(f"Descargando {release.installer_name} ...")

        def worker():
            try:
                path = updater.download_installer(
                    release, lambda f: self.events.put(("update_progress", f)))
                self.events.put(("update_ready", path))
            except Exception as e:  # noqa: BLE001
                self.events.put(("update_failed", e))

        threading.Thread(target=worker, daemon=True).start()

    # --- Eventos (todo lo que llega de los hilos pasa por acá) ---

    def _poll_events(self):
        try:
            while True:
                self._handle(self.events.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _handle(self, ev):
        kind = ev[0]
        if kind == "log":
            self._add_log(ev[1])
        elif kind == "status":
            self._set_status(ev[1])
        elif kind == "title":
            # Si la vista previa no consiguió el título, usamos el de yt-dlp
            if self.preview_title.cget("text") in ("", "Cargando vista previa...", "Sin vista previa"):
                self._show_preview(ev[1], self.preview_author.cget("text"), self._preview_pil)
        elif kind == "preview":
            token, title, author, image = ev[1:]
            if token == self._preview_token:
                self._preview_pil = image
                if title or image is not None:
                    self._show_preview(title or "Video", author or "", image)
                else:
                    self._show_preview("Sin vista previa", "", None)
        elif kind == "progress":
            self._on_progress(*ev[1:])
        elif kind == "done":
            self.downloader = None
            self._set_busy(False)
            self.progress.set(1)
            self.last_file = ev[1]
            self._set_status(f"Listo: {Path(ev[1]).name if ev[1] else 'archivo guardado'}")
            self.open_button.pack(side="right")
            self._open_folder()
        elif kind == "cancelled":
            self.downloader = None
            self._set_busy(False)
            self.progress.set(0)
            self._set_status("Descarga cancelada.")
        elif kind == "error":
            self._add_log(f"ERROR: {ev[1]}")
            self.downloader = None
            self._set_busy(False)
            self.progress.set(0)
            self._set_status(ev[1], error=True)
        elif kind == "update_info":
            self._on_update_info(*ev[1:])
        elif kind == "update_progress":
            self.progress.set(ev[1])
            self._set_status(f"Descargando actualización  {ev[1] * 100:.0f}%")
        elif kind == "update_ready":
            self._add_log(f"Instalando {ev[1]}")
            self._set_status("Instalando actualización... la app se volverá a abrir.")
            self.update_idletasks()
            updater.run_installer(ev[1])
            self.after(300, self.destroy)
        elif kind == "update_failed":
            self.updating = False
            self.main_button.configure(state="normal")
            self.update_button.configure(state="normal", text=f"Actualizar a {self.release.version}")
            self.progress.set(0)
            self._add_log(f"Error al actualizar: {ev[1]!r}")
            self._set_status(f"No se pudo descargar la actualización: {ev[1]}", error=True)

    def _on_progress(self, phase, frac, detail):
        label = "Descargando" if phase == "download" else f"Convirtiendo a {self._active_fmt}"
        if frac is None:
            # Tamaño o duración desconocidos: única situación en que la barra queda animada
            if self.progress.cget("mode") != "indeterminate":
                self.progress.configure(mode="indeterminate")
                self.progress.start()
            self._set_status(f"{label}..." + (f"  ·  {detail}" if detail else ""))
            return
        if self.progress.cget("mode") == "indeterminate":
            self.progress.stop()
            self.progress.configure(mode="determinate")
        overall = frac * DOWNLOAD_WEIGHT if phase == "download" else DOWNLOAD_WEIGHT + frac * (1 - DOWNLOAD_WEIGHT)
        self.progress.set(overall)
        self._set_status(f"{label}  {frac * 100:.0f}%" + (f"  ·  {detail}" if detail else ""))


def main():
    App().mainloop()
