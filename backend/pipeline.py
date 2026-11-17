import logging
import traceback
import os 
import json 
import base64
import fitz  # PyMuPDF
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv
from typing import Dict, Any
import uuid
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from models.state import PipelineState, DocumentInfo
from nodes import document_ingestion_node, text_extraction_node, text_cleaning_node, intelligent_chunking_node, filtering_node, llm_processing_node
from models.state import PipelineState as _PipelineState
from models.prompts import build_dni_prompts


logger = logging.getLogger("Pipeline")
class InsurancePDFPipeline:
    def __init__(self):
        self.graph = None
        self.app = None
        self.initialize_pipeline()
    
    def initialize_pipeline(self):
        # DEFINIR NODOS
        workflow = StateGraph(PipelineState)
        workflow.add_node("document_ingestion", document_ingestion_node)
        workflow.add_node("text_extraction", text_extraction_node)
        workflow.add_node("text_cleaning", text_cleaning_node)
        workflow.add_node("intelligent_chunking", intelligent_chunking_node)
        workflow.add_node("filtering", filtering_node)
        workflow.add_node("llm_processing", llm_processing_node)
            
        # DEFINIR FLUJO
        workflow.set_entry_point("document_ingestion") # Punto de entrada
        workflow.add_edge("document_ingestion", "text_extraction") # Flujo secuencial
        workflow.add_edge("text_extraction", "text_cleaning")
        workflow.add_edge("text_cleaning", "intelligent_chunking")
        workflow.add_edge("intelligent_chunking", "filtering")
        workflow.add_edge("filtering", "llm_processing")
        workflow.add_edge("llm_processing",END)

        # COMPILAR GRAFO
        memory = MemorySaver()
        self.app = workflow.compile(checkpointer=memory)
    
    async def process(self, file_path: str, filename: str) -> Dict[str, Any]:
        """
        Procesa un archivo PDF a través del pipeline.
        Args:
            file_path (str): Ruta del archivo PDF a procesar.
            filename (str): Nombre del archivo PDF.
        Returns:
            Dict[str, Any]: Resultado del procesamiento del pipeline.
        """
        
        initial_state = self.create_initial_state(file_path, filename)      # crea estado inicial
        thread_id = str(uuid.uuid4())                                       # Usar un thread_id único para el checkpointer
        config = {"configurable": {"thread_id": thread_id}}
        final_state = await self.app.ainvoke(initial_state, config=config)  # Ejecuta el grafo

        # En algunos casos el checkpointer puede devolver un dict en vez
        # de una instancia de PipelineState. Normalizar a PipelineState si fuera necesario.

        if isinstance(final_state, dict):
            try:
                # Intentar construir PipelineState desde el dict (pydantic v2 usa model_validate)
                if hasattr(_PipelineState, 'model_validate'):
                    final_state = _PipelineState.model_validate(final_state)
                else:
                    final_state = _PipelineState(**final_state)
            except Exception:
                logger.warning("final_state es un dict y no pudo validarse como PipelineState. Usando dict crudo.")

        # A este punto final_state puede ser PipelineState o dict.
        def fs_get(key, default=None):
            try:
                if isinstance(final_state, dict):
                    return final_state.get(key, default)
                return getattr(final_state, key, default)
            except Exception:
                return default

        
        extracted_data_only = fs_get("extracted_data") # LA DATA QUE NOS INTERESA
        return extracted_data_only


    def create_initial_state(self, file_path: str, filename: str) -> PipelineState:
        """Crear estado inicial simplificado."""
        document_info = DocumentInfo(
            file_path=file_path,
            filename=filename
        )
        return PipelineState(document_info=document_info)
    
from utils.invoice_parser import extraer_factura_final

class InvoicePipeline:
    def __init__(self):
        pass
        
    async def process(self, file_path: str, filename: str) -> Dict[str, Any]:
        return extraer_factura_final(file_path)

class IdentityDocumentPipeline:
    def __init__(self):
        from models.settings import settings
        api_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
        self.client = OpenAI(api_key=api_key)
        
    async def process(self, file_path: str, filename: str) -> Dict[str, Any]:
        # 1. Convertir documento (imagen o PDF) a Base64 para OpenAI Vision
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            with fitz.open(file_path) as doc:
                page = doc[0]
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")
            mime_type = "image/png"
        else:
            with open(file_path, "rb") as f:
                img_bytes = f.read()
            mime_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
            
        b64_image = base64.b64encode(img_bytes).decode("utf-8")
        
        # 2. LLM Vision Processing
        system_prompt, _ = build_dni_prompts("")
        user_text = (
            "Analiza detalladamente la imagen de este Documento Nacional de Identidad (DNI) "
            "y extrae todos los campos requeridos en el formato JSON especificado. "
            "Sigue estrictamente las reglas de validación y normalización (mayúsculas, fechas YYYY-MM-DD y 8 dígitos de DNI)."
        )
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
