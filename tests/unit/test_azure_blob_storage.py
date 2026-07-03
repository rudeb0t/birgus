import os
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import AzureError

from birgus.transports.azure_blob_storage import (
    AzureBlobStorageTransport,
    BlobServiceClientFactory,
)


type ClearEnvFixture = Generator[None, None, None]


@pytest.fixture
def clear_env(monkeypatch: pytest.MonkeyPatch) -> ClearEnvFixture:
    monkeypatch.delenv("AZURE_STORAGE_CONNECTION_STRING", raising=False)
    monkeypatch.delenv("AZURE_STORAGE_BLOB_URL", raising=False)
    yield


# =====================================================================
# SYNCHRONOUS CLIENT FACTORY TESTS
# =====================================================================


@patch("birgus.transports.azure_blob_storage.BlobServiceClient.from_connection_string")
@pytest.mark.azure_blob_storage
def test_sync_client_with_azurite(
    mock_from_conn_str: MagicMock, clear_env: ClearEnvFixture
) -> None:
    os.environ["AZURE_STORAGE_CONNECTION_STRING"] = "ConnStr"
    mock_client: MagicMock = MagicMock()
    mock_from_conn_str.return_value = mock_client

    factory: BlobServiceClientFactory = BlobServiceClientFactory()
    client: MagicMock = factory.get_service_client()

    assert client == mock_client
    mock_from_conn_str.assert_called_once_with("ConnStr")


@patch("birgus.transports.azure_blob_storage.DefaultAzureCredential")
@patch("birgus.transports.azure_blob_storage.BlobServiceClient")
@pytest.mark.azure_blob_storage
def test_sync_client_with_cloud(
    mock_blob_client_class: MagicMock,
    mock_credential_class: MagicMock,
    clear_env: ClearEnvFixture,
) -> None:
    os.environ["AZURE_STORAGE_BLOB_URL"] = "https://windows.net"
    mock_client: MagicMock = MagicMock()
    mock_blob_client_class.return_value = mock_client

    factory: BlobServiceClientFactory = BlobServiceClientFactory()
    client: MagicMock = factory.get_service_client()

    assert client == mock_client
    mock_credential_class.assert_called_once()


@pytest.mark.azure_blob_storage
def test_sync_close_lifecycle(clear_env: ClearEnvFixture) -> None:
    factory: BlobServiceClientFactory = BlobServiceClientFactory()
    factory._client = MagicMock()
    factory.close()

    factory._client.close.assert_called_once()


# =====================================================================
# AZURE BLOB STORAGE TRANSPORT TESTS
# =====================================================================


@pytest.mark.azure_blob_storage
def test_transport_init(clear_env: ClearEnvFixture) -> None:
    transport: AzureBlobStorageTransport = AzureBlobStorageTransport(
        container_name="test-container", prefix="/test-prefix/"
    )
    assert transport.container_name == "test-container"
    # Tests that leading/trailing slashes are stripped
    assert transport.prefix == "test-prefix"


@patch("birgus.transports.base.time.monotonic_ns")
@pytest.mark.azure_blob_storage
def test_transport_generate_blob_name(
    mock_monotonic_ns: MagicMock, clear_env: ClearEnvFixture
) -> None:
    mock_monotonic_ns.return_value = 772840958865291
    transport: AzureBlobStorageTransport = AzureBlobStorageTransport(
        container_name="test-container", prefix="errors"
    )
    blob_name = transport._generate_blob_name()
    assert blob_name == "errors/772840958865291.birgus"

    prefixed_blob_name = transport._generate_blob_name(name_prefix="prefix-")
    assert prefixed_blob_name == "errors/prefix-772840958865291.birgus"


@pytest.mark.azure_blob_storage
def test_transport_send_success(clear_env: ClearEnvFixture) -> None:
    transport: AzureBlobStorageTransport = AzureBlobStorageTransport("test-container")
    mock_container_client: MagicMock = MagicMock()
    mock_service_client: MagicMock = MagicMock()
    mock_service_client.get_container_client.return_value = mock_container_client

    mock_report: MagicMock = MagicMock()
    mock_report.to_bytes.return_value = b"test-report-data"

    with (
        patch.object(
            transport._service_client_factory,
            "get_service_client",
            return_value=mock_service_client,
        ),
        patch.object(
            transport, "_generate_blob_name", return_value="errors/mock.birgus"
        ),
    ):
        transport.send(mock_report)

    mock_container_client.upload_blob.assert_called_once_with(
        name="errors/mock.birgus",
        data=b"test-report-data",
    )


@pytest.mark.azure_blob_storage
def test_transport_send_client_init_failure(
    clear_env: ClearEnvFixture, caplog: pytest.LogCaptureFixture
) -> None:
    transport: AzureBlobStorageTransport = AzureBlobStorageTransport("test-container")
    mock_report: MagicMock = MagicMock()

    with patch.object(
        transport._service_client_factory,
        "get_service_client",
        side_effect=Exception("Initialization failed"),
    ):
        transport.send(mock_report)

    assert "Failed to initialize Azure Blob Storage Service client" in caplog.text
    assert "Initialization failed" in caplog.text


@pytest.mark.azure_blob_storage
def test_transport_send_upload_failure(caplog: pytest.LogCaptureFixture) -> None:
    transport: AzureBlobStorageTransport = AzureBlobStorageTransport("test-container")
    mock_container_client: MagicMock = MagicMock()
    mock_service_client: MagicMock = MagicMock()
    mock_container_client.upload_blob.side_effect = AzureError("Upload failed")
    mock_service_client.get_container_client.return_value = mock_container_client

    mock_report: MagicMock = MagicMock()
    mock_report.to_bytes.return_value = b"test-report-data"

    with patch.object(
        transport._service_client_factory,
        "get_service_client",
        return_value=mock_service_client,
    ):
        transport.send(mock_report)

    assert "Failed to upload exception report to Azure Blob Storage" in caplog.text
    assert "Upload failed" in caplog.text
