import fitz  # PyMuPDF
import re
import json

def extraer_factura_final(path):
    doc = fitz.open(path)
    texto_raw = doc[0].get_text("text")
    lineas_raw = [line.strip() for line in texto_raw.splitlines() if line.strip()]
    
    # --- 1. CONFIGURACIÓN ---
    RUC_AUSTRAL = "20470005727"
    
    # --- 2. EXTRACCIÓN DEL NÚMERO DE FACTURA ---
    patron_factura = rf"{RUC_AUSTRAL}\s*([E|F]\d{{3}}-\d+)"
    match_factura = re.search(patron_factura, texto_raw)
    nro_factura = match_factura.group(1) if match_factura else None

    # --- 3. EXTRACCIÓN DE CABECERA (CLIENTE) ---
    patrones_cabecera = {
        "Fecha de Emisión": r"Fecha de Emisión\s*:\s*(\d{2}/\d{2}/\d{4})",
        "Señor(es)": r"Señor\(es\)\s*:\s*(.*?)(?=RUC)",
        "Dirección del Cliente": r"Dirección del Cliente\s*:\s*(.*?)(?=Tipo de Moneda)",
        "Tipo de Moneda": r"Tipo de Moneda\s*:\s*(SOLES|DOLAR AMERICANO|DOLARES|S/|US\$)"
    }
    
    cabecera_cliente = {}
    for campo, patron in patrones_cabecera.items():
        match = re.search(patron, texto_raw, re.DOTALL | re.IGNORECASE)
        if match:
            valor = " ".join(match.group(1).split())
            if campo == "Tipo de Moneda":
                valor = "SOLES" if any(x in valor.upper() for x in ["SOLES", "S/"]) else "DOLARES"
            cabecera_cliente[campo] = valor

    # RUC del Cliente (excluyendo Austral)
    todos_rucs = re.findall(r"(\d{11})", texto_raw)
    ruc_cliente = next((r for r in todos_rucs if r != RUC_AUSTRAL), None)

    # --- 4. EXTRACCIÓN DE TABLA (DETALLE) ---
    item_tabla = {}
    if "ICBPER" in lineas_raw:
        idx_inicio = lineas_raw.index("ICBPER") + 1
        idx_fin = next(
            (i for i, line in enumerate(lineas_raw)
             if "Valor de Venta de Operaciones Gratuitas" in line),
            len(lineas_raw)
        )
        
        pool = lineas_raw[idx_inicio:idx_fin]
        if len(pool) >= 5:
            item_tabla = {
                "Cantidad": pool[0],
                "Unidad Medida": pool[1],
                "Descripción": " ".join(pool[2:-2]),
                "Valor Unitario": pool[-2]
            }

    # --- 5. EXTRACCIÓN DE EMISOR (NUEVO) ---
    emisor = {}

    match_emisor = re.search(r"(.*?)\bS\.A\.C\b(.*?)(?=FACTURA)", texto_raw, re.DOTALL | re.IGNORECASE)
    if match_emisor:
        razon_social = re.sub(r"\s{2,}|\n", " ", match_emisor.group(1)).strip()
        direccion = re.sub(r"\s{2,}|\n", " ", match_emisor.group(2)).strip()

        emisor["razon_social"] = razon_social + " S.A.C"
        emisor["direccion"] = direccion

    # RUC emisor: primer RUC que empieza con 2
    ruc_emisor_match = re.search(r"\b(2\d{10})\b", texto_raw)
    emisor["ruc"] = ruc_emisor_match.group(1) if ruc_emisor_match else None

    # --- 6. ESTRUCTURA FINAL ---
    return {
        "factura": {
            "numero_factura": nro_factura,
            "fecha_emision": cabecera_cliente.get("Fecha de Emisión")
        },
        "emisor": emisor,
        "cliente": {
            "razon_social": cabecera_cliente.get("Señor(es)"),
            "ruc": ruc_cliente,
            "direccion": cabecera_cliente.get("Dirección del Cliente")
        },
        "detalles": {
            "moneda": cabecera_cliente.get("Tipo de Moneda"),
            **item_tabla
        }
    }
