"""Settings for storage app.

Used to provide s simple default configuration.
"""
from django.conf import settings

from resolwe.flow.executors.constants import UPLOAD_VOLUME

data_dir = getattr(settings, "FLOW_EXECUTOR", {}).get("DATA_DIR", "/some_path")
default_local_connector = "local"


export_connector = "export"
default_storage_connectors = {
    default_local_connector: {
        "connector": "resolwe.storage.connectors.localconnector.LocalFilesystemConnector",
        "config": {"priority": 0, "path": data_dir},
    },
    export_connector: {
        "connector": "resolwe.storage.connectors.localconnector.LocalFilesystemConnector",
        "config": {"priority": 100, "path": UPLOAD_VOLUME, "public_url": UPLOAD_VOLUME},
    },
}

STORAGE_LOCAL_CONNECTOR = getattr(
    settings, "STORAGE_LOCAL_CONNECTOR", default_local_connector
)
STORAGE_CONNECTORS = getattr(settings, "STORAGE_CONNECTORS", default_storage_connectors)
