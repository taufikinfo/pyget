
# PyGet - A Parallel File Downloader

PyGet is a parallel file downloader with both GUI and CLI versions. It allows you to download files by splitting them into multiple parts, improving download speed and reliability. PyGet supports downloading files from both YouTube and non-YouTube sources.

## Features

- Parallel downloads with customizable number of splits.
- GUI version with a progress bar for each part of the download.
- CLI version for command-line enthusiasts.
- Resumable downloads.
- Dynamic default values for splits and chunk size based on the file size.
- Supports downloading from YouTube and non-YouTube sources.

## Installation

### Prerequisites

- Python 3.6+
- `requests` library
- `tkinter` (for GUI version)
- `yt-dlp` (for YouTube downloads)
- `PyInstaller` (for creating executables)

You can install the necessary dependencies using pip:

```bash
pip install requests yt-dlp
```

### Creating Executables

#### GUI Version

1. Save the GUI script as `pyget-win.py`.
2. Create the executable:

    ```bash
    pyinstaller --onefile --windowed pyget-win.py
    ```

3. The executable will be located in the `dist` directory.

#### CLI Version

1. Save the CLI script as `pyget-cli.py`.
2. Create the executable:

    ```bash
    pyinstaller --onefile pyget-cli.py
    ```

3. The executable will be located in the `dist` directory.

## Usage

### GUI Version

1. Run the executable or the script directly using Python:

    ```bash
    python pyget-win.py
    ```

2. Choose the downloader mode (Single or Multiple).
3. Enter the URL(s) of the file(s) you want to download.
4. For Single Downloader mode:
    - Specify the location to save the file.
    - Optionally, adjust the number of splits and chunk size.
5. Click "Download" to start the download process.

### CLI Version

1. Run the executable or the script directly using Python:

    ```bash
    python pyget-cli.py <url> <filename> [--splits <num_splits>] [--chunk_size <chunk_size_kb>]
    ```

    - `<url>`: URL of the file to download.
    - `<filename>`: Name of the file to save as.
    - `--splits <num_splits>`: (Optional) Number of splits. Default is determined dynamically.
    - `--chunk_size <chunk_size_kb>`: (Optional) Chunk size in KB. Default is determined dynamically.

2. Example:

    ```bash
    python pyget-cli.py https://example.com/file.zip file.zip --splits 8 --chunk_size 1024
    ```

## Examples

### GUI Version

![PyGet v1.2.0 Example](./assets/PyGet.v1.2.0-04.08.2024_00.31.28_REC.gif)

### CLI Version

```bash
$ pyget-cli.exe https://example.com/file.zip file.zip
Total size: 150.00 MB
Using 8 splits and 4.00 MB chunk size
Downloading part 1/8: 12.50%
Downloading part 2/8: 25.00%
Downloading part 3/8: 37.50%
...
Download Complete
```

## Contributing

Contributions are welcome! Please fork the repository and submit pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
```

This Markdown snippet will display your GIF within the `README.md` file on GitHub, assuming the GIF file is located in the `assets` directory and named `PyGet.v1.2.0-04.08.2024_00.31.28_REC.gif`.