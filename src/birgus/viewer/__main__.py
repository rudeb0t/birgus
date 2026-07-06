from .app import BirgusViewerApp
from .config import Config


config = Config()

inspector_app = BirgusViewerApp(config)
inspector_app.run()
