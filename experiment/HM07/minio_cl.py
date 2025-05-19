import base64
import io
import json

import requests
from loguru import logger
from minio import Minio, InvalidResponseError

storage_url = "https://minio.emagiceyes.rainscales.com"
storage_access_key = "minioadmin"
storage_secret_key = "minioadmin"
storage_bucket = "emagic-event"


class MinioStorage:
    def __init__(self):
        self.client = None
        self.init()

    def init(self):
        self.client = Minio(
            storage_url, storage_access_key, storage_secret_key, secure=False
        )
        if not self.client.bucket_exists(storage_bucket):
            logger.warning("Bucket not existed create bucket")
            self.create_bucket(storage_bucket)
            logger.warning("Create bucket done")

    def create_bucket(self, bucket_name):
        self.client.make_bucket(bucket_name)
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": [
                        "s3:GetBucketLocation",
                        "s3:ListBucket",
                        "s3:ListBucketMultipartUploads",
                    ],
                    "Resource": f"arn:aws:s3:::{storage_bucket}",
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:ListMultipartUploadParts",
                        "s3:AbortMultipartUpload",
                    ],
                    "Resource": f"arn:aws:s3:::{storage_bucket}/*",
                },
            ],
        }
        self.client.set_bucket_policy(storage_bucket, json.dumps(policy))

    def upload_file(self, m_bucket: str, filename: str, file_path: str):
        try:
            self.client.fput_object(
                bucket_name=m_bucket, object_name=filename, file_path=file_path
            )
            if self.client._base_url.is_https:
                return f"https://{self.client._base_url.host}/{m_bucket}/{filename}"
            return f"http://{self.client._base_url.host}/{m_bucket}/{filename}"
        except InvalidResponseError as err:
            logger.error(f"Minio upload error: {err}")
            return None

    def download_file(self, m_bucket: str, filename: str):
        try:
            res = self.client.get_object(m_bucket, filename)
            return res
        except InvalidResponseError as err:
            logger.error(f"Minio download error: {err}")
            return None

    def delete_file(self, m_bucket: str, filename: str):
        try:
            self.client.remove_object(m_bucket, filename)
        except InvalidResponseError as err:
            logger.error(f"Minio delete error: {err}")
            return None

    def put_b64image(self, m_bucket, filename, b64_image):
        """Upload image (base64 string) with filename to minio"""
        try:

            imgdata = base64.b64decode(b64_image)
            img_as_stream = io.BytesIO(imgdata)
            self.client.put_object(
                m_bucket, filename, img_as_stream, len(imgdata)
            )
            if self.client._base_url.is_https:
                return f"https://{self.client._base_url.host}/{m_bucket}/{filename}"
            return f"http://{self.client._base_url.host}/{m_bucket}/{filename}"

        except InvalidResponseError as err:
            logger.error(f"Minio upload error: {err}")
            return None

    def copy_image(self, m_bucket, image_url, new_filename):
        try:
            response = requests.get(image_url, verify=False)
            # image_data = self.client.get_object(m_bucket, old_filename)
            self.client.put_object(
                m_bucket,
                new_filename,
                io.BytesIO(response.content),
                len(response.content),
            )
            if self.client._base_url.is_https:
                return f"https://{self.client._base_url.host}/{m_bucket}/{new_filename}"
            return (
                f"http://{self.client._base_url.host}/{m_bucket}/{new_filename}"
            )
        except Exception as e:
            logger.error(f"Copy minio failed: {e}")
            return None


minio_client = MinioStorage()
