"""
Configuración centralizada para el procesador de PDFs de pólizas.
Pydantic Settings V2 compatible con LangGraph.
"""

from typing import Dict
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from dotenv import load_dotenv

# Rutas absolutas a los posibles archivos .env (backend/.env o raíz/.env)
CURRENT_FILE = Path(__file__).resolve()
BACKEND_DIR = CURRENT_FILE.parent.parent
ROOT_DIR = BACKEND_DIR.parent

ENV_FILES = [
    BACKEND_DIR / ".env",
    ROOT_DIR / ".env",
    Path(".env")
]

# Cargar de inmediato en os.environ con python-dotenv
for env_path in ENV_FILES:
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path, override=True)

class Settings(BaseSettings):
    """Configuración principal del sistema usando Pydantic V2."""
    
    # === API KEYS (REQUERIDAS) ===
    openai_api_key: str = Field(default="", description="OpenAI API key")
    
    # === CONFIGURACIÓN DE PROCESAMIENTO ===
    max_tokens_per_chunk: int = Field(default=2500, description="Máximo tokens por chunk")
    max_tokens_total: int = Field(default=5000, description="Máximo tokens total")
    chunk_overlap: int = Field(default=250, description="Solapamiento entre chunks")

    # === CONFIGURACIÓN DE ARCHIVOS ===
    max_pdf_size_mb: int = Field(default=10, gt=0, le=100, description="Tamaño máximo PDF en MB")
    temp_dir: str = Field(default="./temp", description="Directorio temporal")
    
    # === CONFIGURACIÓN DE LLM ===
    llm_model: str = Field(default="gpt-4o-mini", description="Modelo OpenAI a usar")
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="Temperatura del modelo")
    max_retries: int = Field(default=3, ge=1, le=10, description="Máximo reintentos")
    request_timeout: int = Field(default=120, ge=30, le=300, description="Timeout en segundos")
    
    # === CONFIGURACIÓN DE EXTRACCIÓN OPTIMIZADA ===
    max_chunks_to_process: int = Field(default=5, ge=1, le=15, description="Máximo chunks a procesar antes de stopping")
    early_stopping_after_chunks: int = Field(default=3, ge=1, le=8, description="Evaluar early stopping después de N chunks")
    
    # === CONFIGURACIÓN DE LOGGING ===
    log_level: str = Field(default="INFO", description="Nivel de logging")
    enable_file_logging: bool = Field(default=True, description="Habilitar logging a archivo")
    log_file_path: str = Field(default="insurance_processor.log", description="Ruta del archivo de log")
    
    openai_pricing: Dict[str, Dict[str, float]] = Field(
        default={
            "gpt-4o": {"input": 0.0025, "output": 0.01},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002}
        },
        description="Precios de modelos OpenAI para cálculo de costos"
    )
    
    # Configuración del modelo (usando rutas absolutas resueltas)
    model_config = SettingsConfigDict(
        env_file=[str(p) for p in ENV_FILES if p.is_file()] or ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # === VALIDATORS ===
    
    @field_validator('openai_api_key', mode='before')
    @classmethod
    def validate_openai_key(cls, v: str) -> str:
        if v and not v.startswith("sk-"):
            raise ValueError("OpenAI API key debe comenzar con 'sk-'")
        return v or ""

    @field_validator('temp_dir', mode='before')
    @classmethod
    def validate_temp_dir(cls, v: str) -> str:
        """Crear directorio temporal si no existe."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    @field_validator('log_level', mode='before')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validar nivel de logging."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level debe ser uno de: {valid_levels}")
        return v.upper()

# Instancia global de configuración
settings = Settings()