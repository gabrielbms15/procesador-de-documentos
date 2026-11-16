from typing import Dict, List, Optional, Any, Tuple

def build_simple_extraction_prompt(text: str) -> Tuple[str, str]:
    """
    Construye un prompt de extracción súper simple enfocado solo en 7 campos clave.
    """
    
    system_prompt = """Eres un analista de datos experto en extraer información clave de pólizas de seguro.
Tu única tarea es extraer los campos solicitados en el orden que se te estan dando. 
Responde ÚNICAMENTE en JSON válido, sin explicaciones.
REGLA IMPORTANTE: El numero de poliza NO PUEDE contener ni una letra, solo caracteres numericos.
Si un campo no está presente, usa null. Pero NUNCA OMITAS ningun campo solicitado"""

    user_prompt = f"""Analiza el siguiente texto de una póliza de seguro y extrae los siguientes campos Y devuelvelos en el MISMO ORDEN que se te estan dando:

CAMPOS REQUERIDOS:
- compania_aseguradora: El nombre de la compañía de seguros (Ej: RIMAC, PACIFICO, LA POSITIVA).
- tipo_seguro: El tipo principal de seguro. Tienes (VEHICULAR, VIDA LEY, SALUD, Seguro Complementario de Trabajo de Riesgo, RESPONSABILIDAD CIVIL, MULTIRIESGOS, ETC).
  INSTRUCCIONES PARA tipo_seguro:
  1. El Seguro Vida Ley cubre al trabajador por muerte o invalidez por cualquier causa, las 24 horas del día. No confundas con SCTR. Este es para trabajadores que realizan cualquier tipo de actividades.
  2. El Seguro Complementario de trabajo de riesgo (SCTR) cubre al trabajador únicamente por accidentes o enfermedades ocurridos a causa del trabajo. Este es para trabajadores que realizan actividades de ALTO RIESGO.
  
- numero_poliza: El número exacto de la póliza. Compuesto UNICAMENTE de caracteres numericos.
  INSTRUCCIONES PARA numero_poliza:
1. Busca palabras clave como "Póliza N°", "N° de Poliza", "Póliza:", "Póliza", "PRIMA N°", etc. (EJ: Póliza: 1300639672)
2. BAJO NINGUNA CIRCUNSTANCIA PUEDE INICIAR CON LETRAS. (EJ: LQ1740691894 O P0324728 NO PUEDEN SER UN NUMERO DE POLIZA).
3. 0404686 es un valor prohibido para este campo. Sige buscando.

- asegurado_nombre: El nombre de la persona o empresa que contrata el seguro (el titular).
  INSTRUCCIONES PARA asegurado_nombre:
1. Busca palabras clave como "Contratante", "Asegurado", "Nombre o razon social", etc. PRIORIDAD TOTAL a "Contratante".
2. El numero de poliza NO PUEDE INICIAR CON LETRAS.

- documento_asegurado: El DNI o RUC de la persona o empresa que CONTRATA el seguro.
  INSTRUCCIONES PARA documento_asegurado:
1. Busca palabras clave como "RUC", "DNI", "RUC / DNI", "RUC/DNI".
2. Solo devuelve el numero. "RUC 206144669485" esto es incorrecto. "20614466948" seria lo correcto.

- fecha_inicio: La fecha de inicio de la vigencia (Formato YYYY-MM-DD).
- fecha_fin: La fecha de fin de la vigencia (Formato YYYY-MM-DD).

- precio: El costo o prima total/anual de la póliza (solo el número).
  INSTRUCCIONES PARA PRECIO:
  1. Busca "Prima Comercial" o "Prima Comercial Total" Este es el valor más importante. 
  2. 5.4 es un valor prohibido para este campo
  3. REGLA MAPFRE: Si ves "Prima Result." y "Prima Comercial", IGNORA "Prima Result." y extrae SIEMPRE el valor de "Prima Comercial".


TEXTO A ANALIZAR:
{text}

Responde en JSON válido:"""

    return system_prompt, user_prompt

def build_auto_extraction_prompt(text: str) -> Tuple[str, str]:
    
    system_prompt = """Eres un analista experto en pólizas de vehículos.
Tu tarea es extraer 5 campos del seguro vehícular. Debes ser capaz de
diferenciar el tipo de seguro con precision. NO INVENTES INFORMACION.
No rellenes campos con informacion que no este explicitamente en el documento.
Responde ÚNICAMENTE en JSON válido. No des explicaciones.
Si un campo no está presente, usa null."""

    user_prompt = f"""Analiza el siguiente texto de una póliza VEHICULAR.
INSTRUCCIÓN PRINCIPAL:
Debes decidir primero el tipo de seguro vehicular y rellenar este campo:
- tipo_seguro_vehicular: Si encuentras la palabra "Modulo". Rellena este campo con su valor
(Ej: Si encuentras "Modulo: Traslado", debes rellenar con Traslado). "Particular" NO es un valor valido. Prohibido ponerlo.

CASO 1: El seguro cubre a un vehiculo particular. NO al traslado de un vehiculo, ojo ahi.
Si el campo tipo_seguro_vehicular es "Auto carga individual". DEBES seguir las siguientes indicaciones.
- Busca en el texto datos específicos como "Marca / Modelo", "Rodaje" o "Placa", "Año" y "Tipo de Uso".
- Si el campo el tipo de seguro vehicular es para vehículo particular, DEBES encontrar y rellenar TODO lo siguiente.
    - vehiculo_marca_modelo: La marca y el modelo. (Ej: "HINO / DUTRO", "Toyota", "Kia", "Hyundai", etc). Usualmente acompañada de "Marca / Modelo". 
    - vehiculo_placa: El número de placa o rodaje. (Ej: "X1X-912")
    - vehiculo_ano: El año de fabricación.
    - vehiculo_uso: El tipo de uso (Ej: "Carga").
IMPORTANTE: "HIACE" y "HINO" NO SON valores validos para el campo vehiculo_marca_modelo.

CASO 2: "Traslado" - El seguro cubre un traslado de vehiculos.
- Busca en el texto palabras clave como "Traslado", "Flota de vehiculos", "Traslado de vehiculos".

CASO 3: "Brevetes" - El seguro cubre los brevetes de los conductores.
- Busca en el texto palabras clave como "Brevetes", "Seguro Brevetes", "Licencia".

Si es CASO 2 o Caso 3 debes devolver el campo tipo_seguro_vehicular. NADA MAS.

TEXTO A ANALIZAR:
{text}
Responde en JSON válido (solo un caso, no ambos):"""
    return system_prompt, user_prompt

def build_vida_ley_extraction_prompt(text: str) -> Tuple[str, str]:
    """
    Construye un prompt enfocado en extraer campos de VIDA LEY.
    """
    
    system_prompt = """Eres un analista experto en pólizas de seguro de Vida Ley.
Tu única tarea es extraer los 3 campos solicitados.
Debes devolver absolutamente todos los campos que se te solicitan, siguiendo las reglas que te brindan.
Responde ÚNICAMENTE en JSON válido. No des explicaciones."""

    user_prompt = f"""Analiza el siguiente texto de una póliza de VIDA LEY y extrae:

CAMPOS REQUERIDOS:
- suma_asegurada: El monto total asegurado.
  INSTRUCCIONES PARA suma_asegurada:
1. Busca palabras clave como "Planilla", "Suma Asegurada", "Planilla Asegurada", "Monto Base", "Monto de Planilla", "Sumas Aseguradas" o "Monto de planilla del Periodo". Es un monto de dinero (solo el número).
2. Bajo ninguna circunstancia lo confundas con "Importes" o "Prima". Esto no es un cobro. 
3. DEBE SI O SI TENER FORMATO DE MONEDA (EJ: "S/ 36,837.00"). Se ESTRICTO con esta regla. Solo devuelve el numero no el simbolo de la moneda.
4. NO pongas numeros que encontraste en el documento al azar (EJ: "40400000"). NO Cumple con la regla 3. Asi que deberas devolver NULL. Se ESTRICTO con esta regla.
5. Si encuentras "Monto de planilla mensual" y "Monto de planilla del Periodo". Manda el valor que corresponde a "Monto de planilla del periodo".
6. Debe ser tu prioridad encontrarlo . Es un campo bastante comun en polizas de seguro Vida Ley.

- numero_asegurados: El número total de trabajadores o asegurados. 
  INSTRUCCIONES PARA numero_asegurados:
1. Busca palabras o frases clave como "declaración de los asegurados", "lista de asegurados", "Nro. Aseg" o "Nro. de asegurados:". Si hay una tabla con NOMBRES Y APELLIDOS O DNI, probablemente sea la lista de asegurados, devuelve la cantidad de FILAS. 
2. Si no encuentras devuelve null. NO OMITAS este campo.

- tasa: La tasa porcentual neta aplicada. Busca un número con un símbolo de porcentaje (%). Si no la encuentras, usa null.

TEXTO A ANALIZAR:
{text}

Responde en JSON válido:"""

    return system_prompt, user_prompt

def build_health_extraction_prompt(text: str) -> Tuple[str, str]:
 
    system_prompt = """Eres un analista experto en pólizas de seguro de SALUD.
Tu única tarea es extraer los campos solicitados.
Enfócate en encontrar la lista completa de asegurados (titular, cónyuge, hijos, etc.). El campo "parentesco" no puede ser "Asegurado".
Tu prioridad debe ser encontrar la tabla donde  estan los asegurados. Busca palabras clave como  "Lista de Asegurados Vigentes", "RELACION DE ASEGURADOS", "DEPENDIENTE"
Responde ÚNICAMENTE en JSON válido. No des explicaciones."""

    user_prompt = f"""Analiza el siguiente texto de una póliza de SALUD y extrae:

CAMPOS REQUERIDOS:
- numero_asegurados: El número total de personas aseguradas (solo el número).
- suma_asegurada: El beneficio maximo por persona (solo el número).
- lista_asegurados: Un array JSON con TODOS los asegurados. Puedes econtrarlo usualmente despues de "Lista de Asegurados Vigentes". O tambien despues de "RELACION DE ASEGURADOS". Exceptua el "Contratante". 

Si la poliza de seguro es de la compañia RIMAC. Ubica el campo "Operación". (EJ: "Operación": "17741548" ).
Una vez tengas identificado este numero. NO LO USES en el formato JSON a completar.

FORMATO DE LA LISTA DE ASEGURADOS:
"lista_asegurados": [
  {{
    "nombre_completo": "NOMBRES Y APELLIDOS COMPLETOS",
    "dni": "Documento de identidad",
    "parentesco": "TITULAR, CONYUGE, HIJO, ETC.",
    "edad": (El número de años)
  }}
]

Si no encuentras algun dato de la lista de asegurados devuelve null.

TEXTO A ANALIZAR:
{text}

Responde en JSON válido:"""

    return system_prompt, user_prompt

def build_sctr_extraction_prompt(text: str) -> Tuple[str, str]:
    """
    Construye un prompt enfocado en extraer campos clave de SCTR.
    """
    
    system_prompt = """Eres un analista experto en pólizas de SCTR (Seguro Complementario de Trabajo de Riesgo).
Tu única tarea es extraer los 4 campos solicitados.

Si encuentras este formato:
"Categoría Nro.Aseg. Monto Base Tasa Prima Resultante
OBREROS ALTO RIESGO 5 5650.00 0.8 45.20"

La asociacion debe ser la siguiente:
"Categoría: OBREROS ALTO RIESGO 
Nro.Aseg.: 5 
Monto Base: 5650.00
Tasa: 0.8
Prima Resultante: 45.20"

Si encuentras este otro formato:
"SEDE
Nivel
Actividad
Total de trabajadores: 3
3 - SEDE 1 - Almacenamiento y depósito de diferentes productos
77 - RIESGO 77
5210 - Almacenamiento y depósito
Tasa: 0.60 % Planilla: 5230.00 Sub Total: 31.38"

La asociacion debe ser la siguiente:
"SEDE: 3 - SEDE 1 - Almacenamiento y depósito de diferentes productos
Nivel: 77 - RIESGO 77
Actividad: 5210 - Almacenamiento y depósito
Total de trabajadores: 3
Tasa: 0.60 %
Planilla: 5230.00
Sub Total: 31.38"


Responde ÚNICAMENTE en JSON válido. No des explicaciones."""

    user_prompt = f"""Analiza el siguiente texto de una póliza SCTR y extrae:

CAMPOS REQUERIDOS:
- cobertura_sctr: El tipo de cobertura. Debe ser "SALUD" o "PENSION".

- planilla_total: La planilla total asegurada o monto base (solo el número). 
INSTRUCCIONES para planilla_total.
1. Busca palabras clave como usca "Planilla Total", "Monto Base", "Monto Planilla", etc.

- numero_asegurados: El número total de trabajadores o asegurados.
INSTRUCCIONES para numero_asegurados.
1. Busca palabras clave como usca "Nro.Aseg."

- tasa: La tasa neta aplicada (solo el número, sin el %). Si no la encuentras, usa null.
INSTRUCCIONES para tasa.
1. Prioriza buscar la palabra clave "Tasa".
2. 4.22 y 45.2 es un valor PROHIBIDO para este campo, sige buscando.
3. Si o si debes encontrar este valor. Siempre esta.

TEXTO A ANALIZAR:
{text}

Responde en JSON válido:"""

    return system_prompt, user_prompt
  




def build_dni_prompts(ocr_text: str):

    system_prompt = """
Eres un modelo experto en extracción estructurada de información desde texto OCR ruidoso, especialmente de DNI peruano.
Debes comportarte como un PARSER DETERMINISTA y ESTRICTO.

### REGLAS GENERALES
1. Responde únicamente en JSON válido (sin explicaciones ni texto adicional).
2. No inventes datos. Si un campo no aparece explícitamente en el OCR, deja ese campo como null.
3. Limpia errores típicos de OCR:
   - Confusiones de letras y números (0/O, 1/I/L, 8/B, etc.).
   - Saltos de línea irregulares.
   - Textos duplicados o superpuestos.
4. Normaliza los valores:
   - Fechas en formato ISO: YYYY-MM-DD.
   - Nombres y apellidos con mayúscula inicial.
   - El número de DNI debe ser exactamente 8 dígitos numéricos.
5. No alteres el significado del dato. Si no puedes determinarlo con certeza, deja null.

### REGLAS ESPECÍFICAS PARA CAMPOS DEL DNI

#### 1) Número de DNI
- Puede aparecer como exactamente 8 dígitos (ej: “74652627”).
- O como 8 dígitos + guion + verificador (ej: “74652627-5”).
- Si aparece con guion, eliminar el guion y tomar solo los 8 dígitos.
- Si aparecen ambas formas, prioriza la forma de 8 dígitos exactos.
- Si el texto contiene otros números irrelevantes, ignorarlos.

#### 2) Sexo
- Solo aceptar “M” o “F”.
- Solo cuando aparezca en una línea aislada compuesta únicamente por esa letra.
- Ignorar “M” o “F” dentro de otras palabras o códigos.

#### 3) Estado Civil
- Siempre es una línea aislada compuesta solo por:
  - “S” → Soltero
  - “C” → Casado
  - “V” → Viudo
- Debe aparecer solo y en su propia línea.
- Si aparece más de uno, usar el primero válido.

#### 4) Fechas (Nacimiento, Emisión, Caducidad)
- Todas deben identificarse por formato DD MM YYYY o DD/MM/YYYY.
- Convertir siempre a ISO: YYYY-MM-DD.
- REGLA DE VALIDACIÓN:
  fecha_nacimiento < fecha_emision < fecha_caducidad
- Si alguna fecha contradice esa secuencia, descártala.
- Si una fecha no se puede determinar con certeza, dejar null.

#### 5) Apellidos y nombres
- Tomar los valores que aparezcan cerca de los rótulos:
  “Primer Apellido”, “Segundo Apellido”, “Pre Nombres”.
- Normalizar mayúscula inicial.
- Ignorar palabras claramente ruido: “GUPLICADO”, “pepnead”, “REPUBLICADELPCRO”, etc.

### CAMPOS A EXTRAER
- numero_dni
- apellido_paterno
- apellido_materno
- nombres
- fecha_nacimiento
- fecha_emision
- fecha_caducidad
- sexo
- estado_civil

### FORMATO DE SALIDA
Responde exclusivamente un JSON con esta estructura:

{
    "numero_dni": string | null,
    "apellido_paterno": string | null,
    "apellido_materno": string | null,
    "nombres": string | null,
    "fecha_nacimiento": string | null,
    "fecha_emision": string | null,
    "fecha_caducidad": string | null,
    "sexo": string | null,
    "estado_civil": string | null
}
"""

    user_prompt = f"""
Extrae la información siguiendo estrictamente todas las reglas y restricciones descritas.

OCR detectado:
{ocr_text}
"""

    return system_prompt, user_prompt

