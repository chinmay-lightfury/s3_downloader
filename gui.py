import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
from datetime import datetime
from settings_manager import load_settings, save_settings
from s3_operations import S3Handler
import darkdetect

class S3DownloaderGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AWS S3 Downloader")
        self.root.geometry("1000x600")
        self.root.minsize(800, 500)
        
        # Set theme based on system
        self.style = ttk.Style()
        if darkdetect.isDark():
            self.style.theme_use('clam')
            self.bg_color = '#2b2b2b'
            self.fg_color = '#ffffff'
        else:
            self.style.theme_use('clam')
            self.bg_color = '#ffffff'
            self.fg_color = '#000000'

        self.root.configure(bg=self.bg_color)
        
        self.s3_handler = S3Handler()
        self.download_thread = None
        self.cancel_download = threading.Event()
        self.current_bucket = None
        self.current_prefix = ''
        self.current_path = []  # Add breadcrumb tracking
        
        self._create_gui()
        
        try:
            self.s3_handler.initialize_client()
            self.update_bucket_dropdown()
        except Exception as e:
            messagebox.showwarning("Warning", str(e))

    def _create_gui(self):
        self._create_menu()
        
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bucket selection
        bucket_frame = ttk.LabelFrame(left_panel, text="S3 Bucket")
        bucket_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.bucket_var = tk.StringVar()
        self.bucket_combo = ttk.Combobox(bucket_frame, textvariable=self.bucket_var)
        self.bucket_combo.pack(fill=tk.X, padx=5, pady=5)
        self.bucket_combo.bind("<<ComboboxSelected>>", self.on_bucket_select)
        
        # Path navigation
        nav_frame = ttk.Frame(left_panel)
        nav_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(nav_frame, text="↑ Up", command=self._go_up).pack(side=tk.LEFT, padx=5)
        self.path_label = ttk.Label(nav_frame, text="/")
        self.path_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Search frame
        search_frame = ttk.Frame(left_panel)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._filter_tree)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Tree view
        tree_frame = ttk.Frame(left_panel)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree = ttk.Treeview(tree_frame, selectmode='extended')
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree["columns"] = ("size", "last_modified")
        self.tree.column("#0", width=300, stretch=tk.YES)
        self.tree.column("size", width=100, anchor='e')
        self.tree.column("last_modified", width=150, anchor='w')
        
        self.tree.heading("#0", text="Name")
        self.tree.heading("size", text="Size")
        self.tree.heading("last_modified", text="Last Modified")
        
        self.tree.bind('<Double-1>', self._on_tree_double_click)
        
        # Right panel
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        
        # Download frame
        download_frame = ttk.LabelFrame(right_panel, text="Download")
        download_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(download_frame, text="Download Selected", 
                  command=self.on_download_selected).pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(download_frame, variable=self.progress_var)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(download_frame, text="Cancel", 
                  command=self.on_cancel_download).pack(fill=tk.X, padx=5, pady=5)

    def _filter_tree(self, *args):
        search_term = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        self._populate_tree(self.current_bucket, self.current_prefix, search_term)

    def _populate_tree(self, bucket_name, prefix='', search_term=''):
        if not bucket_name:
            return
            
        self.tree.delete(*self.tree.get_children())
        folders, files = self.s3_handler.list_objects(bucket_name, prefix)
        
        # Add folders
        for folder in folders:
            folder_name = folder.split('/')[-2]  # Get last folder name
            if search_term and search_term not in folder_name.lower():
                continue
            self.tree.insert("", "end", folder, text=folder_name,
                           values=("-", "-"), tags=('folder',))
        
        # Add files
        for file in files:
            file_name = os.path.basename(file['key'])
            if search_term and search_term not in file_name.lower():
                continue
            # Format size and date
            size = self._format_size(file['size'])
            date = file['last_modified'].strftime('%Y-%m-%d %H:%M')
            self.tree.insert("", "end", file['key'], text=file_name,
                           values=(size, date), tags=('file',))

    def _format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _create_menu(self):
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)
        settings_menu = tk.Menu(menu)
        menu.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="AWS Settings", command=self.open_settings_window)

    def open_settings_window(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("AWS Settings")
        settings_window.geometry("300x300")
        settings_window.resizable(False, False)

        # Create settings form
        settings = load_settings()
        
        fields = [
            ("Access Key ID:", 'AWS_ACCESS_KEY_ID', ''),
            ("Secret Access Key:", 'AWS_ACCESS_SECRET_KEY', '*'),
            ("Session Token:", 'AWS_SESSION_TOKEN', '*'),
            ("Region:", 'AWS_REGION', '')
        ]
        
        entries = {}
        for label_text, key, show in fields:
            tk.Label(settings_window, text=label_text).pack(pady=5)
            entry = tk.Entry(settings_window, width=40, show=show if show else None)
            entry.insert(0, settings.get(key, ''))
            entry.pack(pady=5)
            entries[key] = entry

        def save_and_close():
            new_settings = {key: entry.get() for key, entry in entries.items()}
            save_settings(new_settings)
            settings_window.destroy()
            try:
                self.s3_handler.initialize_client()
                self.update_bucket_dropdown()
                messagebox.showinfo("Success", "AWS credentials are valid and connection is successful.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(settings_window, text="Save", command=save_and_close).pack(pady=10)

    def update_bucket_dropdown(self):
        buckets = self.s3_handler.list_buckets()
        self.bucket_combo['values'] = buckets

    def on_bucket_select(self, event):
        selected_bucket = self.bucket_var.get()
        self.current_bucket = selected_bucket
        self.current_prefix = ''
        self.current_path = []
        self._update_path_label()
        self._populate_tree(selected_bucket)

    def _on_tree_double_click(self, event):
        item = self.tree.selection()[0]
        if 'folder' in self.tree.item(item)['tags']:
            self.current_prefix = item
            self.current_path.append(self.tree.item(item)['text'])
            self._update_path_label()
            self._populate_tree(self.current_bucket, self.current_prefix)

    def _go_up(self):
        if not self.current_path:
            return
            
        self.current_path.pop()
        if not self.current_path:
            self.current_prefix = ''
        else:
            # Reconstruct prefix from path
            self.current_prefix = '/'.join(self.current_path) + '/'
            
        self._update_path_label()
        self._populate_tree(self.current_bucket, self.current_prefix)

    def _update_path_label(self):
        path_text = '/' + '/'.join(self.current_path)
        self.path_label.config(text=path_text)

    def on_download_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select items to download")
            return
            
        download_path = filedialog.askdirectory()
        if not download_path:
            return
            
        # Create list of items to download
        download_list = []
        for item_id in selected_items:
            if 'folder' in self.tree.item(item_id)['tags']:
                # If folder, add the folder prefix
                download_list.append(item_id)  # Will be processed as folder in download_items
            else:
                # If file, add the full path
                download_list.append(item_id)
        
        self.progress_var.set(0)
        self.cancel_download.clear()
        self.download_thread = threading.Thread(
            target=self._download_items_thread,
            args=(self.current_bucket, download_list, download_path)
        )
        self.download_thread.start()

    def _download_items_thread(self, bucket, items, path):
        success = self.s3_handler.download_items(
            bucket, items, path,
            lambda x: self.progress_var.set(x),
            self.cancel_download
        )
        if self.cancel_download.is_set():
            self.progress_var.set(0)
            messagebox.showinfo("Download Canceled", "The download has been canceled.")
        elif success:
            messagebox.showinfo("Download Complete", "The download has been completed successfully.")

    def on_cancel_download(self):
        self.cancel_download.set()

    def run(self):
        self.root.mainloop()
