from minio import Minio
from minio.error import S3Error

minio_client = Minio(minio_endpoint, minio_access_key, minio_secret_key, secure=minio_secure)