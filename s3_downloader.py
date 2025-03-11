import logging
from gui import S3DownloaderGUI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    app = S3DownloaderGUI()
    app.run()
