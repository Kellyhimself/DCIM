import boto3
from botocore.client import Config
from typing import Tuple, Dict
import uuid

from backend.app.settings import settings


def get_s3_client():
	return boto3.client(
		"s3",
		endpoint_url=settings.s3_endpoint,
		aws_access_key_id=settings.s3_access_key,
		aws_secret_access_key=settings.s3_secret_key,
		config=Config(signature_version="s3v4"),
	)


def create_presigned_put(key: str, content_type: str | None = None) -> Tuple[str, Dict[str, str]]:
	client = get_s3_client()
	params = {"Bucket": settings.s3_bucket, "Key": key}
	if content_type:
		params["ContentType"] = content_type
	upload_url = client.generate_presigned_url(
		ClientMethod="put_object",
		Params=params,
		ExpiresIn=3600,
	)
	headers: Dict[str, str] = {}
	if content_type:
		headers["Content-Type"] = content_type
	return upload_url, headers
