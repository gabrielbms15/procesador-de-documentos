import logging
import re
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

def calculate_advanced_priorities(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calcula prioridad avanzada considerando múltiples factores.
    
    Args:
        chunks: Lista de chunks originales
        
    Returns:
        List[Dict]: Chunks con priority_score calculado
    """
    total_chunks = len(chunks)
    
    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "")
        position_in_doc = i / total_chunks  # 0.0 = inicio, 1.0 = final
        
        priority_score = calculate_sophisticated_priority(text, position_in_doc)
        chunk["priority_score"] = priority_score
    
    return chunks

def calculate_sophisticated_priority(text: str, position_in_doc: float) -> float:
    """
    Cálculo sofisticado de prioridad con múltiples factores.
    
    Args:
        text: Texto del chunk
        position_in_doc: Posición relativa en documento (0.0-1.0)
        
    Returns:
        float: Score de prioridad (0.0-1.0)
    """
    if not text:
        return 0.0
    
    score = 0.0
    text_upper = text.upper()
    words = text.split()
    
    # --- Factor 1: Densidad de keywords (no solo presencia) ---
    keywords_score = calculate_keyword_density_score(text_upper, len(words))
    score += keywords_score * 0.4  # 40% del peso total
    
    # --- Factor 2: Proximidad de keywords importantes ---
    proximity_score = calculate_keyword_proximity_score(text_upper)
    score += proximity_score * 0.2  # 20% del peso
    
    # --- Factor 3: Detección de secciones importantes ---
    section_score = calculate_section_importance_score(text_upper)
    score += section_score * 0.2  # 20% del peso
    
    # --- Factor 4: Posición en documento (inicio más importante) ---
    position_score = calculate_position_score(position_in_doc)
    score += position_score * 0.1  # 10% del peso
    
    # --- Factor 5: Patrones específicos de pólizas ---
    pattern_score = calculate_pattern_score(text)
    score += pattern_score * 0.1  # 10% del peso
    
    return min(1.0, score)

def calculate_keyword_density_score(text_upper: str, word_count: int) -> float:
    """Calcula score basado en densidad de keywords."""
    if word_count == 0:
        return 0.0
    palabras_clave = ["POLIZA", "CERTIFICADO", "PRIMA", "VIGENCIA", "COMISION",
                     "SUMARIO", "NOMBRE", "ASEGURADO", "DIRECCIÓN","PRIMA",
                     "ENDOSO"]
    
    keywords_found = sum(1 for keyword in palabras_clave
                        if keyword.upper() in text_upper)
    
    # Densidad = keywords encontradas / total de palabras
    density = keywords_found / word_count
    
    # Score base por keywords
    base_score = min(0.8, keywords_found * 0.1)
    
    # Bonus por alta densidad
    density_bonus = min(0.2, density * 2)
    
    return base_score + density_bonus

def calculate_keyword_proximity_score(text_upper: str) -> float:
    """Calcula score por proximidad de keywords importantes."""
    # Combinaciones importantes para pólizas
    high_value_combinations = [
        ["PRIMA", "ANUAL"],
        ["VIGENCIA", "POLIZA"],
        ["COBERTURA", "BASICA"],
        ["SUMA", "ASEGURADA"],
        ["DEDUCIBLE", "PRIMA"],
        ["BENEFICIARIO", "ASEGURADO"]
    ]
    
    score = 0.0
    
    for combo in high_value_combinations:
        # Buscar si ambas palabras están cerca (dentro de 50 caracteres)
        for keyword1 in combo:
            if keyword1 in text_upper:
                for keyword2 in combo:
                    if keyword2 != keyword1 and keyword2 in text_upper:
                        # Calcular distancia
                        pos1 = text_upper.find(keyword1)
                        pos2 = text_upper.find(keyword2)
                        distance = abs(pos1 - pos2)
                        
                        if distance < 50:  # Dentro de 50 caracteres
                            score += 0.15
                            break
    
    return min(0.6, score)

def calculate_section_importance_score(text_upper: str) -> float:
    """Detecta si el chunk pertenece a secciones importantes."""
    # Patrones de secciones críticas
    critical_sections = [
        r'^COBERTURA[S]?\b',
        r'^PRIMA\b',
        r'^VIGENCIA\b', 
        r'^SUMA ASEGURADA\b',
        r'^BENEFICIARIO[S]?\b',
        r'^DATOS DEL ASEGURADO\b',
        r'^CONDICIONES PARTICULARES\b'
    ]
    
    score = 0.0
    
    for pattern in critical_sections:
        if re.search(pattern, text_upper):
            score += 0.3
            break  # Solo un bonus por sección
    
    return min(0.5, score)

def calculate_position_score(position_in_doc: float) -> float:
    """Score basado en posición en documento (inicio más importante)."""
    if position_in_doc < 0.4:  # Primeros 40%
        return 0.4
    elif position_in_doc < 0.7:  # Siguiente 30%
        return 0.2
    else:  # Resto del documento
        return 0.0

def calculate_pattern_score(text: str) -> float:
    """Score por patrones específicos relevantes."""
    score = 0.0
    
    # Números de póliza largos
    if re.search(r'\d{6,}', text):
        score += 0.1
    
    # Fechas
    if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text):
        score += 0.1
        
    # Montos monetarios
    if re.search(r'[\$\€\£]\s*[\d,]+|\d+\s*(?:PESOS|DOLARES|EUROS)', text.upper()):
        score += 0.1
    
    # Porcentajes
    if re.search(r'\d+\s*%', text):
        score += 0.05
    
    return min(0.3, score)

def apply_dynamic_ranking(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aplica sistema de ranking dinámico en lugar de umbrales fijos.
    
    Args:
        chunks: Chunks con priority_score calculado
        
    Returns:
        List[Dict]: Chunks ordenados con priority_level asignado
    """
    # Ordenar por prioridad descendente
    sorted_chunks = sorted(chunks, key=lambda x: x.get("priority_score", 0.0), reverse=True)
    
    total_chunks = len(sorted_chunks)
    
    # Distribución dinámica: 25% high, 35% medium, 40% low
    high_count = max(1, int(total_chunks * 0.25))
    medium_count = int(total_chunks * 0.35)
    
    for i, chunk in enumerate(sorted_chunks):
        if i < high_count:
            chunk["priority_level"] = "high"
        elif i < high_count + medium_count:
            chunk["priority_level"] = "medium"
        else:
            chunk["priority_level"] = "low"
    
    return sorted_chunks

def intelligent_chunk_selection(ranked_chunks: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Selección inteligente de chunks basada en múltiples criterios.
    
    Args:
        ranked_chunks: Chunks ya ordenados por prioridad
        
    Returns:
        tuple: (chunks_seleccionados, estadisticas_seleccion)
    """
    if not ranked_chunks:
        return [], {"method": "empty", "skipped": 0}
    
    # Estrategia 1: Límite por tokens (preferido)
    target_tokens = 4000  # Objetivo de tokens totales
    selected_chunks = []
    current_tokens = 0
    
    for chunk in ranked_chunks:
        chunk_tokens = chunk.get("token_count", 0)
        if current_tokens + chunk_tokens <= target_tokens:
            selected_chunks.append(chunk)
            current_tokens += chunk_tokens
        else:
            # Si quedan pocos tokens pero es chunk de alta prioridad, incluir anyway
            if chunk.get("priority_level") == "high" and len(selected_chunks) < 8:
                selected_chunks.append(chunk)
                current_tokens += chunk_tokens
    
    # Estrategia 2: Mínimo de chunks importantes si tokens no alcanzaron
    if len(selected_chunks) < 6:
        # Asegurar al menos 10 chunks o todos los high + algunos medium
        high_chunks = [c for c in ranked_chunks if c.get("priority_level") == "high"]
        medium_chunks = [c for c in ranked_chunks if c.get("priority_level") == "medium"]
        
        needed = max(10, len(high_chunks) + min(5, len(medium_chunks)))
        selected_chunks = ranked_chunks[:needed]
        current_tokens = sum(c.get("token_count", 0) for c in selected_chunks)
    
    skipped = len(ranked_chunks) - len(selected_chunks)
    
    stats = {
        "method": "token_optimized" if current_tokens <= target_tokens else "minimum_guaranteed",
        "target_tokens": target_tokens,
        "actual_tokens": current_tokens,
        "skipped": skipped
    }
    
    return selected_chunks, stats