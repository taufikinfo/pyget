"""
PyGet - A Parallel File Downloader (GUI Version)
Author: TaufikInfo
License: MIT

This script provides a graphical user interface for downloading files in parallel.
It supports resumable downloads, dynamic adjustment of splits and chunk sizes, 
and displays progress for each part of the download.

Dependencies:
- requests
- tkinter
- threading
- concurrent.futures
- json
- time
- os
- urllib.parse

Usage:
1. Run the script: python pyget_win.py
2. Enter the URL of the file to download.
3. Specify the location to save the file.
4. Optionally, adjust the number of splits and chunk size.
5. Click "Download" to start the download process.
"""

import os
import requests
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import json
from urllib.parse import urlsplit
import yt_dlp
import re

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

def human_readable_speed(speed):
    mbps = (speed * 8) / (1024 * 1024)  # Convert bytes/s to Mbps
    return f"{mbps:.2f} Mbps"

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def extract_file_extension(url):
    path = urlsplit(url).path
    _, ext = os.path.splitext(path)
    return ext or ".bin"

class Downloader:
    def __init__(self, url, num_splits=8, chunk_size=1024*1024):
        self.url = url
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
        self.progress_file = None
        self.download_url = None
        self.filename = None

    def get_download_info(self):
        if "youtube.com" in self.url or "youtu.be" in self.url:
            ydl_opts = {'format': 'best'}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(self.url, download=False)
                self.download_url = info_dict.get('url', self.url)  # Use URL directly if no download URL is found
                self.filename = sanitize_filename(info_dict.get('title', 'download')) + ".mp4"
        else:
            self.download_url = self.url
            file_extension = extract_file_extension(self.url)
            path = urlsplit(self.url).path
            filename = os.path.basename(path) or 'download'
            self.filename = sanitize_filename(filename) + file_extension
        self.progress_file = f"{self.filename}.progress"
        self.total_size = int(requests.head(self.download_url).headers.get('Content-Length', 0))
        return self.download_url, self.filename

    def update_progress_file(self):
        self.progress_file = f"{self.filename}.progress"

    def determine_optimal_settings(self):
        total_size = self.total_size
        if total_size < 100 * 1024 * 1024:  # Less than 100 MB
            self.num_splits = 4
        elif total_size < 1 * 1024 * 1024 * 1024:  # Less than 1 GB
            self.num_splits = 8
        else:  # 1 GB and above
            self.num_splits = 16
        self.chunk_size = min(4 * 1024 * 1024, total_size // self.num_splits)  # Max 4 MB chunks or equal chunks based on splits

    def load_progress(self):
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                self.part_progress = json.load(f)
            for i in range(self.num_splits):
                if str(i) not in self.part_progress:
                    self.part_progress[str(i)] = 0
        else:
            self.part_progress = {str(i): 0 for i in range(self.num_splits)}

    def save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump(self.part_progress, f)

    def download_split(self, start, end, part_file, split_index, progress_callback=None, status_callback=None, time_callback=None, speed_callback=None):
        current_start = start + self.part_progress[str(split_index)]
        if current_start >= end:
            return
        headers = {'Range': f'bytes={current_start}-{end}'}
        response = requests.get(self.download_url, headers=headers, stream=True)
        bytes_downloaded = 0
        start_time = time.time()  # Local start time for this split
        with open(part_file, 'ab') as f:
            for data in response.iter_content(chunk_size=self.chunk_size):
                if self.stop_event.is_set():
                    return
                while self.pause_event.is_set():
                    self.pause_event.wait()
                f.write(data)
                bytes_downloaded += len(data)
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
                if speed_callback:
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 0:
                        speed_callback(bytes_downloaded / elapsed_time)

    def merge_files(self):
        with open(self.filename, 'wb') as outfile:
            for part_file in self.parts:
                if os.path.exists(part_file):
                    with open(part_file, 'rb') as infile:
                        outfile.write(infile.read())
                    os.remove(part_file)

    def download(self, progress_callback=None, status_callback=None, time_callback=None, speed_callback=None):
        self.load_progress()
        self.start_time = time.time()
        split_size = self.total_size // self.num_splits
        self.parts = [f"{self.filename}.part{i}" for i in range(self.num_splits)]
        self.split_sizes = [(i * split_size, (i + 1) * split_size - 1 if i < self.num_splits - 1 else self.total_size - 1) for i in range(self.num_splits)]
        with ThreadPoolExecutor(max_workers=self.num_splits) as executor:
            futures = []
            for i, (start, end) in enumerate(self.split_sizes):
                part_file = self.parts[i]
                futures.append(executor.submit(self.download_split, start, end, part_file, i, progress_callback, status_callback, time_callback, speed_callback))
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
        self.root.title("PyGet v1.2.0")
        self.url_queue = []

        self.mode_var = tk.StringVar(value="single")
        self.single_mode_radio = tk.Radiobutton(root, text="Single Downloader", variable=self.mode_var, value="single", command=self.update_mode)
        self.single_mode_radio.grid(row=0, column=0, padx=5, pady=5)
        self.multi_mode_radio = tk.Radiobutton(root, text="Multiple Downloader", variable=self.mode_var, value="multi", command=self.update_mode)
        self.multi_mode_radio.grid(row=0, column=1, padx=5, pady=5)

        self.url_label = tk.Label(root, text="URL:")
        self.url_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        self.url_entry = tk.Entry(root, width=50)
        self.url_entry.grid(row=1, column=1, padx=5, pady=5)
        self.add_url_button = tk.Button(root, text="Add URL", command=self.add_url)
        self.add_url_button.grid(row=1, column=2, padx=5, pady=5)
        self.del_url_button = tk.Button(root, text="Del URL", command=self.del_url)
        self.del_url_button.grid(row=1, column=3, padx=5, pady=5)

        self.url_listbox = tk.Listbox(root, height=5)
        self.url_listbox.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")

        self.file_label = tk.Label(root, text="Save As:")
        self.file_label.grid(row=3, column=0, padx=5, pady=5, sticky=tk.E)
        self.file_entry = tk.Entry(root, width=50)
        self.file_entry.grid(row=3, column=1, padx=5, pady=5)
        self.browse_button = tk.Button(root, text="Browse", command=self.browse_file)
        self.browse_button.grid(row=3, column=2, padx=5, pady=5)

        self.split_label = tk.Label(root, text="Number of Splits:")
        self.split_label.grid(row=4, column=0, padx=5, pady=5, sticky=tk.E)
        self.split_entry = tk.Entry(root, width=10)
        self.split_entry.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)

        self.chunk_label = tk.Label(root, text="Chunk Size (KB):")
        self.chunk_label.grid(row=5, column=0, padx=5, pady=5, sticky=tk.E)
        self.chunk_entry = tk.Entry(root, width=10)
        self.chunk_entry.grid(row=5, column=1, padx=5, pady=5, sticky=tk.W)

        self.recommend_button = tk.Button(root, text="Recommend Download", command=self.recommend_download)
        self.recommend_button.grid(row=6, column=0, padx=5, pady=5)
        self.download_button = tk.Button(root, text="Download", command=self.start_download)
        self.download_button.grid(row=6, column=1, padx=5, pady=5)
        self.cancel_button = tk.Button(root, text="Cancel", command=self.cancel_download)
        self.cancel_button.grid(row=6, column=2, padx=5, pady=5)
        self.resume_button = tk.Button(root, text="Resume", command=self.resume_download)
        self.resume_button.grid(row=6, column=3, padx=5, pady=5)
        self.clear_button = tk.Button(root, text="Clear", command=self.clear_fields)
        self.clear_button.grid(row=6, column=4, padx=5, pady=5)

        self.status_label = tk.Label(root, text="Status: Waiting")
        self.status_label.grid(row=7, column=0, columnspan=5, padx=5, pady=5)
        self.total_size_label = tk.Label(root, text="Total size: N/A")
        self.total_size_label.grid(row=8, column=0, columnspan=5, padx=5, pady=5)
        self.time_label = tk.Label(root, text="Estimated time remaining: N/A")
        self.time_label.grid(row=9, column=0, columnspan=5, padx=5, pady=5)
        self.speed_label = tk.Label(root, text="Speed: N/A")
        self.speed_label.grid(row=10, column=0, columnspan=5, padx=5, pady=5)

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
        self.canvas.grid(row=11, column=0, columnspan=5, padx=5, pady=5, sticky="nsew")
        self.scroll_y.grid(row=11, column=5, pady=5, sticky="ns")

        self.progress_bars = []
        self.progress_labels = []
        self.downloader = None
        self.download_thread = None
        self.current_speed = 0  # Track current speed for display

        self.update_mode()

    def update_mode(self):
        mode = self.mode_var.get()
        if mode == "single":
            self.add_url_button.config(state=tk.DISABLED)
            self.del_url_button.config(state=tk.DISABLED)
            self.url_listbox.config(state=tk.DISABLED)
            self.browse_button.config(state=tk.NORMAL)
            self.file_entry.config(state=tk.NORMAL)
            self.split_entry.config(state=tk.NORMAL)
            self.chunk_entry.config(state=tk.NORMAL)
            self.recommend_button.config(state=tk.NORMAL)
        elif mode == "multi":
            self.add_url_button.config(state=tk.NORMAL)
            self.del_url_button.config(state=tk.NORMAL)
            self.url_listbox.config(state=tk.NORMAL)
            self.browse_button.config(state=tk.DISABLED)
            self.file_entry.config(state=tk.DISABLED)
            self.split_entry.config(state=tk.DISABLED)
            self.chunk_entry.config(state=tk.DISABLED)
            self.recommend_button.config(state=tk.DISABLED)

    def add_url(self):
        url = self.url_entry.get()
        if url:
            self.url_queue.append(url)
            self.url_listbox.insert(tk.END, url)
            self.url_entry.delete(0, tk.END)

    def del_url(self):
        selected = self.url_listbox.curselection()
        if selected:
            index = selected[0]
            del self.url_queue[index]
            self.url_listbox.delete(index)

    def browse_file(self):
        url = self.url_entry.get()
        if url:
            self.downloader = Downloader(url)
            self.downloader.get_download_info()
            filename = self.downloader.filename
            save_path = filedialog.asksaveasfilename(initialfile=filename)
            if save_path:
                save_path = os.path.join(os.getcwd(), os.path.basename(save_path))
                self.downloader.filename = save_path  # Update the filename
                self.downloader.update_progress_file()  # Update the progress file name
                self.file_entry.delete(0, tk.END)
                self.file_entry.insert(0, save_path)

    def recommend_download(self):
        url = self.url_entry.get()
        if url:
            self.downloader = Downloader(url)
            self.downloader.get_download_info()
            self.downloader.determine_optimal_settings()
            total_size = self.downloader.total_size
            num_splits = self.downloader.num_splits
            chunk_size = self.downloader.chunk_size // 1024  # Convert to KB
            self.total_size_label.config(text=f"Total size: {self.downloader.filename} - {human_readable_size(total_size)}")
            self.split_entry.delete(0, tk.END)
            self.split_entry.insert(0, num_splits)
            self.chunk_entry.delete(0, tk.END)
            self.chunk_entry.insert(0, chunk_size)

    def start_download(self):
        if self.mode_var.get() == "single":
            url = self.url_entry.get()
            if not url:
                messagebox.showerror("Error", "No URL provided.")
                return
            self.downloader = Downloader(url)
            self.downloader.get_download_info()
            num_splits = int(self.split_entry.get())
            chunk_size = int(self.chunk_entry.get()) * 1024  # Convert to bytes
            self.downloader.num_splits = num_splits
            self.downloader.chunk_size = chunk_size
            self.total_size_label.config(text=f"Total size: {self.downloader.filename} - {human_readable_size(self.downloader.total_size)}")

            self.clear_progress_bars()
            for i in range(num_splits):
                part_size = self.downloader.total_size // num_splits
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
                    self.clear_progress_bars()
                    self.total_size_label.grid_remove()  # Hide total size label
                    self.time_label.grid_remove()  # Hide estimated time remaining label
                    self.speed_label.grid_remove()  # Hide speed label

            def update_time_remaining(remaining_time):
                if remaining_time > 0:
                    self.time_label.config(text=f"Estimated time remaining: {human_readable_time(remaining_time)}")
                else:
                    self.time_label.config(text="Estimated time remaining: Calculating...")
                self.root.update_idletasks()

            def update_speed(speed):
                self.current_speed = speed
                self.speed_label.config(text=f"Speed: {human_readable_speed(speed)}")

            self.status_label.config(text="Status: Downloading...")

            def threaded_download():
                self.downloader.download(progress_callback=update_progress, status_callback=update_status, time_callback=update_time_remaining, speed_callback=update_speed)

            self.download_thread = threading.Thread(target=threaded_download)
            self.download_thread.start()

        elif self.mode_var.get() == "multi":
            if len(self.url_queue) == 0:
                messagebox.showerror("Error", "No URLs to download.")
                return

            def download_queue():
                for url in self.url_queue:
                    self.downloader = Downloader(url)
                    self.downloader.get_download_info()
                    self.downloader.determine_optimal_settings()
                    num_splits = self.downloader.num_splits
                    chunk_size = self.downloader.chunk_size // 1024  # Convert to KB
                    total_size = self.downloader.total_size
                    self.total_size_label.config(text=f"Total size: {self.downloader.filename} - {human_readable_size(total_size)}")
                    self.clear_progress_bars()
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

                    def update_speed(speed):
                        self.current_speed = speed
                        self.speed_label.config(text=f"Speed: {human_readable_speed(speed)}")

                    self.status_label.config(text="Status: Downloading...")

                    def threaded_download():
                        self.downloader.download(progress_callback=update_progress, status_callback=update_status, time_callback=update_time_remaining, speed_callback=update_speed)

                    self.download_thread = threading.Thread(target=threaded_download)
                    self.download_thread.start()
                    self.download_thread.join()  # Wait for the current download to complete

                self.clear_progress_bars()  # Clear progress bars after all downloads are complete
                self.total_size_label.grid_remove()  # Hide total size label
                self.time_label.grid_remove()  # Hide estimated time remaining label
                self.speed_label.grid_remove()  # Hide speed label

            self.download_thread = threading.Thread(target=download_queue)
            self.download_thread.start()

    def clear_progress_bars(self):
        for pb in self.progress_bars:
            pb.destroy()
        for lbl in self.progress_labels:
            lbl.destroy()
        self.progress_bars = []
        self.progress_labels = []

    def cancel_download(self):
        if self.downloader:
            self.downloader.stop_event.set()
            self.status_label.config(text="Status: Download Cancelled")

    def resume_download(self):
        if self.downloader:
            self.downloader.stop_event.clear()  # Clear the stop event to resume the download
            self.downloader.pause_event.clear()  # Clear the pause event if it was set

            total_size = self.downloader.total_size
            num_splits = self.downloader.num_splits
            chunk_size = self.downloader.chunk_size // 1024  # Convert to KB
            self.total_size_label.config(text=f"Total size: {self.downloader.filename} - {human_readable_size(total_size)}")
            for pb in self.progress_bars:
                pb.destroy()
            for lbl in self.progress_labels:
                lbl.destroy()
            self.progress_bars = []
            self.progress_labels = []
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

            def update_speed(speed):
                self.current_speed = speed
                self.speed_label.config(text=f"Speed: {human_readable_speed(speed)}")

            self.status_label.config(text="Status: Resuming...")

            def threaded_resume_download():
                self.downloader.download(progress_callback=update_progress, status_callback=update_status, time_callback=update_time_remaining, speed_callback=update_speed)

            self.download_thread = threading.Thread(target=threaded_resume_download)
            self.download_thread.start()

    def clear_fields(self):
        self.url_entry.delete(0, tk.END)
        self.file_entry.delete(0, tk.END)
        self.split_entry.delete(0, tk.END)
        self.chunk_entry.delete(0, tk.END)
        self.status_label.config(text="Status: Waiting")
        self.total_size_label.config(text="Total size: N/A")
        self.time_label.config(text="Estimated time remaining: N/A")
        self.speed_label.config(text="Speed: N/A")
        self.clear_progress_bars()
        self.url_queue = []
        self.url_listbox.delete(0, tk.END)
        self.recommend_button.config(state=tk.NORMAL)
        self.split_entry.config(state=tk.NORMAL)
        self.chunk_entry.config(state=tk.NORMAL)
        self.total_size_label.grid()  # Show total size label again
        self.time_label.grid()  # Show estimated time remaining label again
        self.speed_label.grid()  # Show speed label again
        self.update_mode()  # Reset mode settings

if __name__ == "__main__":
    root = tk.Tk()
    app = DownloaderGUI(root)
    root.mainloop()
