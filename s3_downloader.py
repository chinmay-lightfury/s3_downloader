import json
import logging
import os
import threading

import boto3
from botocore.exceptions import ClientError
from cryptography.fernet import Fernet
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

settings_file = 'aws_settings.enc'
key_file = 'secret.key'

def generate_key():
    key = Fernet.generate_key()
    with open(key_file, 'wb') as key_out:
        key_out.write(key)

def load_key():
    if not os.path.exists(key_file):
        generate_key()
    with open(key_file, 'rb') as key_in:
        return key_in.read()

def encrypt_data(data, key):
    fernet = Fernet(key)
    return fernet.encrypt(data.encode())

def decrypt_data(data, key):
    fernet = Fernet(key)
    return fernet.decrypt(data).decode()

def load_settings():
    key = load_key()
    if os.path.exists(settings_file):
        with open(settings_file, 'rb') as f:
            encrypted_data = f.read()
        decrypted_data = decrypt_data(encrypted_data, key)
        return json.loads(decrypted_data)
    else:
        default_settings = {
            'AWS_ACCESS_KEY_ID': '',
            'AWS_ACCESS_SECRET_KEY': '',
            'AWS_SESSION_TOKEN': '',
            'AWS_REGION': ''
        }
        save_settings(default_settings)
        return default_settings

def save_settings(settings):
    key = load_key()
    data = json.dumps(settings)
    encrypted_data = encrypt_data(data, key)
    with open(settings_file, 'wb') as f:
        f.write(encrypted_data)

def open_settings_window():
    def save_and_close():
        settings = {
            'AWS_ACCESS_KEY_ID': access_key_entry.get(),
            'AWS_ACCESS_SECRET_KEY': secret_key_entry.get(),
            'AWS_SESSION_TOKEN': session_token_entry.get(),
            'AWS_REGION': region_entry.get()
        }
        save_settings(settings)
        settings_window.destroy()
        initialize_s3_client()
        update_bucket_dropdown()

    settings_window = tk.Toplevel(root)
    settings_window.title("AWS Settings")
    settings_window.geometry("300x300")
    settings_window.resizable(False, False)

    tk.Label(settings_window, text="Access Key ID:").pack(pady=5)
    access_key_entry = tk.Entry(settings_window, width=40)
    access_key_entry.pack(pady=5)

    tk.Label(settings_window, text="Secret Access Key:").pack(pady=5)
    secret_key_entry = tk.Entry(settings_window, width=40, show='*')
    secret_key_entry.pack(pady=5)

    tk.Label(settings_window, text="Session Token:").pack(pady=5)
    session_token_entry = tk.Entry(settings_window, width=40, show='*')
    session_token_entry.pack(pady=5)

    tk.Label(settings_window, text="Region:").pack(pady=5)
    region_entry = tk.Entry(settings_window, width=40)
    region_entry.pack(pady=5)

    tk.Button(settings_window, text="Save", command=save_and_close).pack(pady=10)

    settings = load_settings()
    access_key_entry.insert(0, settings.get('AWS_ACCESS_KEY_ID', ''))
    secret_key_entry.insert(0, settings.get('AWS_ACCESS_SECRET_KEY', ''))
    session_token_entry.insert(0, settings.get('AWS_SESSION_TOKEN', ''))
    region_entry.insert(0, settings.get('AWS_REGION', ''))

def initialize_s3_client():
    global s3_client
    settings = load_settings()
    aws_access_key_id = settings.get('AWS_ACCESS_KEY_ID')
    aws_secret_access_key = settings.get('AWS_ACCESS_SECRET_KEY')
    aws_session_token = settings.get('AWS_SESSION_TOKEN')
    aws_region = settings.get('AWS_REGION')

    if not aws_access_key_id or not aws_secret_access_key or not aws_session_token or not aws_region:
        messagebox.showwarning("Warning", "AWS credentials and region must be set in the settings.")
        logging.warning("AWS credentials and region are not set.")
        return

    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=aws_region
        )
        s3_client.list_buckets()
        messagebox.showinfo("Success", "AWS credentials are valid and connection is successful.")
        logging.info("AWS credentials are valid and connection is successful.")
    except ClientError as e:
        messagebox.showerror("Error", f"Invalid AWS credentials: {e}")
        logging.error(f"Invalid AWS credentials: {e}")
        s3_client = None

def update_bucket_dropdown():
    if 's3_client' in globals() and s3_client:
        buckets = list_buckets()
        bucket_dropdown['values'] = buckets

cancel_download = threading.Event()

def list_buckets():
    response = s3_client.list_buckets()
    buckets = [bucket['Name'] for bucket in response['Buckets']]
    return buckets

def list_folders(bucket_name):
    response = s3_client.list_objects_v2(Bucket=bucket_name, Delimiter='/')
    folders = [prefix['Prefix'] for prefix in response.get('CommonPrefixes', [])]
    return folders

def download_folder(bucket_name, folder_name, download_path, progress_var):
    paginator = s3_client.get_paginator('list_objects_v2')
    objects = []
    for page in paginator.paginate(Bucket=bucket_name, Prefix=folder_name):
        objects.extend(page.get('Contents', []))
    
    total_files = len(objects)
    for idx, obj in enumerate(objects):
        if cancel_download.is_set():
            logging.info("Download canceled by user.")
            break
        key = obj['Key']
        local_path = os.path.join(download_path, key)
        if key.endswith('/'):
            continue
        local_dir = os.path.dirname(local_path)
        os.makedirs(local_dir, exist_ok=True)
        try:
            logging.info(f"Downloading {key} to {local_path}")
            s3_client.download_file(bucket_name, key, local_path)
        except Exception as e:
            logging.error(f"Error downloading {key}: {e}")
        progress_var.set((idx + 1) / total_files * 100)
    if cancel_download.is_set():
        progress_var.set(0)
        messagebox.showinfo("Download Canceled", "The download has been canceled.")
    else:
        messagebox.showinfo("Download Complete", "The download has been completed successfully.")
        logging.info("Download completed successfully.")

def on_bucket_select(event):
    selected_bucket = bucket_var.get()
    folders = list_folders(selected_bucket)
    folder_listbox.delete(0, tk.END)
    for folder in folders:
        folder_listbox.insert(tk.END, folder)

def on_folder_select():
    global download_thread
    selected_bucket = bucket_var.get()
    selected_folder = folder_listbox.get(tk.ACTIVE)
    if not selected_folder:
        messagebox.showerror("Error", "Please select a folder")
        return
    download_path = filedialog.askdirectory()
    if not download_path:
        messagebox.showerror("Error", "Please select a download location")
        return

    download_path = os.path.join(download_path, selected_folder.strip('/'))
    os.makedirs(download_path, exist_ok=True)
    
    progress_var.set(0)
    cancel_download.clear()
    download_thread = threading.Thread(target=download_folder, args=(selected_bucket, selected_folder, download_path, progress_var))
    download_thread.start()

def on_cancel_download():
    cancel_download.set()

root = tk.Tk()
root.title("S3 Folder Downloader")
root.geometry("400x550")
root.resizable(False, False)

menu = tk.Menu(root)
root.config(menu=menu)
settings_menu = tk.Menu(menu)
menu.add_cascade(label="Settings", menu=settings_menu)
settings_menu.add_command(label="AWS Settings", command=open_settings_window)

frame_buckets = tk.Frame(root)
frame_buckets.pack(fill=tk.X, padx=10, pady=10)

label_buckets = tk.Label(frame_buckets, text="Select Bucket:", font=("Arial", 12))
label_buckets.pack(anchor=tk.W)

bucket_var = tk.StringVar()
bucket_dropdown = ttk.Combobox(frame_buckets, textvariable=bucket_var, font=("Arial", 10))
bucket_dropdown.pack(fill=tk.X, pady=5)
bucket_dropdown.bind("<<ComboboxSelected>>", on_bucket_select)

initialize_s3_client()
update_bucket_dropdown()

frame_folders = tk.Frame(root)
frame_folders.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

label_folders = tk.Label(frame_folders, text="Available Folders:", font=("Arial", 12))
label_folders.pack(anchor=tk.W)

folder_listbox = tk.Listbox(frame_folders, height=10, font=("Arial", 10))
folder_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

frame_download = tk.Frame(root)
frame_download.pack(fill=tk.X, padx=10, pady=10)

download_button = tk.Button(frame_download, text="Download Selected Folder", command=on_folder_select, font=("Arial", 12))
download_button.pack(fill=tk.X, pady=5)

cancel_button = tk.Button(frame_download, text="Cancel Download", command=on_cancel_download, font=("Arial", 12))
cancel_button.pack(fill=tk.X, pady=5)

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(frame_download, variable=progress_var, maximum=100)
progress_bar.pack(fill=tk.X, pady=5)

root.mainloop()
