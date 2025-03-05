# S3 Folder Downloader

S3 Folder Downloader is a Python-based tool that allows you to download entire folders from an AWS S3 bucket using a graphical user interface (GUI) built with Tkinter.

## Features

- List and select S3 buckets
- List and select folders within a bucket
- Download selected folders to a local directory
- Save and load AWS credentials securely using encryption

## Requirements

- Python 3.x
- The following Python packages:
  - boto3
  - tk-tools
  - cryptography
  - pyinstaller

## Installation

1. Clone the repository:

    ```sh
    git clone git@github.com:chinmay-lightfury/s3_downloader.git
    cd s3_downloader
    ```

2. Install the required packages:

    ```sh
    pip install -r requirements.txt
    ```

## Usage

1. Run the `s3_downloader.py` script:

    ```sh
    python s3_downloader.py
    ```

2. Configure your AWS credentials and region by selecting "Settings" from the menu and entering the required information.

3. Select an S3 bucket from the dropdown list.

4. Select a folder from the list of available folders.

5. Click "Download Selected Folder" to choose a local directory and start the download.

6. You can cancel the download at any time by clicking "Cancel Download".

## Building Executable

To build a standalone executable for Windows using PyInstaller, you can use the provided GitHub Actions workflow. The workflow will automatically build the executable and create a release when you push a tag matching the pattern `v*`.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.
