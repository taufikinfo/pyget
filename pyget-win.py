import os
import requests
import tkinter as tk
from tkinter import ttk, filedialog
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import json
from urllib.parse import urlsplit

def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.{decimal_places}f} {unit}"
        size /= 1024

def human_readable_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{int(hours)} hours, {int(minutes)} minutes"
    elif minutes > 0:
        return f"{int(minutes)} minutes, {int(seconds)} seconds"
    else:
        return f"{int(seconds)} seconds"

class Downloader:
    def __init__(self, url, filename, num_splits=8, chunk_size=1024*1024):
        self.url = url
        self.filename = filename
        self.num_splits = num_splits
        self.chunk_size = chunk_size
        self.total_size = 0
        self.downloaded = 0
        self.split_sizes = []
        self.parts = []
        self.part_progress = {}
        self.start_time = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.progress_file = f"{self.filename}.progress"

    def get_total_size(self):
        response = requests.head(self.url)
        self.total_size = int(response.headers.get('content-length', 0))
        return self.total_size

    def determine_optimal_settings(self):
        total_size = self.get_total_size()
        # Increase the number of splits for large files
        if total_size < 100 * 1024 * 1024:  # Less than 100 MB
            self.num_splits = 4
        elif total_size < 1 * 1024 * 1024 * 1024:  # Less than 1 GB
            self.num_splits = 8
        else:  # 1 GB and above
            self.num_splits = 16
        # Optimize chunk size
        self.chunk_size = min(4 * 1024 * 1024, total_size // self.num_splits)  # Max 4 MB chunks or equal chunks based on splits

    def load_progress(self):
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                self.part_progress = json.load(f)
            # Ensure all splits are accounted for in progress
            for i in range(self.num_splits):
                if str(i) not in self.part_progress:
                    self.part_progress[str(i)] = 0
        else:
            self.part_progress = {str(i): 0 for i in range(self.num_splits)}

    def save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump(self.part_progress, f)

    def download_split(self, start, end, part_file, split_index, progress_callback=None, status_callback=None, time_callback=None):
        current_start = start + self.part_progress[str(split_index)]
        if current_start >= end:
            return  # This part is already complete

        headers = {'Range': f'bytes={current_start}-{end}'}
        response = requests.get(self.url, headers=headers, stream=True)

        with open(part_file, 'ab') as f:
            for data in response.iter_content(chunk_size=self.chunk_size):
                if self.stop_event.is_set():
                    return
                while self.pause_event.is_set():
                    self.pause_event.wait()
                f.write(data)
                self.part_progress[str(split_index)] += len(data)
                self.save_progress()
                if progress_callback:
                    self.downloaded += len(data)
                    progress_callback(split_index, len(data), end - start + 1)
                if status_callback:
                    status_callback(f"Downloading part {split_index + 1}/{self.num_splits}: {self.part_progress[str(split_index)] / (end - start + 1) * 100:.2f}%")
                if time_callback:
                    elapsed_time = time.time() - self.start_time
                    if self.downloaded > 0:
                        estimated_total_time = (self.total_size / self.downloaded) * elapsed_time
                        remaining_time = estimated_total_time - elapsed_time
                        time_callback(remaining_time)

    def merge_files(self):
        with open(self.filename, 'wb') as outfile:
            for part_file in self.parts:
                with open(part_file, 'rb') as infile:
                    outfile.write(infile.read())
                os.remove(part_file)

    def download(self, progress_callback=None, status_callback=None, time_callback=None):
        self.load_progress()
        self.start_time = time.time()
        split_size = self.total_size // self.num_splits

        self.parts = [f"{self.filename}.part{i}" for i in range(self.num_splits)]
        self.split_sizes = [(i * split_size, (i + 1) * split_size - 1 if i < self.num_splits - 1 else self.total_size - 1) for i in range(self.num_splits)]

        with ThreadPoolExecutor(max_workers=self.num_splits) as executor:
            futures = []
            for i, (start, end) in enumerate(self.split_sizes):
                part_file = self.parts[i]
                futures.append(executor.submit(self.download_split, start, end, part_file, i, progress_callback, status_callback, time_callback))

            for future in as_completed(futures):
                future.result()

        if not self.stop_event.is_set():
            self.merge_files()
            if status_callback:
                status_callback("Download Complete")
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)

class DownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("File Downloader")

        self.url_label = tk.Label(root, text="URL:")
        self.url_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)

        self.url_entry = tk.Entry(root, width=50)
        self.url_entry.grid(row=0, column=1, padx=5, pady=5)

        self.file_label = tk.Label(root, text="Save As:")
        self.file_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)

        self.file_entry = tk.Entry(root, width=50)
        self.file_entry.grid(row=1, column=1, padx=5, pady=5)

        self.browse_button = tk.Button(root, text="Browse", command=self.browse_file)
        self.browse_button.grid(row=1, column=2, padx=5, pady=5)

        self.split_label = tk.Label(root, text="Number of Splits:")
        self.split_label.grid(row=2, column=0, padx=5, pady=5, sticky=tk.E)

        self.split_entry = tk.Entry(root, width=10)
        self.split_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        self.chunk_label = tk.Label(root, text="Chunk Size (KB):")
        self.chunk_label.grid(row=3, column=0, padx=5, pady=5, sticky=tk.E)

        self.chunk_entry = tk.Entry(root, width=10)
        self.chunk_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        self.recommend_button = tk.Button(root, text="Recommend Download", command=self.recommend_download)
        self.recommend_button.grid(row=4, column=0, padx=5, pady=5)

        self.download_button = tk.Button(root, text="Download", command=self.start_download)
        self.download_button.grid(row=4, column=1, padx=5, pady=5)

        self.cancel_button = tk.Button(root, text="Cancel", command=self.cancel_download)
        self.cancel_button.grid(row=4, column=2, padx=5, pady=5)

        self.resume_button = tk.Button(root, text="Resume", command=self.resume_download)
        self.resume_button.grid(row=4, column=3, padx=5, pady=5)

        self.status_label = tk.Label(root, text="Status: Waiting")
        self.status_label.grid(row=5, column=0, columnspan=4, padx=5, pady=5)

        self.total_size_label = tk.Label(root, text="Total size: N/A")
        self.total_size_label.grid(row=6, column=0, columnspan=4, padx=5, pady=5)

        self.time_label = tk.Label(root, text="Estimated time remaining: N/A")
        self.time_label.grid(row=7, column=0, columnspan=4, padx=5, pady=5)

        self.canvas = tk.Canvas(root)
        self.scroll_y = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll_y.set)

        self.canvas.grid(row=8, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")
        self.scroll_y.grid(row=8, column=4, pady=5, sticky="ns")

        self.progress_bars = []
        self.progress_labels = []
        self.downloader = None
        self.download_thread = None

    def browse_file(self):
        url = self.url_entry.get()
        filename = self.file_entry.get()
        if url:
            url_path = urlsplit(url).path
            suggested_filename = os.path.basename(url_path)
            filename = filedialog.asksaveasfilename(initialfile=suggested_filename)
            if filename:
                self.file_entry.delete(0, tk.END)
                self.file_entry.insert(0, filename)

    def recommend_download(self):
        url = self.url_entry.get()
        if url:
            self.downloader = Downloader(url, "")
            self.downloader.determine_optimal_settings()
            total_size = self.downloader.get_total_size()
            num_splits = self.downloader.num_splits
            chunk_size = self.downloader.chunk_size // 1024  # Convert to KB

            self.total_size_label.config(text=f"Total size: {human_readable_size(total_size)}")
            self.split_entry.delete(0, tk.END)
            self.split_entry.insert(0, num_splits)
            self.chunk_entry.delete(0, tk.END)
            self.chunk_entry.insert(0, chunk_size)

    def start_download(self):
        url = self.url_entry.get()
        filename = self.file_entry.get()

        if url and filename:
            num_splits = int(self.split_entry.get())
            chunk_size = int(self.chunk_entry.get()) * 1024  # Convert to bytes

            self.downloader = Downloader(url, filename, num_splits, chunk_size)
            total_size = self.downloader.get_total_size()

            # Update total size label
            self.total_size_label.config(text=f"Total size: {human_readable_size(total_size)}")

            # Clear old progress bars and labels
            for pb in self.progress_bars:
                pb.destroy()
            for lbl in self.progress_labels:
                lbl.destroy()
            self.progress_bars = []
            self.progress_labels = []

            # Create new progress bars and labels
            for i in range(num_splits):
                part_size = total_size // num_splits
                lbl = tk.Label(self.scroll_frame, text=f"Part {i + 1} - Size: {human_readable_size(part_size)}, Downloaded: 0 bytes (0.00%)", anchor="w")
                lbl.grid(row=i, column=0, padx=5, pady=2, sticky="w")
                pb = ttk.Progressbar(self.scroll_frame, orient="horizontal", length=400, mode="determinate", maximum=part_size)
                pb.grid(row=i, column=1, padx=5, pady=2, sticky="w")
                self.progress_labels.append(lbl)
                self.progress_bars.append(pb)

            def update_progress(split_index, chunk_size, part_size):
                self.progress_bars[split_index]["value"] += chunk_size
                downloaded = self.progress_bars[split_index]["value"]
                percentage = (downloaded / part_size) * 100
                self.progress_labels[split_index].config(text=f"Part {split_index + 1} - Size: {human_readable_size(part_size)}, Downloaded: {human_readable_size(downloaded)} ({percentage:.2f}%)")
                self.root.update_idletasks()

            def update_status(message):
                self.status_label.config(text=message)
                self.root.update_idletasks()
                if "Download Complete" in message:
                    for pb in self.progress_bars:
                        pb["value"] = 0

            def update_time_remaining(remaining_time):
                if remaining_time > 0:
                    self.time_label.config(text=f"Estimated time remaining: {human_readable_time(remaining_time)}")
                else:
                    self.time_label.config(text="Estimated time remaining: Calculating...")
                self.root.update_idletasks()

            self.status_label.config(text="Status: Downloading...")

            def threaded_download():
                self.downloader.download(progress_callback=update_progress, status_callback=update_status, time_callback=update_time_remaining)

            self.download_thread = threading.Thread(target=threaded_download)
            self.download_thread.start()

    def cancel_download(self):
        if self.downloader:
            self.downloader.stop_event.set()
            self.status_label.config(text="Status: Download Cancelled")

    def resume_download(self):
        url = self.url_entry.get()
        filename = self.file_entry.get()

        if url and filename:
            num_splits = int(self.split_entry.get())
            chunk_size = int(self.chunk_entry.get()) * 1024  # Convert to bytes

            self.downloader = Downloader(url, filename, num_splits, chunk_size)
            self.downloader.load_progress()

            total_size = self.downloader.get_total_size()

            # Update total size label
            self.total_size_label.config(text=f"Total size: {human_readable_size(total_size)}")

            # Clear old progress bars and labels
            for pb in self.progress_bars:
                pb.destroy()
            for lbl in self.progress_labels:
                lbl.destroy()
            self.progress_bars = []
            self.progress_labels = []

            # Create new progress bars and labels
            for i in range(num_splits):
                part_size = total_size // num_splits
                downloaded = self.downloader.part_progress.get(str(i), 0)
                percentage = (downloaded / part_size) * 100
                lbl = tk.Label(self.scroll_frame, text=f"Part {i + 1} - Size: {human_readable_size(part_size)}, Downloaded: {human_readable_size(downloaded)} ({percentage:.2f}%)", anchor="w")
                lbl.grid(row=i, column=0, padx=5, pady=2, sticky="w")
                pb = ttk.Progressbar(self.scroll_frame, orient="horizontal", length=400, mode="determinate", maximum=part_size)
                pb["value"] = downloaded
                pb.grid(row=i, column=1, padx=5, pady=2, sticky="w")
                self.progress_labels.append(lbl)
                self.progress_bars.append(pb)

            def update_progress(split_index, chunk_size, part_size):
                self.progress_bars[split_index]["value"] += chunk_size
                downloaded = self.progress_bars[split_index]["value"]
                percentage = (downloaded / part_size) * 100
                self.progress_labels[split_index].config(text=f"Part {split_index + 1} - Size: {human_readable_size(part_size)}, Downloaded: {human_readable_size(downloaded)} ({percentage:.2f}%)")
                self.root.update_idletasks()

            def update_status(message):
                self.status_label.config(text=message)
                self.root.update_idletasks()
                if "Download Complete" in message:
                    for pb in self.progress_bars:
                        pb["value"] = 0

            def update_time_remaining(remaining_time):
                if remaining_time > 0:
                    self.time_label.config(text=f"Estimated time remaining: {human_readable_time(remaining_time)}")
                else:
                    self.time_label.config(text="Estimated time remaining: Calculating...")
                self.root.update_idletasks()

            self.status_label.config(text="Status: Downloading...")

            def threaded_download():
                self.downloader.download(progress_callback=update_progress, status_callback=update_status, time_callback=update_time_remaining)

            self.download_thread = threading.Thread(target=threaded_download)
            self.download_thread.start()

    def pause_download(self):
        if self.downloader:
            self.downloader.pause_event.set()
            self.status_label.config(text="Status: Download Paused")

if __name__ == "__main__":
    root = tk.Tk()
    app = DownloaderGUI(root)
    root.mainloop()
