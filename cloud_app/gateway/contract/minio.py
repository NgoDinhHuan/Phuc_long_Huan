import base64
import io
import json

import requests
from loguru import logger
from minio import Minio, InvalidResponseError
from cloud_app.common.config import cfg


class MinioStorage:
    def __init__(self):
        self.client = None
        # self.init()

    def init(self) -> bool:
        try:
            logger.info(f"Init minio client: {cfg.storage_url}")
            self.client = Minio(
                cfg.storage_url,
                cfg.storage_access_key,
                cfg.storage_secret_key,
                secure=cfg.storage_secure,
            )
            if not self.client.bucket_exists(cfg.storage_bucket):
                logger.warning("Bucket not existed, creating bucket")
                self.create_bucket(cfg.storage_bucket)
                logger.warning("Create bucket done")
            return True

        except Exception as e:
            logger.error(f"Failed to init Minio client: {e}")
            self.client = None
            return False

    def is_connected(self) -> bool:
        if self.client is None:
            return self.init()
        try:
            self.client.bucket_exists(cfg.storage_bucket)
            return True
        except:
            logger.warning("Lost connection to Minio, trying to reconnect...")
            return self.init()

    def create_bucket(self, bucket_name):
        try:
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
                        "Resource": f"arn:aws:s3:::{cfg.storage_bucket}",
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
                        "Resource": f"arn:aws:s3:::{cfg.storage_bucket}/*",
                    },
                ],
            }
            self.client.set_bucket_policy(cfg.storage_bucket, json.dumps(policy))
        except Exception as e:
            logger.error(f"Failed to create bucket: {e}")
            raise e

    def upload_file(self, m_bucket: str, filename: str, file_path: str):
        """Upload file to Minio"""
        if not self.is_connected():
            logger.error("Cannot connect to Minio")
            return None

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
        """Download file from Minio"""
        if not self.is_connected():
            logger.error("Cannot connect to Minio")
            return None

        try:
            return self.client.get_object(m_bucket, filename)
        except InvalidResponseError as err:
            logger.error(f"Minio download error: {err}")
            return None

    def delete_file(self, m_bucket: str, filename: str):
        """Delete file from Minio"""
        if not self.is_connected():
            logger.error("Cannot connect to Minio")
            return None

        try:
            self.client.remove_object(m_bucket, filename)
            return True
        except InvalidResponseError as err:
            logger.error(f"Minio delete error: {err}")
            return None

    def put_b64image(self, m_bucket, filename, b64_image):
        """Upload base64 image to Minio"""
        if not self.is_connected():
            logger.error("Cannot connect to Minio")
            return None

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
        """Copy image from URL to Minio"""
        if not self.ensure_connected():
            logger.error("Cannot connect to Minio")
            return None

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
