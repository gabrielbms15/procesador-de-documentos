from fastapi.testclient import TestClient
from main import app
import pandas as pd
import io

client = TestClient(app)

def test_export_invoice():
    payload = [
        {
            "factura": {
                "numero_factura": "F001-123",
                "fecha_emision": "10/10/2023"
            },
            "emisor": {
                "razon_social": "Empresa A",
                "ruc": "20123456789",
                "direccion": "Av. Siempre Viva 123"
            },
            "cliente": {
                "razon_social": "Cliente B",
                "ruc": "10987654321",
                "direccion": "Calle Falsa 123"
            },
            "detalles": {
                "moneda": "SOLES",
                "Cantidad": "10",
                "Unidad Medida": "UND",
                "Descripción": "Producto de prueba",
                "Valor Unitario": "50.00"
            }
        },
        {
            "factura": {
                "numero_factura": "F001-124", 
                "fecha_emision": "11/10/2023"
            },
            "detalles": {
                "moneda": "DOLARES",
                "Cantidad": "5"
            }
        }
    ]

    response = client.post("/export/invoice", json=payload)
    
    assert response.status_code == 200, f"Error: {response.text}"
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    # Verify content
    content = io.BytesIO(response.content)
    df = pd.read_excel(content, dtype=str)
    
    print("Columns found:", df.columns.tolist())
    print("Rows found:", len(df))
    print("First row keys:", df.iloc[0].to_dict().keys())
    
    # assert "Archivo" in df.columns, "Missing 'Archivo' column"
    assert "Nro Factura" in df.columns, "Missing 'Nro Factura' column"
    assert "Detalle Cantidad" in df.columns, "Missing 'Detalle Cantidad' column - Columns are: " + str(df.columns.tolist())
    
    # Check values
    # We can't query by Archivo anymore, so we check by Nro Factura or index
    row1 = df[df["Nro Factura"] == "F001-123"].iloc[0]
    assert row1["Nro Factura"] == "F001-123", f"Wrong Invoice Num: {row1['Nro Factura']}"
    assert row1["Emisor RUC"] == "20123456789", f"Wrong Emisor RUC: {row1['Emisor RUC']}"
    assert row1["Detalle moneda"] == "SOLES", f"Wrong Currency: {row1['Detalle moneda']}"

    print("Test passed successfully!")

if __name__ == "__main__":
    try:
        test_export_invoice()
    except Exception as e:
        print(f"Test failed: {e}")
