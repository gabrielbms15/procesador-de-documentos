import logging
import json
import re
from typing import Dict, Tuple, Any, List, Optional
from models.settings import settings
from openai import OpenAI
from models.prompts import build_simple_extraction_prompt
from models.prompts import build_vida_ley_extraction_prompt
from models.prompts import build_health_extraction_prompt
from models.prompts import build_auto_extraction_prompt
from models.prompts import build_sctr_extraction_prompt

logger = logging.getLogger(__name__)

def calculate_and_log_cost(usage, label: str) -> float:
    input_tokens = usage.prompt_tokens      
    output_tokens = usage.completion_tokens
    price_input_1m = 2.50    # Pricing de GPT-4o
    price_output_1m = 10.00
    costo_input = (input_tokens / 1_000_000) * price_input_1m
    costo_output = (output_tokens / 1_000_000) * price_output_1m
    costo_total = costo_input + costo_output 
    print(f"Consumo {label}: In: {input_tokens} | Out: {output_tokens} | Costo: ${costo_total:.6f}")
    return costo_total

def flatten_nested_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplana un JSON anidado a estructura plana.
    OpenAI a veces devuelve datos en sub-objetos como 'informacion_basica', 'asegurados', etc.
    """
    flattened = {}
    
    for key, value in data.items():
        if isinstance(value, dict):
            # Si es un diccionario, expandir sus contenidos al nivel principal
            for subkey, subvalue in value.items():
                flattened[subkey] = subvalue
        else:
            # Si no es diccionario, mantener como está
            flattened[key] = value
    
    return flattened

def perform_hybrid_extraction(client: OpenAI, text: str) -> Dict[str, Any]:
    """
    Realiza una llamada a OpenAI usando el prompt específico para CAMPOS GENERALES.
    """
    system_prompt, user_prompt = build_simple_extraction_prompt(text[:3000])
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        max_tokens=1500, # Reducido, ya que pedimos menos datos
        temperature=settings.llm_temperature,
        top_p=0.9
    )
    content = response.choices[0].message.content.strip()
    #content = clean_json_content(content)
    result = json.loads(content)
    result = flatten_nested_json(result)
    _ = calculate_and_log_cost(response.usage, "General")
    return result

def merge_extracted_data(current: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    merged = current.copy()

    for field, new_value in new.items():
        if new_value is None:
            continue
            
        old_value = merged.get(field)

        # Casos especiales para listas y estructuras complejas
        if field==["lista_asegurados", "asegurados_adicionales"]:
            current_asegurados = merged.get("lista_asegurados", [])
            if isinstance(new_value, list):
                nombres_existentes = {a.get("nombre", "").upper() for a in current_asegurados}
                for nuevo_asegurado in new_value:
                    if nuevo_asegurado.get("nombre", "").upper() not in nombres_existentes:
                        current_asegurados.append(nuevo_asegurado)
                merged["lista_asegurados"] = current_asegurados
            continue
        
        # Lógica de merge estándar
        if not old_value and new_value:
            merged[field] = new_value
        elif isinstance(new_value, str) and isinstance(old_value, str):
            # Preferir valor más largo (supone más información)
            if len(new_value) > len(old_value):
                merged[field] = new_value
        elif isinstance(new_value, (int, float)) and not old_value:
            merged[field] = new_value

    return merged

def perform_vida_ley_extraction(client: OpenAI, text: str) -> Dict[str, Any]:
    """
    Realiza una llamada a OpenAI usando el prompt específico para VIDA LEY.
    """
    system_prompt, user_prompt = build_vida_ley_extraction_prompt(text[:3000])
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        max_tokens=1000,
        temperature=settings.llm_temperature,
        top_p=0.9
    )  
    content = response.choices[0].message.content.strip()
    #content = clean_json_content(content)
    result = json.loads(content)
    result = flatten_nested_json(result)
    _ = calculate_and_log_cost(response.usage, "Vida Ley")
    return result

def perform_health_extraction(client: OpenAI, text: str) -> Dict[str, Any]:
    """
    Realiza una llamada a OpenAI usando el prompt específico para SALUD.
    """
    system_prompt, user_prompt = build_health_extraction_prompt(text[:3000])
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        max_tokens=2000, # Aumentamos un poco por si la lista de asegurados es larga
        temperature=settings.llm_temperature,
        top_p=0.9
    )
    content = response.choices[0].message.content.strip()
    #content = clean_json_content(content)
    result = json.loads(content)
    result = flatten_nested_json(result) # aplana por si anida
    _ = calculate_and_log_cost(response.usage, "Salud")
    return result

def perform_auto_extraction(client: OpenAI, text: str) -> Dict[str, Any]:
    """
    Realiza una llamada a OpenAI usando el prompt específico para AUTOMÓVIL.
    """
    system_prompt, user_prompt = build_auto_extraction_prompt(text[:3000])
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        max_tokens=1000, # Más pequeño, pedimos pocos datos
        temperature=settings.llm_temperature,
        top_p=0.9
    )
    content = response.choices[0].message.content.strip()
    #content = clean_json_content(content)
    result = json.loads(content)  
    result = flatten_nested_json(result)
    _ = calculate_and_log_cost(response.usage, "Vehicular")
    return result

def perform_sctr_extraction(client: OpenAI, text: str) -> Tuple[Dict[str, Any], int, str]:
    """
    Realiza una llamada a OpenAI usando el prompt específico para SCTR.
    """
    system_prompt, user_prompt = build_sctr_extraction_prompt(text[:3000])
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        max_tokens=1000,
        temperature=settings.llm_temperature,
        top_p=0.9
    )
    content = response.choices[0].message.content.strip()
    #content = clean_json_content(content)
    result = json.loads(content)
    result = flatten_nested_json(result)
    _ = calculate_and_log_cost(response.usage, "SCTR")
    return result
        
