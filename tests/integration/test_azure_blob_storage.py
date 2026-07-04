from typing import Generator

import pytest
from unittest.mock import MagicMock, patch

from azure.storage.blob import (
    BlobServiceClient,
    ContainerClient,
    StorageStreamDownloader,
)
from testcontainers.azurite import AzuriteContainer

from birgus.transports.azure_blob_storage import (
    AzureBlobStorageTransport,
    BlobServiceClientFactory,
)


@pytest.fixture(scope="session")
def azurite_storage_connection_string() -> Generator[str, None, None]:
    with AzuriteContainer() as azurite:
        yield azurite.get_connection_string()


@pytest.mark.azure_blob_storage
def test_azure_blob_storage_transport(
    monkeypatch: pytest.MonkeyPatch,
    azurite_storage_connection_string: str,
) -> None:
    monkeypatch.setenv(
        "AZURE_STORAGE_CONNECTION_STRING", azurite_storage_connection_string
    )

    mock_report: MagicMock = MagicMock()
    mock_report.to_bytes.return_value = b"test-report-data"

    blob_service_client: BlobServiceClient = BlobServiceClient.from_connection_string(
        azurite_storage_connection_string, api_version="2025-01-05"
    )
    blob_service_client.create_container("test-container")

    transport: AzureBlobStorageTransport = AzureBlobStorageTransport(
        "test-container", "errors"
    )
    with patch.object(
        BlobServiceClientFactory, "get_service_client", return_value=blob_service_client
    ):
        transport.send(mock_report, "test-prefix-772840958865291.birgus")

        blob_name: str = "errors/test-prefix-772840958865291.birgus"
        blob_client: ContainerClient = blob_service_client.get_blob_client(
            "test-container", blob_name
        )
        blob_stream: StorageStreamDownloader = blob_client.download_blob()
        blob: bytes = blob_stream.readall()
        assert blob == b"test-report-data"
