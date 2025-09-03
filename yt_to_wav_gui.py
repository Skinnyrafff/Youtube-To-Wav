import tkinter as tk
from tkinter import ttk, messagebox
import threading
from pathlib import Path
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

# --- Lógica de descarga (adaptada para la GUI) ---

def on_progress_gui(d, status_var):
    """Actualiza una variable de Tkinter con el progreso de la descarga."""
    if d.get('status') == 'downloading':
        p = d.get('_percent_str', '').strip()
        spd = d.get('_speed_str', '').strip()
        eta = d.get('_eta_str', '').strip()
        status_var.set(f"Descargando: {p} | Velocidad: {spd} | ETA: {eta}")
    elif d.get('status') == 'finished':
        status_var.set("Descarga completa, convirtiendo a WAV...")

def download_to_wav_gui(url: str, status_var: tk.StringVar, progress_hook_callback):
    """
    Descarga el audio de una URL y lo convierte a WAV, actualizando la GUI.
    """
    try:
        out_dir = "wav_output"
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        script_dir = Path(__file__).parent
        ffmpeg_dir = script_dir / "ffmpeg-8.0-essentials_build" / "bin"

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(Path(out_dir) / "% (title)s.%(ext)s"),
            "noplaylist": True,
            "progress_hooks": [progress_hook_callback],
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }],
            "quiet": True,
        }

        if ffmpeg_dir.exists():
            ydl_opts["ffmpeg_location"] = str(ffmpeg_dir)

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            base_filename = ydl.prepare_filename(info_dict).rsplit('.', 1)[0]
            output_filename = f"{base_filename}.wav"
            status_var.set(f"¡Éxito! Guardado en: {output_filename}")
            messagebox.showinfo("Éxito", f"Audio guardado en:\n{output_filename}")

    except DownloadError as e:
        error_message = f"Error: No se pudo procesar la URL."
        if "is not a valid URL" in str(e):
            error_message = f"Error: La URL no parece ser válida."
        elif "ffmpeg not found" in str(e):
            error_message = "Error: FFmpeg no encontrado. Asegúrate de que esté en la carpeta correcta."
        status_var.set(error_message)
        messagebox.showerror("Error de Descarga", error_message)
    except Exception as e:
        status_var.set(f"Error inesperado: {e}")
        messagebox.showerror("Error Inesperado", f"Ocurrió un error:\n{e}")

# --- Aplicación GUI ---

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube to WAV Downloader")
        self.geometry("550x170")
        self.resizable(False, False)

        # Estilo
        style = ttk.Style(self)
        style.theme_use('clam')

        # Widgets
        self.url_label = ttk.Label(self, text="URL de YouTube:")
        self.url_label.pack(pady=(10, 0))

        self.url_entry = ttk.Entry(self, width=70)
        self.url_entry.pack(pady=5, padx=15)

        self.download_button = ttk.Button(self, text="Descargar y Convertir a WAV", command=self.start_download_thread)
        self.download_button.pack(pady=10)

        self.status_var = tk.StringVar()
        self.status_var.set("Listo para descargar.")
        self.status_label = ttk.Label(self, textvariable=self.status_var, wraplength=500)
        self.status_label.pack(pady=(5, 10), padx=10)

    def start_download_thread(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showwarning("URL Vacía", "Por favor, introduce una URL de YouTube.")
            return

        self.download_button.config(state=tk.DISABLED)
        self.status_var.set("Iniciando descarga...")

        progress_hook = lambda d: on_progress_gui(d, self.status_var)

        thread = threading.Thread(
            target=self.run_download,
            args=(url, self.status_var, progress_hook),
            daemon=True # El hilo se cerrará si la ventana principal se cierra
        )
        thread.start()
        self.check_thread(thread)

    def run_download(self, url, status_var, progress_hook):
        download_to_wav_gui(url, status_var, progress_hook)

    def check_thread(self, thread):
        if thread.is_alive():
            self.after(100, lambda: self.check_thread(thread))
        else:
            self.download_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    app = App()
    app.mainloop()
