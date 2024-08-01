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
```

### Creating Executables

#### GUI Version

1. Save the GUI script as `pyget_win.py`.
2. Create the executable:

    ```bash
    pyinstaller --onefile --windowed pyget_win.py
    ```

3. The executable will be located in the `dist` directory.

#### CLI Version

1. Save the CLI script as `pyget_cli.py`.
2. Create the executable:

    ```bash
    pyinstaller --onefile pyget_cli.py
    ```

3. The executable will be located in the `dist` directory.

## Usage

### GUI Version

1. Run the executable or the script directly using Python:

    ```bash
    python pyget_win.py
    ```

2. Enter the URL of the file you want to download.
3. Specify the location to save the file.
4. Optionally, adjust the number of splits and chunk size.
5. Click "Download" to start the download process.

### CLI Version

1. Run the executable or the script directly using Python:

    ```bash
    python pyget_cli.py <url> <filename> [--splits <num_splits>] [--chunk_size <chunk_size_kb>]
    ```

    - `<url>`: URL of the file to download.
    - `<filename>`: Name of the file to save as.
    - `--splits <num_splits>`: (Optional) Number of splits. Default is determined dynamically.
    - `--chunk_size <chunk_size_kb>`: (Optional) Chunk size in KB. Default is determined dynamically.

2. Example:

    ```bash
    python pyget_cli.py https://example.com/file.zip file.zip --splits 8 --chunk_size 1024
    ```

## Examples

### GUI Version

![GUI Example](./assets/gui_example.png)

### CLI Version

```bash
$ pyget_cli.exe https://example.com/file.zip file.zip
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

### Additional Notes

1. **Screenshots**: If you have screenshots of the GUI version, you can include them in the `assets` directory and reference them in the README.
2. **LICENSE**: Add a `LICENSE` file if you haven't already.
3. **Customization**: Adjust the text to better match your project details, such as specific features or usage instructions.

### GitHub Repository Structure

Here’s a suggested structure for your GitHub repository:

```
pyget/
├── assets/
│   └── gui_example.png  # Add screenshots here
├── dist/
│   └── pyget_cli.exe
│   └── pyget_win.exe
├── pyget_cli.py
├── pyget_win.py
├── LICENSE
└── README.md
```

### Instructions for the Users

Users can follow the instructions in the README to set up, run, and contribute to the project. The provided examples and usage instructions will help them understand how to use both the GUI and CLI versions of PyGet.

By providing a comprehensive README, you make it easier for others to use and contribute to your project, enhancing its utility and reach.