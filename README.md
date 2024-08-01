# PyGet - A Parallel File Downloader

PyGet is a parallel file downloader with both GUI and CLI versions. It allows you to download files by splitting them into multiple parts, improving download speed and reliability.

## Features

- Parallel downloads with customizable number of splits.
- GUI version with a progress bar for each part of the download.
- CLI version for command-line enthusiasts.
- Resumable downloads.
- Dynamic default values for splits and chunk size based on the file size.

## Installation

### Prerequisites

- Python 3.6+
- `requests` library
- `tkinter` (for GUI version)
- `PyInstaller` (for creating executables)

You can install the necessary dependencies using pip:

```bash
pip install requests
