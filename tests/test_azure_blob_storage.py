import os
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import AzureError

from birgus.transports.azure_blob_storage import (
    AzureBlobStorageTransport,
    StorageClientFactory,
)


@pytest.fixture(autouse=True)
def clear_env() -> Generator[None, None, None]:
    old_env: dict[str, str] = dict(os.environ)
    os.environ.pop("AZURE_STORAGE_CONNECTION_STRING", None)
    os.environ.pop("AZURE_STORAGE_BLOB_URL", None)
    yield
    os.environ.clear()
    os.environ.update(old_env)


# =====================================================================
# SYNCHRONOUS CLIENT FACTORY TESTS
# =====================================================================


@patch(
    "birgus.transports.azure_blob_storage.SyncBlobServiceClient.from_connection_string"
)
def test_sync_client_with_azurite(mock_from_conn_str: MagicMock) -> None:
    os.environ["AZURE_STORAGE_CONNECTION_STRING"] = "SyncConnStr"
    mock_client: MagicMock = MagicMock()
    mock_from_conn_str.return_value = mock_client

    factory: StorageClientFactory = StorageClientFactory()
    client: MagicMock = factory.get_client()

    assert client == mock_client
    mock_from_conn_str.assert_called_once_with("SyncConnStr")


@patch("birgus.transports.azure_blob_storage.SyncDefaultAzureCredential")
@patch("birgus.transports.azure_blob_storage.SyncBlobServiceClient")
def test_sync_client_with_cloud(
    mock_blob_client_class: MagicMock, mock_credential_class: MagicMock
) -> None:
    os.environ["AZURE_STORAGE_BLOB_URL"] = "https://windows.net"
    mock_client: MagicMock = MagicMock()
    mock_blob_client_class.return_value = mock_client

    factory: StorageClientFactory = StorageClientFactory()
    client: MagicMock = factory.get_client()

    assert client == mock_client
    mock_credential_class.assert_called_once()


def test_sync_close_lifecycle() -> None:
    factory: StorageClientFactory = StorageClientFactory()
    factory._client = MagicMock()
    factory.close()

    factory._client.close.assert_called_once()


# =====================================================================
# AZURE BLOB STORAGE TRANSPORT TESTS
# =====================================================================


def test_transport_init() -> None:
    transport: AzureBlobStorageTransport = AzureBlobStorageTransport(
        container_name="test-container", prefix="/test-prefix/"
    )
    assert transport.container_name == "test-container"
    # Tests that leading/trailing slashes are stripped
    assert transport.prefix == "test-prefix"


@patch("birgus.transports.base.time.monotonic_ns")
def test_transport_generate_blob_name(mock_monotonic_ns: MagicMock) -> None:
    mock_monotonic_ns.return_value = 772840958865291
    transport: AzureBlobStorageTransport = AzureBlobStorageTransport(
        container_name="test-container", prefix="errors"
    )
    blob_name = transport._generate_blob_name()
    assert blob_name == "errors/772840958865291.birgus"

    prefixed_blob_name = transport._generate_blob_name(name_prefix="prefix-")
    assert prefixed_blob_name == "errors/prefix-772840958865291.birgus"


def test_transport_send_success() -> None:
    transport: AzureBlobStorageTransport = AzureBlobStorageTransport("test-container")
    mock_client: MagicMock = MagicMock()

    mock_report: MagicMock = MagicMock()
    mock_report.to_bytes.return_value = b"test-report-data"

    with (
        patch.object(transport._client_factory, "get_client", return_value=mock_client),
        patch.object(
            transport, "_generate_blob_name", return_value="errors/mock.birgus"
        ),
    ):
        transport.send(mock_report)

    mock_client.upload_blob.assert_called_once_with(
        container_name="test-container",
        blob_name="errors/mock.birgus",
        data=b"test-report-data",
    )


def test_transport_send_client_init_failure(caplog: pytest.LogCaptureFixture) -> None:
    transport: AzureBlobStorageTransport = AzureBlobStorageTransport("test-container")
    mock_report: MagicMock = MagicMock()

    with patch.object(
        transport._client_factory,
        "get_client",
        side_effect=Exception("Initialization failed"),
    ):
        transport.send(mock_report)

    assert "Failed to initialize Azure Blob Storage client" in caplog.text
    assert "Initialization failed" in caplog.text


def test_transport_send_upload_failure(caplog: pytest.LogCaptureFixture) -> None:
    transport: AzureBlobStorageTransport = AzureBlobStorageTransport("test-container")
    mock_client: MagicMock = MagicMock()
    mock_client.upload_blob.side_effect = AzureError("Upload failed")

    mock_report: MagicMock = MagicMock()
    mock_report.to_bytes.return_value = b"test-report-data"

    with patch.object(
        transport._client_factory, "get_client", return_value=mock_client
    ):
        transport.send(mock_report)

    assert "Failed to upload exception report to Azure Blob Storage" in caplog.text
    assert "Upload failed" in caplog.text
