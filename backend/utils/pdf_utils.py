from pathlib import Path
from typing import Tuple, Dict
from paddleocr import PaddleOCR
import logging

# Configure logger
logger = logging.getLogger(__name__)

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Constantes
MIN_TEXT_LENGTH = 10
MAX_PAGES = 15

def try_pymupdf_extraction(file_path: Path) -> bool:
    """Intenta extraer texto usando PyMuPDF."""
    if not PYMUPDF_AVAILABLE:
        return False
        
    try:
        doc = fitz.open(str(file_path))
        if doc.page_count == 0:
            doc.close()
            return False
        first_page = doc[0]
        test_text = first_page.get_text().strip()
        doc.close()
        
        # Validación más inteligente: caracteres alfanuméricos
        meaningful_chars = sum(1 for c in test_text if c.isalnum())
        return meaningful_chars > MIN_TEXT_LENGTH
    except Exception:
        return False

def try_pdfplumber_extraction(file_path: Path) -> bool:
    """Intenta extraer texto usando pdfplumber."""
    if not PDFPLUMBER_AVAILABLE:
        return False
        
    try:
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                return False
            test_text = pdf.pages[0].extract_text() or ""
            meaningful_chars = sum(1 for c in test_text.strip() if c.isalnum())
            return meaningful_chars > MIN_TEXT_LENGTH
    except Exception:
        return False

def try_pypdf2_extraction(file_path: Path) -> bool:
    """Intenta extraer texto usando PyPDF2."""
    if not PYPDF2_AVAILABLE:
        return False
        
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            if not reader.pages:
                return False
            test_text = reader.pages[0].extract_text() or ""
            meaningful_chars = sum(1 for c in test_text.strip() if c.isalnum())
            return meaningful_chars > MIN_TEXT_LENGTH
    except Exception:
        return False

def validate_extractable_text(file_path: Path) -> Tuple[bool, str]:
    """
    Valida si el PDF tiene texto extraíble usando múltiples estrategias.
    
    Returns:
        tuple: (has_extractable_text, extraction_method_used)
    """
    # Estrategias de extracción en orden de preferencia
    strategies = [
        ("PyMuPDF", try_pymupdf_extraction),
        ("pdfplumber", try_pdfplumber_extraction), 
        ("PyPDF2", try_pypdf2_extraction)
    ]
    
    for strategy_name, extraction_func in strategies:
        try:
            logger.info(f"Probando extracción con {strategy_name}...")
            if extraction_func(file_path):
                logger.debug(f"{strategy_name} extrajo texto correctamente")
                return True, strategy_name
        except Exception as e:
            logger.warning(f"{strategy_name} falló: {e}")
            continue
    
    logger.error("Todas las estrategias de extracción fallaron o no encontraron texto suficiente")
    return False, "none"

def validate_pdf_integrity(file_path: Path) -> Tuple[bool, str, int, dict]:
    """
    Valida la integridad básica del PDF.
    
    Returns:
        tuple: (is_valid, error_message, page_count, metadata)
    """
    if not PYMUPDF_AVAILABLE:
        # Fallback si fitz no está disponible, asumimos válido si existe
        return True, "", 1, {}

    try:
        doc = fitz.open(str(file_path))
        
        # Verificar protección por contraseña
        if doc.needs_pass:
            doc.close()
            return False, "PDF protegido con contraseña no soportado", 0, {}
        
        # Verificar número de páginas
        page_count = doc.page_count
        if page_count == 0:
            doc.close()
            return False, "PDF no contiene páginas válidas", 0, {}
        
        # Verificar integridad básica intentando acceder a la primera página
        try:
            first_page = doc[0]
            _ = first_page.rect  # Verificar que la página es accesible
        except Exception:
            doc.close()
            return False, "PDF corrupto: no se puede acceder a las páginas", 0, {}
        
        # Obtener metadatos
        metadata = doc.metadata or {}
        doc.close()
        
        return True, "", page_count, metadata
        
    except Exception as e:
        return False, f"Error inesperado analizando PDF: {str(e)}", 0, {}

def extract_with_pymupdf(file_path: Path, MAX_PAGES) -> Tuple[str, Dict[int, str]]:
    """Extrae texto usando PyMuPDF."""
    if not PYMUPDF_AVAILABLE:
         raise ImportError("PyMuPDF (fitz) no está disponible")

    raw_text = ""
    page_data = {}
    
    doc = fitz.open(str(file_path))
    try:
        pages_to_process = min(MAX_PAGES, doc.page_count)
        
        for page_num in range(pages_to_process):
            page = doc[page_num]
            page_text = page.get_text().strip()
            
            if len(page_text) > 20:  # Mínimo 20 caracteres para ser válido
                page_data[page_num + 1] = page_text
                raw_text += f"\n--- PÁGINA {page_num + 1} ---\n{page_text}\n"
                
    finally:
        doc.close()
    
    return raw_text, page_data


def extract_with_pdfplumber(file_path: Path, MAX_PAGES) -> Tuple[str, Dict[int, str]]:
    """Extrae texto usando pdfplumber."""
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError("pdfplumber no está disponible")
    
    raw_text = ""
    page_data = {}
    
    with pdfplumber.open(file_path) as pdf:
        pages_to_process = pdf.pages[:MAX_PAGES]
        
        for page_num, page in enumerate(pages_to_process, 1):
            page_text = page.extract_text() or ""
            page_text = page_text.strip()
            
            if len(page_text) > 20:  # Mínimo 20 caracteres para ser válido
                page_data[page_num] = page_text
                raw_text += f"\n--- PÁGINA {page_num} ---\n{page_text}\n"
    
    return raw_text, page_data


def extract_with_pypdf2(file_path: Path, MAX_PAGES) -> Tuple[str, Dict[int, str]]:
    """Extrae texto usando PyPDF2."""
    if not PYPDF2_AVAILABLE:
        raise ImportError("PyPDF2 no está disponible")
    
    raw_text = ""
    page_data = {}
    
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        pages_to_process = reader.pages[:MAX_PAGES]
        
        for page_num, page in enumerate(pages_to_process, 1):
            page_text = page.extract_text() or ""
            page_text = page_text.strip()
            
            if len(page_text) > 20:  # Mínimo 20 caracteres para ser válido
                page_data[page_num] = page_text
                raw_text += f"\n--- PÁGINA {page_num} ---\n{page_text}\n"
    
    return raw_text, page_data



def ocr_full_text(img_path):
    ocr = PaddleOCR(
        lang="en",
        use_textline_orientation=True, 
        use_doc_orientation_classify=True,
        use_doc_unwarping=True
    )
    result = ocr.ocr(img_path) # Ejecutar OCR

    if not result:
        return {"texto_completo": "", "lineas": []}

    data = result[0]
    lines = data.get("rec_texts", [])
    full_text = "\n".join(lines)
    return {
        "texto_completo": full_text,
        "lineas": lines
    }