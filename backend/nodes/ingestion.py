import logging
from pathlib import Path

from utils.pdf_utils import validate_pdf_integrity, validate_extractable_text
from models.state import PipelineState
from models.settings import settings

def document_ingestion_node(state: PipelineState) -> PipelineState:
    
    filename = state.document_info.filename or "documento"

    logger = logging.getLogger("Nodo Ingesta")
    logger.info(f"Iniciando ingesta de documento: {filename}")
    state = state.update_stage('Ingesta')

    try:
        
        file_path = Path(state.document_info.file_path or "")
        
        # === VALIDACIONES BÁSICAS ===
        if not file_path.exists():
            error_msg = f"Archivo no encontrado: {file_path}"
            return state.add_error(error_msg)
        
        # Verificar tamaño del archivo
        file_size_bytes = file_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        if file_size_mb > settings.max_pdf_size_mb:
            error_msg = f"Archivo excede tamaño máximo ({file_size_mb:.1f}MB > {settings.max_pdf_size_mb}MB)"
            return state.add_error(error_msg)
        
        # === ANÁLISIS PDF ===
        logger.info("Analizando estructura del PDF...")
        
        # Validar integridad del PDF
        is_valid, error_msg, page_count, metadata = validate_pdf_integrity(file_path)

        if not is_valid:
            return state.add_error(error_msg)
        
        # Validar texto extraíble
        has_extractable_text, extraction_method = validate_extractable_text(file_path)
        if not has_extractable_text:
            error_msg = "PDF no contiene texto extraíble (posiblemente escaneado)"
            return state.add_error(error_msg)
        
        logger.info(f"PDF válido: {page_count} páginas, {file_size_mb:.2f}MB, texto extraíble con {extraction_method}")
        return state
        
    except Exception as e:
        error_msg = f"Error crítico en ingesta: {str(e)}"
        state = state.add_error(error_msg)
        logger.error(error_msg)
        return state