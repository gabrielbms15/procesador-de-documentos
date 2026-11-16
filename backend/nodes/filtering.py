import logging

from models.state import PipelineState
from utils.filtering_utils import calculate_advanced_priorities, apply_dynamic_ranking, intelligent_chunk_selection

def filtering_node(state: PipelineState) -> PipelineState:
    """
    Nodo 5: Filtrado Inteligente y Priorización Avanzada
    
    Funciones consolidadas:
    - Cálculo de prioridad avanzada con múltiples factores
    - Sistema de ranking dinámico (no umbrales fijos)
    - Ordenamiento y limitación inteligente de chunks
    - Optimización de tokens para procesamiento
    """
    logger = logging.getLogger("Nodo Filtrado")
    logger.info("Iniciando filtrado ")
    state = state.update_stage('Filtrado')
    
    # Obtener chunks desde la estructura correcta
    chunks = state.chunk_data.text_chunks
    
    if not chunks:
        logger.warning("No hay chunks para filtrar")
        return state.add_warning("No hay chunks para procesar")
    
    logger.info(f"Procesando {len(chunks)} chunks para priorización...")
    
    try:
        # Calcular prioridad avanzada para todos los chunks
        prioritized_chunks = calculate_advanced_priorities(chunks)
        
        # Aplicar sistema de ranking dinámico
        ranked_chunks = apply_dynamic_ranking(prioritized_chunks)
        
        # Limitar chunks de forma inteligente
        final_chunks, selection_stats = intelligent_chunk_selection(ranked_chunks)
        
        # Actualizar estado con chunks priorizados
        state.chunk_data.filtered_chunks = final_chunks
        
        return state
        
    except Exception as e:
        logger.error(f"Error durante filtrado y priorización: {e}")
        return state.add_error(f"Error en filtrado: {str(e)}")