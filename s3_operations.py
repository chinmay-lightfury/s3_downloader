import logging
import os
import boto3
from botocore.exceptions import ClientError
from settings_manager import load_settings

class S3Handler:
    def __init__(self):
        self.s3_client = None

    def initialize_client(self):
        settings = load_settings()
        aws_access_key_id = settings.get('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = settings.get('AWS_ACCESS_SECRET_KEY')
        aws_session_token = settings.get('AWS_SESSION_TOKEN')
        aws_region = settings.get('AWS_REGION')

        if not all([aws_access_key_id, aws_secret_access_key, aws_session_token, aws_region]):
            raise ValueError("AWS credentials and region must be set in the settings.")

        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=aws_region
        )
        # Test connection
        self.s3_client.list_buckets()

    def list_buckets(self):
        response = self.s3_client.list_buckets()
        return [bucket['Name'] for bucket in response['Buckets']]

    def list_folders(self, bucket_name):
        response = self.s3_client.list_objects_v2(Bucket=bucket_name, Delimiter='/')
        return [prefix['Prefix'] for prefix in response.get('CommonPrefixes', [])]

    def list_objects(self, bucket_name, prefix=''):
        try:
            # For current level folders
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                Delimiter='/'
            )
            
            folders = [prefix['Prefix'] for prefix in response.get('CommonPrefixes', [])]
            
            # For files in current prefix
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Skip if object is the prefix itself
                    if obj['Key'] == prefix:
                        continue
                    # Skip if object is a folder marker
                    if obj['Key'].endswith('/'):
                        continue
                    # Only include files in current level
                    if '/' in obj['Key'][len(prefix):].rstrip('/'):
                        continue
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified']
                    })
            
            return folders, files
        except Exception as e:
            logging.error(f"Error listing objects: {e}")
            return [], []

    def download_items(self, bucket_name, items, download_path, progress_callback, cancel_event):
        """Download multiple items with progress tracking"""
        total_downloaded = 0
        files_to_download = []

        # First, collect all files that need to be downloaded
        for item in items:
            if item.endswith('/'):  # It's a folder
                # Get all files in this folder
                paginator = self.s3_client.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=bucket_name, Prefix=item):
                    for obj in page.get('Contents', []):
                        if not obj['Key'].endswith('/'):
                            files_to_download.append(obj['Key'])
            else:  # It's a file
                files_to_download.append(item)

        total_files = len(files_to_download)
        if total_files == 0:
            return True

        for idx, key in enumerate(files_to_download):
            if cancel_event.is_set():
                return False

            # Preserve the folder structure
            rel_path = key
            if rel_path.startswith('/'):
                rel_path = rel_path[1:]
            local_path = os.path.join(download_path, rel_path)
            
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            try:
                logging.info(f"Downloading {key} to {local_path}")
                self.s3_client.download_file(bucket_name, key, local_path)
                total_downloaded += 1
                progress_callback(total_downloaded / total_files * 100)
            except Exception as e:
                logging.error(f"Error downloading {key}: {e}")

        return True
