"""
blob_uploader.py

Uploads generated PDF reports to Azure Blob Storage and returns
a public download URL.
"""

import os
import logging
from pathlib import Path

from azure.storage.blob import BlobServiceClient, ContentSettings

logger = logging.getLogger("blob_uploader")

CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER", "reports")


def upload_pdf_to_blob(local_path: Path, filename: str) -> str:
    """
    Uploads a local PDF file to Azure Blob Storage.
    Returns the public URL of the uploaded blob.
    """
    blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)

    blob_client = container_client.get_blob_client(filename)

    with open(local_path, "rb") as f:
        blob_client.upload_blob(
            f,
            overwrite=True,
            content_settings=ContentSettings(content_type="application/pdf"),
        )

    logger.info(f"Uploaded {filename} to blob storage: {blob_client.url}")
    return blob_client.url

def upload_pdf_bytes_to_blob(pdf_bytes: bytes, filename: str) -> str:
    """
    Uploads PDF bytes (from an in-memory buffer) to Azure Blob Storage.
    Returns the public URL of the uploaded blob.
    """
    blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(CONTAINER_NAME)
    blob_client = container_client.get_blob_client(filename)

    blob_client.upload_blob(
        pdf_bytes,
        overwrite=True,
        content_settings=ContentSettings(content_type="application/pdf"),
    )

    logger.info(f"Uploaded {filename} to blob storage: {blob_client.url}")
    return blob_client.url