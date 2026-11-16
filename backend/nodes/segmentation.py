import logging

from models.state import PipelineState
from utils.chunking_utils import create_chunks

def intelligent_chunking_node(state: PipelineState) -> PipelineState:
    """
    Nodo 3: Chunking por páginas
    
    Funciones:
    - Segmentación por páginas de texto limpio
    - Estimación de tokens por chunk
    - Mantenimiento de trazabilidad con páginas originales
    """

    logger = logging.getLogger("Nodo Segmentación")
    logger.info("Iniciando chunking")
    state = state.update_stage('Segmentación')
    
    # Obtener texto limpio
    text = state.document_info.text

    if not text or not text.strip():
        logger.warning("No hay texto para segmentar")
        return state.add_warning("No hay texto para crear chunks")
    
    # Obtener datos de páginas para trazabilidad
    page_data = state.logging.debug_info.get("extraction_stats", {}).get("page_data", {})
    
    logger.info("Segmentando texto por páginas...")
    
    try:
        chunks = create_chunks(text, page_data)
        
        if not chunks:
            logger.error("No se pudieron crear chunks válidos del texto")
            return state.add_error("No se pudieron crear chunks válidos")
        
        # Actualizar estado con chunks
        state.chunk_data.text_chunks = chunks
        
        # Estadísticas para debug
        total_tokens = sum(chunk["token_count"] for chunk in chunks)
        avg_tokens = total_tokens // len(chunks) if chunks else 0
        
        state.logging.debug_info.update({
            "chunking_stats": {
                "chunking_method": "paged_based",
                "total_chunks": len(chunks),
                "total_tokens_estimated": total_tokens,
                "average_tokens_per_chunk": avg_tokens,
                "min_chunk_length": 50,  # caracteres mínimos
                "chunking_successful": True
            }
        })
        
        logger.info(f"Chunking completado: {len(chunks)} páginas, ~{total_tokens} tokens estimados")

        return state
        
    except Exception as e:
        logger.error(f"Error durante chunking: {e}")
        return state.add_error(f"Error en segmentación: {str(e)}")