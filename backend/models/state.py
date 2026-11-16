from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# === MODELOS AUXILIARES (Solo lo esencial) ===

class DocumentInfo(BaseModel):
    """Información del documento."""
    file_path: str = Field(default="", description="Ruta del archivo")
    filename: str = Field(default="", description="Nombre del archivo")
    text: Optional[str] = Field(default=None, description="Texto extraído")

class ChunkData(BaseModel):
    """Datos de segmentación."""
    text_chunks: List[Dict[str, Any]] = Field(default_factory=list, description="Chunks de texto originales")
    filtered_chunks: List[Dict[str, Any]] = Field(default_factory=list, description="Chunks filtrados")

class ProcessingControl(BaseModel):
    """Control de flujo del procesamiento."""
    processing_stage: str = Field(default="ingestion", description="Etapa actual de procesamiento")
    status: str = Field(default="PROCESSING", description="Estado del procesamiento")
    
class LoggingData(BaseModel):
    """Datos de logging y debug (SOLO lo esencial)."""
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    # 'debug_info' es CRÍTICO para que 'extraction' pase 'page_data' a 'segmentation'
    debug_info: Dict[str, Any] = Field(default_factory=dict)

# === MODELO PRINCIPAL (SIMPLIFICADO) ===

class PipelineState(BaseModel):
    """
    Estado del pipeline (Versión MVP).
    """
    
    model_config = ConfigDict(
        extra='allow',
        validate_assignment=True,
    )
    
    # === COMPOSICIÓN (Solo lo esencial) ===
    document_info: DocumentInfo = Field(default_factory=DocumentInfo)
    chunk_data: ChunkData = Field(default_factory=ChunkData)
    processing_control: ProcessingControl = Field(default_factory=ProcessingControl)
    logging: LoggingData = Field(default_factory=LoggingData)
    
    # === DATOS EXTRAÍDOS ===
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="El JSON simple extraído por el LLM")
    
    # === CONTROL DE EXTRACCIÓN (Usado por llm_processing.py) ===
    tipo_seguro_detectado: Optional[str] = Field(default=None, description="Tipo de seguro detectado")
    extraccion_especializada_realizada: bool = Field(default=False)
    fase_extraccion: str = Field(default="basica")
    
    
    # === MÉTODOS DE ESTADO (Simplificados) ===
    
    def update_stage(self, stage: str) -> 'PipelineState':
        """Actualizar etapa de procesamiento."""
        self.processing_control.processing_stage = stage
        # (Se eliminó el 'add_message')
        return self
    
    def add_error(self, error: str) -> 'PipelineState':
        """Agregar error al estado."""
        self.logging.errors.append(error)
        self.processing_control.status = "FAILED"
        return self
    
    def add_warning(self, warning: str) -> 'PipelineState':
        """Agregar warning al estado."""
        self.logging.warnings.append(warning)
        return self
    
    def update_debug_info(self, updates: dict) -> None:
        """
        Actualiza el diccionario debug_info.
        CRÍTICO para la comunicación entre nodos.
        """
        if not hasattr(self, "logging") or not isinstance(self.logging.debug_info, dict):
            self.logging.debug_info = {}
        self.logging.debug_info.update(updates)
    
    def actualizar_tipo_seguro(self, tipo_seguro: str) -> 'PipelineState':
        """Actualiza el tipo de seguro detectado (Usado por Fase 1)"""
        self.tipo_seguro_detectado = tipo_seguro
        # (Se eliminó la lógica de 'PolizaCompleta')
        return self
    
    def marcar_extraccion_especializada(self) -> 'PipelineState':
        """Marca que se completó la extracción especializada (Usado por Fase 2)"""
        self.extraccion_especializada_realizada = True
        self.fase_extraccion = "especializada"
        return self