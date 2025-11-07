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


def _replace_endpoint_in_url(url: str) -> str:
	"""Replace internal S3 endpoint with public endpoint in presigned URLs."""
	import logging
	logger = logging.getLogger(__name__)
	
	if settings.s3_public_endpoint != settings.s3_endpoint:
		# Extract hostname from both endpoints
		from urllib.parse import urlparse
		internal_parsed = urlparse(settings.s3_endpoint)
		public_parsed = urlparse(settings.s3_public_endpoint)
		
		original_url = url
		# Replace the hostname in the URL
		if internal_parsed.netloc in url:
			url = url.replace(internal_parsed.netloc, public_parsed.netloc)
		# Also try replacing the full endpoint URL
		if settings.s3_endpoint in url:
			url = url.replace(settings.s3_endpoint, settings.s3_public_endpoint)
		
		if original_url != url:
			logger.info(f"Replaced endpoint: {internal_parsed.netloc} -> {public_parsed.netloc}")
		else:
			logger.warning(f"Failed to replace endpoint in URL. Internal: {settings.s3_endpoint}, Public: {settings.s3_public_endpoint}, URL: {url[:100]}")
	else:
		logger.info(f"S3 endpoints are the same, no replacement needed: {settings.s3_endpoint}")
	
	return url


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
	upload_url = _replace_endpoint_in_url(upload_url)
	headers: Dict[str, str] = {}
	if content_type:
		headers["Content-Type"] = content_type
	return upload_url, headers


def create_presigned_get(key: str, expires_in: int = 3600) -> str:
	"""Create a presigned GET URL for downloading objects."""
	client = get_s3_client()
	url = client.generate_presigned_url(
		"get_object",
		Params={"Bucket": settings.s3_bucket, "Key": key},
		ExpiresIn=expires_in,
	)
	return _replace_endpoint_in_url(url)
