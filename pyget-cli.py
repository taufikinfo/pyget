import os
import requests
import argparse
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
    def __init__(self, url, filename, num_splits=None, chunk_size=None):
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
        # Determine the number of splits
        if total_size < 100 * 1024 * 1024:  # Less than 100 MB
            self.num_splits = 4
        elif total_size < 1 * 1024 * 1024 * 1024:  # Less than 1 GB
            self.num_splits = 8
        else:  # 1 GB and above
            self.num_splits = 16
        # Determine the chunk size
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

    def download_split(self, start, end, part_file, split_index):
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
                self.downloaded += len(data)
                print(f"Downloading part {split_index + 1}/{self.num_splits}: {self.part_progress[str(split_index)] / (end - start + 1) * 100:.2f}%")

    def merge_files(self):
        with open(self.filename, 'wb') as outfile:
            for part_file in self.parts:
                with open(part_file, 'rb') as infile:
                    outfile.write(infile.read())
                os.remove(part_file)

    def download(self):
        self.load_progress()
        self.start_time = time.time()
        split_size = self.total_size // self.num_splits

        self.parts = [f"{self.filename}.part{i}" for i in range(self.num_splits)]
        self.split_sizes = [(i * split_size, (i + 1) * split_size - 1 if i < self.num_splits - 1 else self.total_size - 1) for i in range(self.num_splits)]

        with ThreadPoolExecutor(max_workers=self.num_splits) as executor:
            futures = []
            for i, (start, end) in enumerate(self.split_sizes):
                part_file = self.parts[i]
                futures.append(executor.submit(self.download_split, start, end, part_file, i))

            for future in as_completed(futures):
                future.result()

        if not self.stop_event.is_set():
            self.merge_files()
            print("Download Complete")
            if os.path.exists(self.progress_file):
                os.remove(self.progress_file)

def main():
    parser = argparse.ArgumentParser(description="Download files in parallel.")
    parser.add_argument('url', help="URL of the file to download")
    parser.add_argument('filename', help="Name of the file to save as")
    parser.add_argument('--splits', type=int, help="Number of splits")
    parser.add_argument('--chunk_size', type=int, help="Chunk size in KB")

    args = parser.parse_args()

    url = args.url
    filename = args.filename

    downloader = Downloader(url, filename)
    total_size = downloader.get_total_size()
    print(f"Total size: {human_readable_size(total_size)}")

    if args.splits is None or args.chunk_size is None:
        downloader.determine_optimal_settings()
        if args.splits is not None:
            downloader.num_splits = args.splits
        if args.chunk_size is not None:
            downloader.chunk_size = args.chunk_size * 1024  # Convert to bytes
    else:
        downloader.num_splits = args.splits
        downloader.chunk_size = args.chunk_size * 1024  # Convert to bytes

    print(f"Using {downloader.num_splits} splits and {human_readable_size(downloader.chunk_size)} chunk size")

    downloader.download()

if __name__ == "__main__":
    main()
