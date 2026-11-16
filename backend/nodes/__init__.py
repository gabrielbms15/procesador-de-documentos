# nodes/__init__.py

# Importar solo los nodos necesarios
from .ingestion import document_ingestion_node
from .extraction import text_extraction_node
from .cleaning import text_cleaning_node
from .segmentation import intelligent_chunking_node
from .filtering import filtering_node
from .llm_processing import llm_processing_node

# Metadatos del módulo

# Configuración de logging para todos los nodos
import logging

logger = logging.getLogger(__name__)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)