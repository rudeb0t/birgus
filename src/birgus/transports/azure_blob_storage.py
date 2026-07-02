import logging
import os


from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential as SyncDefaultAzureCredential
from azure.storage.blob import BlobServiceClient as SyncBlobServiceClient

from .base import AbstractTransport, TransportPayload


logger = logging.getLogger(__name__)


def _get_env_config() -> tuple[str | None, str | None]:
    return (
        os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        os.getenv("AZURE_STORAGE_BLOB_URL"),
    )


class StorageClientFactory:
    def __init__(self) -> None:
        self._client: SyncBlobServiceClient | None = None

    def get_client(self) -> SyncBlobServiceClient:
        if self._client:
            return self._client

        conn_str, account_url = _get_env_config()

        if conn_str:
            logger.info("Initializing sync Azurite Client via connection string.")
            try:
                self._client = SyncBlobServiceClient.from_connection_string(conn_str)
                return self._client
            except ValueError as err:
                logger.error("Invalid Azurite connection string: %s", err)
                raise

        if not account_url:
            raise KeyError(
                "Missing environment configuration: Provide either "
                "'AZURE_STORAGE_CONNECTION_STRING' or 'AZURE_STORAGE_BLOB_URL'."
            )

        logger.info("Initializing production sync client with DefaultAzureCredential.")
        try:
            credential = SyncDefaultAzureCredential()
            self._client = SyncBlobServiceClient(
                account_url=account_url, credential=credential
            )
            return self._client
        except AzureError as err:
            logger.critical("Sync Azure authentication failure: %s", err)
            raise

    def close(self) -> None:
        if self._client:
            self._client.close()
            logger.info("Sync BlobServiceClient connection pool closed.")


class AzureBlobStorageTransport(AbstractTransport):
    def __init__(self, container_name: str, prefix: str = "") -> None:
        self.container_name = container_name
        self.prefix = prefix.strip("/")
        self._client_factory = StorageClientFactory()

    def _generate_blob_name(self, name_prefix: str = "") -> str:
        return f"{self.prefix}/{self.generate_name(name_prefix)}".strip("/")

    def send(
        self,
        report: TransportPayload,
        name_prefix: str = "",
    ) -> None:
        try:
            client = self._client_factory.get_client()
        except Exception as exc:
            logger.warning("Failed to initialize Azure Blob Storage client: %s", exc)
            return

        if isinstance(report, bytes):
            report_bytes = report
        else:
            report_bytes = report.to_bytes()
        try:
            client.upload_blob(
                container_name=self.container_name,
                blob_name=self._generate_blob_name(name_prefix),
                data=report_bytes,
            )
        except AzureError as exc:
            logger.warning(
                "Failed to upload exception report to Azure Blob Storage: %s", exc
            )
