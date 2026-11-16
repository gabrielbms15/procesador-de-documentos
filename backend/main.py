import uvicorn
import shutil
import os
import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import StreamingResponse
from pathlib import Path
from pipeline import InsurancePDFPipeline, InvoicePipeline, IdentityDocumentPipeline
from dotenv import load_dotenv
import pandas as pd
import io
from pydantic import BaseModel
from typing import Dict, Optional, Any, List


# Cargar variables de entorno
load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Microservicio de Extracción de Seguros")

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Modelos para Exportación ===
class FacturaData(BaseModel):
    numero_factura: Optional[str] = None
    fecha_emision: Optional[str] = None

class EmisorData(BaseModel):
    razon_social: Optional[str] = None
    direccion: Optional[str] = None
    ruc: Optional[str] = None

class ClienteData(BaseModel):
    razon_social: Optional[str] = None
    ruc: Optional[str] = None
    direccion: Optional[str] = None

class DetallesData(BaseModel):
    moneda: Optional[str] = None
    Cantidad: Optional[str] = None
    Unidad_Medida: Optional[str] = None  # Mapping names with spaces
    Descripcion: Optional[str] = None
    Valor_Unitario: Optional[str] = None

    class Config:
        # Permite mapear campos como "Unidad Medida" a "Unidad_Medida" si fuera necesario, 
        # pero aqui recibiremos el JSON tal cual. 
        # Si el JSON viene con espacios, Pydantic lo puede manejar con alias o via dict.
        extra = "allow" 

class InvoiceData(BaseModel):
    factura: Optional[FacturaData] = None
    emisor: Optional[EmisorData] = None
    cliente: Optional[ClienteData] = None
    detalles: Optional[Dict[str, Any]] = None # Usamos Dict para flexibilidad con los campos variables del detalle



# Directorio temporal
TEMP_DIR = Path("temp_uploads")
TEMP_DIR.mkdir(exist_ok=True)

# === 1. Endpoint de Salud (Microservicio "Good Practice") ===
@app.get("/health")
def health_check():
    return {"status": "ok"}

# === 2. Endpoint Principal (Tu Lógica) ===
@app.post("/extract/insurance")
async def extract_data(file: UploadFile = File(...)):
    file_location = TEMP_DIR / file.filename
    try:
        # Guardar archivo
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Ejecutar Pipeline
        pipeline = InsurancePDFPipeline()
        result = await pipeline.process(
            file_path=str(file_location),
            filename=file.filename
        )
        
        return result

    except Exception as e:
        # Log del error en la consola del microservicio
        print(f"Error crítico procesando {file.filename}: {e}")
        traceback.print_exc()
        # Devolver error 500 a NestJS para que sepa que falló
        raise HTTPException(status_code=500, detail=f"Error interno del modelo: {str(e)}")
        
    finally:
        # Limpieza siempre
        if file_location.exists():
            os.remove(file_location)

@app.post("/extract/invoice")
async def extract_invoice(file: UploadFile = File(...)):
    file_location = TEMP_DIR / file.filename
    try:
        # Guardar archivo (Reutilizamos la lógica, el archivo físico es el mismo)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Ejecutar Pipeline de Facturas
        # Aquí es donde cambiamos la clase que instanciamos
        pipeline = InvoicePipeline() 
        
        result = await pipeline.process(
            file_path=str(file_location),
            filename=file.filename
        )
        
        return result

    except Exception as e:
        print(f"[Invoice] Error crítico procesando {file.filename}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno del modelo (Facturas): {str(e)}")
        
    finally:
        # Limpieza
        if file_location.exists():
            os.remove(file_location)

@app.post("/export/invoice")
async def export_invoice(data: List[InvoiceData] = Body(...)):
    try:
        # Aplanar datos para el DataFrame
        rows = []
        for index, invoice in enumerate(data):
            # Obtener el numero de factura para usarlo como referencia si existe, sino el indice
            nro_factura = invoice.factura.numero_factura if invoice.factura else f"Item {index + 1}"
            
            row = {
                "Nro Factura": invoice.factura.numero_factura if invoice.factura else None,
                "Fecha Emisión": invoice.factura.fecha_emision if invoice.factura else None,
                "Emisor Razón Social": invoice.emisor.razon_social if invoice.emisor else None,
                "Emisor RUC": invoice.emisor.ruc if invoice.emisor else None,
                "Cliente Razón Social": invoice.cliente.razon_social if invoice.cliente else None,
                "Cliente RUC": invoice.cliente.ruc if invoice.cliente else None,
            }
            
            # Agregar detalles planos
            if invoice.detalles:
                # Copiamos todo lo que hay en detalles al nivel raiz del row
                for k, v in invoice.detalles.items():
                    row[f"Detalle {k}"] = v
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Generar Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Facturas')
        
        output.seek(0)
        
        headers = {
            'Content-Disposition': 'attachment; filename="reporte_facturas.xlsx"'
        }
        
        return StreamingResponse(
            output, 
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
            headers=headers
        )

    except Exception as e:
        print(f"[Export] Error generando excel: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generando reporte: {str(e)}")


@app.post("/extract/identity")
async def extract_identity(file: UploadFile = File(...)):
    file_location = TEMP_DIR / file.filename
    try:
        # Guardar archivo (imagen)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Ejecutar Pipeline de Identidad
        pipeline = IdentityDocumentPipeline() 
        
        result = await pipeline.process(
            file_path=str(file_location),
            filename=file.filename
        )
        
        return result

    except Exception as e:
        print(f"[Identity] Error crítico procesando {file.filename}: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno del modelo (Identidad): {str(e)}")
        
    finally:
        # Limpieza
        if file_location.exists():
            os.remove(file_location)

@app.post("/extract/license")
async def extract_license(file: UploadFile = File(...)):
    """Endpoint para licencias (preparado para integración de modelo)."""
    return {
        "tipo_documento": "Licencia",
        "nombre_archivo": file.filename,
        "estado": "Documento recibido",
        "nota": "Pipeline específico de licencias en preparación"
    }

@app.post("/extract/contract")
async def extract_contract(file: UploadFile = File(...)):
    """Endpoint para contratos (preparado para integración de modelo)."""
    return {
        "tipo_documento": "Contrato",
        "nombre_archivo": file.filename,
        "estado": "Documento recibido",
        "nota": "Pipeline específico de contratos en preparación"
    }

if __name__ == "__main__":
    # En producción, usualmente el host es 0.0.0.0 para que Docker lo exponga
    uvicorn.run(app, host="0.0.0.0", port=8001)
