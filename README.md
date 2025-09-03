# YouTube to WAV Downloader

A simple tool to download audio from YouTube videos and save it in WAV format. The project includes both a command-line interface (CLI) and a graphical user interface (GUI).

## Features

- **GUI Application:** A user-friendly window to paste a URL and download.
- **Command-Line Script:** For terminal-based usage.
- **Portable:** Includes `ffmpeg` and a launcher script (`.bat`) for easy execution on Windows without needing to modify system PATH variables.

## Requirements

- Python 3.x
- The `yt-dlp` library. Install it via pip:
  ```
  pip install yt-dlp
  ```

## How to Use

### Graphical Interface (Recommended)

1.  Go to the project directory.
2.  Double-click the `start_gui.bat` file.
3.  A window will open. Paste the YouTube URL into the text box and click the "Descargar" button.

Alternatively, you can run the GUI script from your terminal:
```
python yt_to_wav_gui.py
```

### Command-Line

Open a terminal in the project directory and use the following command, replacing `"URL_HERE"` with your YouTube video URL:

```
python yt_to_wav.py "URL_HERE"
```

## Output Files

The downloaded and converted `.wav` files will be saved in the `wav_output` directory.
