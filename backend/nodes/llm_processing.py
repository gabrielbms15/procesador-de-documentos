import logging
from typing import Dict, Any
from openai import OpenAI
from utils.llm_utils import (
    perform_hybrid_extraction,
    merge_extracted_data, 
    perform_auto_extraction,
    perform_health_extraction,
    perform_vida_ley_extraction,
    perform_sctr_extraction
)
from models.settings import settings
from models.state import PipelineState

def llm_processing_node(state: PipelineState) -> PipelineState:
    """
    MODIFICADO: Procesamiento LLM con lógica condicional para VEHICULAR, SALUD, VIDA LEY y SCTR.
    """
    
    logger = logging.getLogger("LLM Processing")    
    state = state.update_stage("Procesamiento LLM Condicional")
    chunks_to_process = state.chunk_data.filtered_chunks
    if not chunks_to_process:
        return state.add_warning("No hay chunks para procesar con LLM")
    try:
        client = OpenAI(api_key=settings.openai_api_key)
    except Exception as e:
        return state.add_error(f"Error inicializando cliente OpenAI: {str(e)}")

    current_data = state.extracted_data.copy()
    processed_count = 0
    
    # --- Banderas de Control (TODAS INCLUIDAS) ---
    fase_extraccion = "base"
    campos_base_encontrados = False
    campos_auto_encontrados = False
    campos_salud_encontrados = False
    campos_vida_ley_encontrados = False # <-- AHORA SÍ ESTÁ
    campos_sctr_encontrados = False

    # --- Listas de Campos Esenciales y Especificos
    campos_esenciales_base = [
        "compania_aseguradora", "numero_poliza", "tipo_seguro", 
        "asegurado_nombre", "documento_asegurado", "fecha_inicio", 
        "fecha_fin", "precio"
    ]
    campos_esenciales_auto = [
        "tipo_seguro_vehicular", "vehiculo_marca_modelo", "vehiculo_placa", 
        "vehiculo_ano", "vehiculo_uso"
    ]
    campos_esenciales_salud = [
        "numero_asegurados", "suma_asegurada", "lista_asegurados"
    ]
    campos_esenciales_vida_ley = [ # <-- AHORA SÍ ESTÁ
        "suma_asegurada", "numero_asegurados", "tasa"
    ]
    campos_esenciales_sctr = [
        "cobertura_sctr", "numero_asegurados", "planilla_total", "tasa"
    ]

    # === PROCESAMIENTO CONDICIONAL ===
    for i, chunk in enumerate(chunks_to_process[:settings.max_chunks_to_process]):
        chunk_id = f"c{i + 1}"
        
        # --- FASE 1: EXTRACCIÓN BASE ---
        if not campos_base_encontrados:
            extracted_fields = perform_hybrid_extraction(client, chunk.get("text"))
            processed_count += 1

            if extracted_fields:
                current_data = merge_extracted_data(current_data, extracted_fields)
                state.extracted_data = current_data
                
                tipo_detectado = current_data.get("tipo_seguro")
                if tipo_detectado in ["VEHICULOS", "VEHICULAR"]:
                    fase_extraccion = "auto"
                elif tipo_detectado == "SALUD":
                    fase_extraccion = "salud"
                elif tipo_detectado == "VIDA LEY":
                    fase_extraccion = "vida_ley"
                elif tipo_detectado == "Seguro Complementario de Trabajo de Riesgo":
                    fase_extraccion = "sctr"

            if all(current_data.get(f) for f in campos_esenciales_base):
                campos_base_encontrados = True
                

        # --- FASE 2 (AUTO) ---
        if fase_extraccion == "auto" and not campos_auto_encontrados:
            logger.info(f"Procesando chunk {chunk_id} [FASE 2: Auto]")
            auto_fields = perform_auto_extraction(client, chunk.get("text"))
            if auto_fields:
                current_data = merge_extracted_data(current_data, auto_fields)
                state.extracted_data = current_data
            if all(current_data.get(f) for f in campos_esenciales_auto):
                campos_auto_encontrados = True
        
        
        # --- FASE 2 (SALUD) ---
        if fase_extraccion == "salud" and not campos_salud_encontrados:
            logger.info(f"Procesando chunk {chunk_id} [FASE 2: Salud]")
            salud_fields = perform_health_extraction(client, chunk.get("text"))
            if salud_fields:
                current_data = merge_extracted_data(current_data, salud_fields)
                state.extracted_data = current_data
            if (all(current_data.get(f) for f in campos_esenciales_salud) and 
                len(current_data.get("lista_asegurados", [])) > 0):
                campos_salud_encontrados = True


        if fase_extraccion == "vida_ley" and not campos_vida_ley_encontrados:
            logger.info(f"Procesando chunk {chunk_id} [FASE 2: Vida Ley]")
            vida_fields = perform_vida_ley_extraction(client, chunk.get("text"))
            if vida_fields:
                current_data = merge_extracted_data(current_data, vida_fields)
                state.extracted_data = current_data
            # Usamos 'is not None' porque 0 o null son valores válidos
            if all(current_data.get(f) is not None for f in campos_esenciales_vida_ley):
                logger.info("FASE 2: Todos los campos de Vida Ley encontrados.")     
                campos_vida_ley_encontrados = True


        if fase_extraccion == "sctr" and not campos_sctr_encontrados:
            logger.info(f"Procesando chunk {chunk_id} [FASE 2: SCTR]")
            sctr_fields = perform_sctr_extraction(client, chunk.get("text"))
            if sctr_fields:
                current_data = merge_extracted_data(current_data, sctr_fields)
                state.extracted_data = current_data
            if all(current_data.get(f) is not None for f in campos_esenciales_sctr):
                campos_sctr_encontrados = True
        if processed_count >= settings.max_chunks_to_process:
            logger.info("Early stopping: Límite de chunks alcanzado.")
            break

    state.extracted_data = current_data
    return state