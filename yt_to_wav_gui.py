import tkinter as tk
from tkinter import ttk, messagebox
import threading
from pathlib import Path
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

# --- Lógica de descarga (adaptada para la GUI) ---

def download_to_wav_gui(url: str, status_var: tk.StringVar):
    """
    Descarga el audio de una URL y lo convierte a WAV.
    """
    try:
        out_dir = "wav_output"
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        script_dir = Path(__file__).parent
        ffmpeg_dir = script_dir / "ffmpeg-8.0-essentials_build" / "bin"

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(Path(out_dir) / "%(title)s.%(ext)s"),
            "noplaylist": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }],
            "quiet": True,
        }

        if ffmpeg_dir.exists():
            ydl_opts["ffmpeg_location"] = str(ffmpeg_dir)

        status_var.set("Descargando y convirtiendo...")
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            status_var.set(f"¡Éxito! Conversión a WAV finalizada.")

    except DownloadError as e:
        error_message = f"Error: No se pudo procesar la URL."
        if "is not a valid URL" in str(e):
            error_message = f"Error: La URL no parece ser válida."
        elif "ffmpeg not found" in str(e):
            error_message = "Error: FFmpeg no encontrado."
        status_var.set(error_message)
    except Exception as e:
        status_var.set(f"Error inesperado: {e}")

# --- Aplicación GUI ---

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube to WAV Downloader")
        self.geometry("550x200")
        self.resizable(False, False)

        style = ttk.Style(self)
        style.theme_use('clam')

        self.url_label = ttk.Label(self, text="URL de YouTube:")
        self.url_label.pack(pady=(10, 0))

        self.url_entry = ttk.Entry(self, width=70)
        self.url_entry.pack(pady=5, padx=15)

        self.download_button = ttk.Button(self, text="Descargar y Convertir a WAV", command=self.start_download_thread)
        self.download_button.pack(pady=10)

        self.progress_bar = ttk.Progressbar(self, orient='horizontal', length=400, mode='determinate')
        self.progress_bar.pack(pady=5)

        self.status_var = tk.StringVar()
        self.status_var.set("Listo para descargar.")
        self.status_label = ttk.Label(self, textvariable=self.status_var, wraplength=500)
        self.status_label.pack(pady=(5, 10), padx=10)
        
        self.animation_job = None

    def animate_progress(self, step=0):
        if step <= 100:
            self.progress_bar['value'] = step
            self.animation_job = self.after(15, lambda: self.animate_progress(step + 1))
        else:
            self.progress_bar['value'] = 100

    def start_download_thread(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showwarning("URL Vacía", "Por favor, introduce una URL de YouTube.")
            return

        self.download_button.config(state=tk.DISABLED)
        self.status_var.set("Iniciando...")
        self.progress_bar['value'] = 0
        if self.animation_job:
            self.after_cancel(self.animation_job)
        self.animate_progress()

        thread = threading.Thread(
            target=self.run_download,
            args=(url, self.status_var),
            daemon=True
        )
        thread.start()
        self.check_thread(thread)

    def run_download(self, url, status_var):
        download_to_wav_gui(url, status_var)

    def check_thread(self, thread):
        if thread.is_alive():
            self.after(100, lambda: self.check_thread(thread))
        else:
            if self.animation_job:
                self.after_cancel(self.animation_job)
            self.progress_bar['value'] = 100
            self.download_button.config(state=tk.NORMAL)
            final_status = self.status_var.get()
            if final_status.startswith("¡Éxito!"):
                messagebox.showinfo("Éxito", final_status)
            elif final_status.startswith("Error:"):
                messagebox.showerror("Error", final_status)
            
            self.status_var.set("Listo para descargar.")
            self.after(500, lambda: self.progress_bar.config(value=0))

if __name__ == "__main__":
    app = App()
    app.mainloop()