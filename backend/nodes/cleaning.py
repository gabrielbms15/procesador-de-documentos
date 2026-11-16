import logging
import re
from models.state import PipelineState

def text_cleaning_node(state: PipelineState) -> PipelineState:
    """
    Nodo 3: Limpieza y Normalización de Texto
    
    Funciones:
    - Normalización de espaciado
    - Remoción de patrones comunes de headers/footers
    - Limpieza específica para pólizas
    """
    logger = logging.getLogger("Nodo Limpieza")
    logger.info("Iniciando limpieza de texto")
    state = state.update_stage('Limpieza')

    text = state.document_info.text

    if not text:
        logger.warning("No hay texto para limpiar")
        return state.add_warning("No hay texto para limpiar")
    
    # === CÁLCULO DE 'original_length' ELIMINADO ===
    cleaned_text = text.upper()
    
    # === LIMPIEZA BÁSICA ===
    
    # 1. Normalizar espaciado
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # Múltiples espacios → uno
    cleaned_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_text)  # Múltiples saltos → doble
    
    # 2. Remover patrones comunes de headers/footers (específicos para pólizas)
    patterns_to_remove = [
        r'PÁGINA \d+ DE \d+',
        r'PAGE \d+ OF \d+', 
        r'WWW\.\S+\.\S+',
        r'©.*\d{4}.*',
        r'CONFIDENCIAL.*',
    ]
    
    for pattern in patterns_to_remove:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE | re.MULTILINE)
    
    # 3. Limpiar espacios resultantes
    cleaned_text = cleaned_text.strip()
    
    # === ACTUALIZAR ESTADO ===
    state.document_info.text = cleaned_text

    
    return state