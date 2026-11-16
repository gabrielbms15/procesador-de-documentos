import logging 
from typing import Dict, List, Any
import re

logger = logging.getLogger(__name__)

def create_chunks(cleaned_text: str, page_data: Dict[int, str]) -> List[Dict[str, Any]]:
    """
    Crea chunks basados en páginas de texto limpio.
    
    Args:
        cleaned_text: Texto ya limpio y normalizado
        page_data: Datos de páginas originales para trazabilidad
        
    Returns:
        List[Dict]: Lista de chunks con metadata
    """
    
    chunks = []
    chunk_id = 0
    
    for page_num, page_text in page_data.items():
        if len(page_text.strip()) > 10:  # Solo páginas con contenido significativo
            chunk_id += 1
            
            priority_score: int = 0
            priority_level: str = 'low'

            # Crear chunk como diccionario
            chunk = {
                "chunk_id": f"c{chunk_id}",
                "text": page_text,
                "page_number": page_num,
                "priority_score": priority_score,
                "priority_level": priority_level,
                "token_count": estimate_tokens_advanced(page_text),  # Estimación avanzada de tokens
                "processed": False
            }            
            chunks.append(chunk)
    
    return chunks

def estimate_tokens_advanced(text: str) -> int:
    """
    Estimación más precisa de tokens para texto en español.
    
    Args:
        text: Texto a estimar

    Returns:
        int: Número estimado de tokens
    """
    # Contar palabras
    words = len(text.split())

    # Contar caracteres especiales que suelen ser tokens separados
    special_chars = len(re.findall(r'[.,;:!?()"\'-]', text))

    # En español, aproximadamente 1.3 tokens por palabra + caracteres especiales
    estimated_tokens = int(words * 1.3) + special_chars

    return max(1, estimated_tokens)  # Mínimo 1 token
