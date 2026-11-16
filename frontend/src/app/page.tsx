"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import Image from "next/image";
import dynamic from "next/dynamic";

// Dynamic import for react-pdf to prevent SSR canvas issues
const Document = dynamic(() => import("react-pdf").then((mod) => mod.Document), { ssr: false });
const Page = dynamic(() => import("react-pdf").then((mod) => mod.Page), { ssr: false });

/* ==========================================================================
   TYPES & SCHEMAS
   ========================================================================== */

export type SchemaType = "insurance" | "invoice" | "identity" | "license" | "contract";

export interface InvoiceData {
  factura?: {
    numero_factura?: string;
    fecha_emision?: string;
  };
  emisor?: {
    razon_social?: string;
    direccion?: string;
    ruc?: string;
  };
  cliente?: {
    razon_social?: string;
    ruc?: string;
    direccion?: string;
  };
  detalles?:
    | {
        moneda?: string;
        Cantidad?: string;
        "Unidad Medida"?: string;
        Descripción?: string;
        "Valor Unitario"?: string;
      }
    | Array<{
        moneda?: string;
        Cantidad?: string;
        "Unidad Medida"?: string;
        Descripción?: string;
        "Valor Unitario"?: string;
      }>;
}

export interface IdentityDocumentData {
  numero_dni?: string;
  apellido_paterno?: string;
  apellido_materno?: string;
  nombres?: string;
  fecha_nacimiento?: string;
  fecha_emision?: string;
  fecha_caducidad?: string;
  sexo?: string;
  estado_civil?: string;
  departamento?: string;
  provincia?: string;
  distrito?: string;
  direccion?: string;
}

export interface InsurancePolicyData {
  compania_aseguradora?: string;
  tipo_seguro?: string;
  numero_poliza?: string;
  asegurado_nombre?: string;
  documento_asegurado?: string;
  fecha_inicio?: string;
  fecha_fin?: string;
  precio?: number | string;

  // Vehicular
  tipo_seguro_vehicular?: string;
  vehiculo_marca_modelo?: string;
  vehiculo_placa?: string;
  vehiculo_ano?: string;
  vehiculo_uso?: string;

  // Vida Ley / SCTR
  suma_asegurada?: number | string;
  numero_asegurados?: number;
  tasa?: number | string;
  cobertura_sctr?: string;
  planilla_total?: number | string;

  // Salud
  lista_asegurados?: Array<{
    nombre_completo: string;
    dni: string;
    parentesco: string;
    edad: number | string;
  }>;
}

export interface GenericDocumentData {
  [key: string]: any;
}

export type ExtractedData =
  | InvoiceData
  | IdentityDocumentData
  | InsurancePolicyData
  | GenericDocumentData
  | null;

export interface DocumentQueueItem {
  id: string;
  file: File;
  name: string;
  size: number;
  docType: SchemaType;
  timestamp: string;
  status: "idle" | "processing" | "completed" | "error";
  data: ExtractedData;
  errorMessage?: string;
}

const DOC_TYPES: { id: SchemaType; label: string }[] = [
  { id: "insurance", label: "Pólizas de seguro" },
  { id: "invoice", label: "Facturas" },
  { id: "identity", label: "DNI" },
  { id: "license", label: "Licencias" },
  { id: "contract", label: "Contratos" },
];

/* ==========================================================================
   MAIN COMPONENT
   ========================================================================== */

export default function DocumentProcessorApp() {
  const [selectedCategory, setSelectedCategory] = useState<SchemaType>("insurance");
  const [queue, setQueue] = useState<DocumentQueueItem[]>([]);
  const [activeItemId, setActiveItemId] = useState<string | null>(null);
  const [workerReady, setWorkerReady] = useState(false);
  const [viewMode, setViewMode] = useState<"form" | "json">("form");
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Initialize PDF worker
  useEffect(() => {
    const initPdf = async () => {
      try {
        const { pdfjs } = await import("react-pdf");
        pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.mjs";
        setWorkerReady(true);
      } catch (err) {
        console.error("Error setting up PDF worker:", err);
      }
    };
    initPdf();
  }, []);

  const activeItem = useMemo(() => {
    return queue.find((item) => item.id === activeItemId) || queue[0] || null;
  }, [queue, activeItemId]);

  const formatDateTime = (date: Date): string => {
    return date.toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getDocTypeBadge = (type: SchemaType) => {
    switch (type) {
      case "insurance":
        return { text: "Póliza", bg: "bg-terracota/10 text-terracota border-terracota/30" };
      case "invoice":
        return { text: "Factura", bg: "bg-concreto/10 text-concreto-dark border-concreto/30" };
      case "identity":
        return { text: "DNI", bg: "bg-naranja/10 text-naranja border-naranja/30" };
      case "license":
        return { text: "Licencia", bg: "bg-arena/20 text-arena-dark border-arena/40" };
      case "contract":
        return { text: "Contrato", bg: "bg-industrial-200 text-concreto-dark border-industrial-300" };
    }
  };

  // Upload and process documents
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;

    const filesArray = Array.from(e.target.files);
    const newItems: DocumentQueueItem[] = filesArray.map((file) => ({
      id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      file,
      name: file.name,
      size: file.size,
      docType: selectedCategory,
      timestamp: formatDateTime(new Date()),
      status: "processing",
      data: null,
    }));

    setQueue((prev) => [...newItems, ...prev]);
    setActiveItemId(newItems[0].id);

    // Reset input
    if (fileInputRef.current) fileInputRef.current.value = "";

    // Send each file to extraction API
    for (const item of newItems) {
      try {
        const formData = new FormData();
        formData.append("file", item.file);

        let endpoint = "invoice";
        if (item.docType === "identity") endpoint = "identity";
        if (item.docType === "insurance") endpoint = "insurance";
        if (item.docType === "license") endpoint = "license";
        if (item.docType === "contract") endpoint = "contract";

        const response = await fetch(`http://localhost:8001/extract/${endpoint}`, {
          method: "POST",
          body: formData,
        });

        if (response.ok) {
          const extractedData = await response.json();
          setQueue((prev) =>
            prev.map((q) =>
              q.id === item.id ? { ...q, status: "completed", data: extractedData } : q
            )
          );
        } else {
          setQueue((prev) =>
            prev.map((q) =>
              q.id === item.id
                ? { ...q, status: "error", errorMessage: `Error ${response.status}: ${response.statusText}` }
                : q
            )
          );
        }
      } catch (err: any) {
        console.error("API error:", err);
        setQueue((prev) =>
          prev.map((q) =>
            q.id === item.id
              ? { ...q, status: "error", errorMessage: err.message || "Error de conexión" }
              : q
          )
        );
      }
    }
  };

  const removeItem = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setQueue((prev) => {
      const filtered = prev.filter((item) => item.id !== id);
      if (activeItemId === id && filtered.length > 0) {
        setActiveItemId(filtered[0].id);
      } else if (filtered.length === 0) {
        setActiveItemId(null);
      }
      return filtered;
    });
  };

  const handleExport = async () => {
    if (!activeItem || !activeItem.data) {
      alert("No hay datos extraídos para exportar en el documento seleccionado.");
      return;
    }

    try {
      const response = await fetch("http://localhost:8001/export/invoice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify([activeItem.data]),
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `export_${activeItem.name.replace(/\.[^/.]+$/, "")}_${new Date().toISOString().split("T")[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
      } else {
        alert("El endpoint de exportación no respondió correctamente.");
      }
    } catch (error) {
      console.error("Export error:", error);
      alert("No se pudo conectar al servicio de exportación en localhost:8001.");
    }
  };

  // Preview helper
  const imageUrl = useMemo(() => {
    if (activeItem && activeItem.file.type.startsWith("image/")) {
      return URL.createObjectURL(activeItem.file);
    }
    return null;
  }, [activeItem]);

  useEffect(() => {
    return () => {
      if (imageUrl) URL.revokeObjectURL(imageUrl);
    };
  }, [imageUrl]);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-industrial-100 font-sans text-concreto-dark select-none">
      {/* ====================================================================
          HEADER INDUSTRIAL BETONDECKEN
          ==================================================================== */}
      <header className="h-[70px] bg-white border-b border-industrial-200 px-6 flex items-center justify-between shrink-0 shadow-sm z-30">
        {/* Left: Logo & Dual-row titles */}
        <div className="flex items-center gap-5">
          <div className="flex items-center">
            <Image
              src="/BETONDECKEN-logo-SEO.png"
              alt="BETONDECKEN"
              width={180}
              height={44}
              priority
              className="h-10 w-auto object-contain"
            />
          </div>

          <div className="h-9 w-px bg-industrial-200 hidden sm:block"></div>

          <div className="flex flex-col justify-center">
            <span className="font-condensed text-xl font-bold tracking-wider text-concreto-dark uppercase leading-tight">
              Procesador de documentos
            </span>
            <span className="font-sans text-xs text-concreto-light leading-tight font-normal lowercase tracking-wide">
              extracción automatizada de datos estructurados
            </span>
          </div>
        </div>

        {/* Right: Rectangular light-gray component with document types */}
        <div className="bg-industrial-100 border border-industrial-200 rounded-lg p-1 flex items-center gap-1 shadow-inner">
          {DOC_TYPES.map((type, index) => {
            const isSelected = selectedCategory === type.id;
            return (
              <React.Fragment key={type.id}>
                {index > 0 && <span className="text-industrial-300 font-light select-none">|</span>}
                <button
                  type="button"
                  onClick={() => setSelectedCategory(type.id)}
                  className={`px-3 py-1.5 rounded-md font-condensed text-xs font-bold uppercase tracking-wider transition-all duration-150 ${
                    isSelected
                      ? "bg-white text-naranja border border-industrial-200 shadow-sm"
                      : "text-concreto hover:text-concreto-dark hover:bg-industrial-200/60"
                  }`}
                >
                  {type.label}
                </button>
              </React.Fragment>
            );
          })}
        </div>
      </header>

      {/* ====================================================================
          MAIN 3-COLUMN LAYOUT: 30% | 30% | 40%
          ==================================================================== */}
      <div className="flex-1 flex overflow-hidden w-full h-[calc(100vh-70px)]">
        {/* ------------------------------------------------------------------
            COLUMNA 1: COLA DE DOCUMENTOS (30%)
            ------------------------------------------------------------------ */}
        <section className="w-[30%] min-w-[280px] flex flex-col bg-white border-r border-industrial-200 relative overflow-hidden">
          {/* Header of Column 1 */}
          <div className="h-12 border-b border-industrial-200 px-4 flex items-center justify-between bg-industrial-50/70 shrink-0">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-lg text-concreto">format_list_bulleted</span>
              <h2 className="font-condensed font-bold text-sm tracking-wider uppercase text-concreto-dark">
                Cola de documentos
              </h2>
            </div>
            <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-industrial-200 text-concreto">
              {queue.length}
            </span>
          </div>

          {/* Scrollable list of processed documents */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
            {queue.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-industrial-400">
                <span className="material-symbols-outlined text-4xl mb-2 text-industrial-300">
                  inbox
                </span>
                <p className="font-condensed text-sm font-semibold uppercase tracking-wider text-concreto">
                  Cola vacía
                </p>
                <p className="text-xs text-concreto-light mt-1">
                  Sube documentos abajo para procesarlos automáticamente.
                </p>
              </div>
            ) : (
              queue.map((item) => {
                const isActive = (activeItem?.id === item.id);
                const badge = getDocTypeBadge(item.docType);

                return (
                  <div
                    key={item.id}
                    onClick={() => setActiveItemId(item.id)}
                    className={`group relative p-3 rounded-lg border transition-all cursor-pointer ${
                      isActive
                        ? "bg-industrial-50 border-naranja shadow-sm ring-1 ring-naranja/20"
                        : "bg-white border-industrial-200 hover:border-concreto-light hover:bg-industrial-50/50"
                    }`}
                  >
                    {/* Active Accent Bar */}
                    {isActive && (
                      <div className="absolute left-0 top-2 bottom-2 w-1 bg-naranja rounded-r"></div>
                    )}

                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="font-sans text-xs font-bold text-concreto-dark truncate">
                          {item.name}
                        </p>

                        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                          <span
                            className={`font-condensed text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${badge.bg}`}
                          >
                            {badge.text}
                          </span>

                          <span className="font-mono text-[10px] text-concreto-light flex items-center gap-1">
                            <span className="material-symbols-outlined text-[12px]">schedule</span>
                            {item.timestamp}
                          </span>
                        </div>
                      </div>

                      {/* Status & Delete */}
                      <div className="flex items-center gap-1 shrink-0">
                        {item.status === "processing" && (
                          <span className="font-mono text-[10px] text-naranja flex items-center gap-1 animate-pulse font-semibold">
                            <span className="material-symbols-outlined text-xs animate-spin">sync</span>
                            Extrayendo
                          </span>
                        )}
                        {item.status === "completed" && (
                          <span className="material-symbols-outlined text-base text-emerald-600" title="Procesado">
                            check_circle
                          </span>
                        )}
                        {item.status === "error" && (
                          <span className="material-symbols-outlined text-base text-terracota" title={item.errorMessage || "Error"}>
                            error
                          </span>
                        )}

                        <button
                          type="button"
                          onClick={(e) => removeItem(item.id, e)}
                          className="opacity-0 group-hover:opacity-100 p-1 text-industrial-400 hover:text-terracota transition-opacity rounded"
                          title="Eliminar documento"
                        >
                          <span className="material-symbols-outlined text-sm">close</span>
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Fixed Upload Area at the bottom of Column 1 */}
          <div className="p-3 border-t border-industrial-200 bg-industrial-50/90 shrink-0">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              multiple
              onChange={handleFileUpload}
              className="hidden"
              id="file-upload-input"
            />
            <label
              htmlFor="file-upload-input"
              className="border-2 border-dashed border-industrial-300 hover:border-naranja bg-white hover:bg-naranja-tint/30 rounded-lg p-3 flex flex-col items-center justify-center gap-1.5 cursor-pointer transition-all group"
            >
              <div className="size-8 rounded-full bg-industrial-100 group-hover:bg-naranja group-hover:text-white flex items-center justify-center text-concreto transition-colors shadow-sm">
                <span className="material-symbols-outlined text-lg">cloud_upload</span>
              </div>
              <div className="text-center">
                <p className="font-condensed text-xs font-bold uppercase tracking-wider text-concreto-dark group-hover:text-naranja transition-colors">
                  Subir documentos
                </p>
                <p className="text-[10px] text-concreto-light">
                  PDF, JPG o PNG • Arrastra o selecciona
                </p>
              </div>
            </label>
          </div>
        </section>

        {/* ------------------------------------------------------------------
            COLUMNA 2: PREVISUALIZACIÓN DEL DOCUMENTO (30%)
            ------------------------------------------------------------------ */}
        <section className="w-[30%] min-w-[300px] flex flex-col bg-industrial-100 border-r border-industrial-200 relative overflow-hidden">
          {/* Header of Column 2 */}
          <div className="h-12 border-b border-industrial-200 px-4 flex items-center justify-between bg-white shrink-0">
            <div className="flex items-center gap-2 overflow-hidden">
              <span className="material-symbols-outlined text-lg text-concreto">visibility</span>
              <h2 className="font-condensed font-bold text-sm tracking-wider uppercase text-concreto-dark truncate">
                Previsualización
              </h2>
            </div>

            {/* Zoom Controls */}
            {activeItem && (
              <div className="flex items-center gap-1 bg-industrial-100 border border-industrial-200 rounded px-1.5 py-0.5">
                <button
                  type="button"
                  onClick={() => setZoomLevel((z) => Math.max(50, z - 10))}
                  className="text-concreto hover:text-concreto-dark p-0.5"
                  title="Alejar"
                >
                  <span className="material-symbols-outlined text-xs">remove</span>
                </button>
                <span className="font-mono text-[10px] font-semibold text-concreto px-1">
                  {zoomLevel}%
                </span>
                <button
                  type="button"
                  onClick={() => setZoomLevel((z) => Math.min(180, z + 10))}
                  className="text-concreto hover:text-concreto-dark p-0.5"
                  title="Acercar"
                >
                  <span className="material-symbols-outlined text-xs">add</span>
                </button>
              </div>
            )}
          </div>

          {/* Preview viewport */}
          <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-[#E5E8EB]/50">
            {activeItem ? (
              activeItem.file.type.startsWith("image/") ? (
                <div
                  className="relative transition-all duration-150 flex items-center justify-center"
                  style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: "top center" }}
                >
                  {imageUrl && (
                    <img
                      src={imageUrl}
                      alt={activeItem.name}
                      className="max-w-full max-h-[75vh] object-contain rounded shadow-lg border border-industrial-300 bg-white"
                    />
                  )}
                </div>
              ) : workerReady ? (
                <div
                  className="w-full flex justify-center items-start transition-all duration-150"
                  style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: "top center" }}
                >
                  <Document
                    file={activeItem.file}
                    className="shadow-xl rounded overflow-hidden border border-industrial-300"
                    loading={
                      <div className="font-condensed text-xs uppercase tracking-wider text-concreto-light p-6">
                        Cargando PDF...
                      </div>
                    }
                    error={
                      <div className="font-condensed text-xs uppercase tracking-wider text-terracota p-6">
                        Error al cargar el archivo PDF.
                      </div>
                    }
                  >
                    <Page
                      pageNumber={1}
                      width={380}
                      renderTextLayer={false}
                      renderAnnotationLayer={false}
                    />
                  </Document>
                </div>
              ) : (
                <div className="font-condensed text-xs uppercase tracking-wider text-concreto-light animate-pulse">
                  Inicializando visor de PDF...
                </div>
              )
            ) : (
              <div className="text-center p-6 text-industrial-400">
                <span className="material-symbols-outlined text-4xl mb-2 text-industrial-300">
                  find_in_page
                </span>
                <p className="font-condensed text-sm font-semibold uppercase tracking-wider text-concreto">
                  Sin documento seleccionado
                </p>
                <p className="text-xs text-concreto-light mt-1">
                  Selecciona un archivo de la cola para previsualizarlo aquí.
                </p>
              </div>
            )}
          </div>
        </section>

        {/* ------------------------------------------------------------------
            COLUMNA 3: RESULTADOS DE LA EXTRACCIÓN (40%)
            ------------------------------------------------------------------ */}
        <section className="w-[40%] flex flex-col bg-white overflow-hidden">
          {/* Header of Column 3 */}
          <div className="h-12 border-b border-industrial-200 px-5 flex items-center justify-between bg-industrial-50/70 shrink-0">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-lg text-concreto">dataset</span>
              <h2 className="font-condensed font-bold text-sm tracking-wider uppercase text-concreto-dark">
                Resultados de la extracción
              </h2>
            </div>

            <div className="flex items-center gap-2">
              {/* Form / JSON Toggle */}
              <div className="bg-industrial-200/80 p-0.5 rounded flex items-center">
                <button
                  type="button"
                  onClick={() => setViewMode("form")}
                  className={`px-2.5 py-1 rounded text-xs font-condensed font-bold uppercase tracking-wider transition-colors ${
                    viewMode === "form"
                      ? "bg-white text-concreto-dark shadow-xs"
                      : "text-concreto hover:text-concreto-dark"
                  }`}
                >
                  Formulario
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("json")}
                  className={`px-2.5 py-1 rounded text-xs font-condensed font-bold uppercase tracking-wider transition-colors ${
                    viewMode === "json"
                      ? "bg-white text-concreto-dark shadow-xs"
                      : "text-concreto hover:text-concreto-dark"
                  }`}
                >
                  JSON
                </button>
              </div>

              {/* Export button */}
              <button
                type="button"
                onClick={handleExport}
                className="px-3 py-1 bg-concreto hover:bg-concreto-dark text-white rounded font-condensed text-xs font-bold uppercase tracking-wider flex items-center gap-1 transition-colors shadow-sm"
              >
                <span className="material-symbols-outlined text-sm">download</span>
                Exportar
              </button>
            </div>
          </div>

          {/* Results body */}
          <div className="flex-1 overflow-y-auto p-6 bg-white">
            {!activeItem ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 text-industrial-400">
                <span className="material-symbols-outlined text-4xl mb-2 text-industrial-300">
                  assignment
                </span>
                <p className="font-condensed text-sm font-semibold uppercase tracking-wider text-concreto">
                  Esperando selección
                </p>
                <p className="text-xs text-concreto-light mt-1">
                  Los datos extraídos del documento se mostrarán en esta sección.
                </p>
              </div>
            ) : activeItem.status === "processing" ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8">
                <div className="size-10 rounded-full border-3 border-industrial-200 border-t-naranja animate-spin mb-4"></div>
                <p className="font-condensed text-sm font-bold uppercase tracking-wider text-concreto-dark">
                  Extrayendo datos estructurados...
                </p>
                <p className="text-xs text-concreto-light mt-1">
                  Procesando {activeItem.name} con modelos de extracción.
                </p>
              </div>
            ) : viewMode === "json" ? (
              <div className="bg-industrial-900 rounded-lg p-4 overflow-auto border border-industrial-800 shadow-inner">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-industrial-800">
                  <span className="font-mono text-[10px] text-arena uppercase font-bold">
                    Payload JSON
                  </span>
                  <span className="font-mono text-[10px] text-industrial-400">
                    {activeItem.docType}
                  </span>
                </div>
                <pre className="font-mono text-xs text-arena-light whitespace-pre-wrap leading-relaxed">
                  {activeItem.data
                    ? JSON.stringify(activeItem.data, null, 2)
                    : "// No se generó respuesta JSON"}
                </pre>
              </div>
            ) : (
              /* Structured Industrial Form View */
              <div className="space-y-6">
                {activeItem.data ? (
                  renderStructuredFields(activeItem.docType, activeItem.data)
                ) : (
                  <div className="p-6 border border-dashed border-industrial-300 rounded-lg text-center text-concreto-light text-xs">
                    No hay datos estructurados disponibles para este documento.
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

/* ==========================================================================
   RENDER STRUCTURED DATA FIELDS BY TYPE (INDUSTRIAL PALETTE)
   ========================================================================== */

function renderStructuredFields(type: SchemaType, data: any) {
  if (type === "invoice") {
    const invoice = data as InvoiceData;
    const items = Array.isArray(invoice.detalles)
      ? invoice.detalles
      : invoice.detalles
      ? [invoice.detalles]
      : [];
    const currency = Array.isArray(invoice.detalles)
      ? invoice.detalles[0]?.moneda || "PEN"
      : invoice.detalles?.moneda || "PEN";

    return (
      <div className="space-y-6">
        {/* Section: Emisor & Factura */}
        <div className="border border-industrial-200 rounded-lg p-4 bg-industrial-50/50 space-y-3">
          <div className="flex items-center justify-between border-b border-industrial-200 pb-2">
            <span className="font-condensed font-bold text-xs uppercase tracking-wider text-terracota flex items-center gap-1.5">
              <span className="material-symbols-outlined text-sm">business</span>
              Datos del Emisor y Comprobante
            </span>
            <span className="font-mono text-xs font-bold text-concreto-dark bg-white px-2 py-0.5 rounded border border-industrial-200">
              {invoice.factura?.numero_factura || "S/N"}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                RUC Emisor
              </label>
              <p className="font-mono font-bold text-concreto-dark mt-0.5">
                {invoice.emisor?.ruc || "-"}
              </p>
            </div>
            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Fecha Emisión
              </label>
              <p className="font-mono font-medium text-concreto-dark mt-0.5">
                {invoice.factura?.fecha_emision || "-"}
              </p>
            </div>
            <div className="col-span-2">
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Razón Social Emisor
              </label>
              <p className="font-sans font-semibold text-concreto-dark mt-0.5">
                {invoice.emisor?.razon_social || "-"}
              </p>
            </div>
            <div className="col-span-2">
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Dirección
              </label>
              <p className="font-sans text-concreto mt-0.5">
                {invoice.emisor?.direccion || "-"}
              </p>
            </div>
          </div>
        </div>

        {/* Section: Cliente */}
        <div className="border border-industrial-200 rounded-lg p-4 bg-industrial-50/50 space-y-3">
          <div className="border-b border-industrial-200 pb-2">
            <span className="font-condensed font-bold text-xs uppercase tracking-wider text-concreto flex items-center gap-1.5">
              <span className="material-symbols-outlined text-sm">person</span>
              Datos del Cliente
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                RUC / Doc Cliente
              </label>
              <p className="font-mono font-bold text-concreto-dark mt-0.5">
                {invoice.cliente?.ruc || "-"}
              </p>
            </div>
            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Moneda
              </label>
              <p className="font-mono font-bold text-naranja mt-0.5">
                {currency}
              </p>
            </div>
            <div className="col-span-2">
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Razón Social Cliente
              </label>
              <p className="font-sans font-semibold text-concreto-dark mt-0.5">
                {invoice.cliente?.razon_social || "-"}
              </p>
            </div>
          </div>
        </div>

        {/* Section: Line items table */}
        <div className="border border-industrial-200 rounded-lg overflow-hidden">
          <div className="bg-industrial-100 px-4 py-2 border-b border-industrial-200 flex items-center justify-between">
            <span className="font-condensed font-bold text-xs uppercase tracking-wider text-concreto flex items-center gap-1.5">
              <span className="material-symbols-outlined text-sm">receipt_long</span>
              Detalle de Productos / Servicios
            </span>
            <span className="font-mono text-[10px] text-concreto-light">
              {items.length} items
            </span>
          </div>

          <table className="w-full text-left text-xs">
            <thead className="bg-industrial-50 text-[10px] uppercase font-condensed font-bold text-concreto-light border-b border-industrial-200">
              <tr>
                <th className="px-3 py-2">Cant.</th>
                <th className="px-3 py-2">U.M.</th>
                <th className="px-3 py-2">Descripción</th>
                <th className="px-3 py-2 text-right">V. Unit.</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-industrial-200">
              {items.length > 0 ? (
                items.map((item, idx) => (
                  <tr key={idx} className="hover:bg-industrial-50/70">
                    <td className="px-3 py-2 font-mono">{item.Cantidad || "1"}</td>
                    <td className="px-3 py-2 font-mono text-concreto-light">{item["Unidad Medida"] || "UND"}</td>
                    <td className="px-3 py-2 font-medium text-concreto-dark">{item["Descripción"] || "-"}</td>
                    <td className="px-3 py-2 font-mono font-bold text-right text-concreto-dark">
                      {item["Valor Unitario"] || "-"}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-3 py-4 text-center text-concreto-light">
                    No se extrajeron ítems detallados
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (type === "identity") {
    const idData = data as IdentityDocumentData;
    return (
      <div className="space-y-6">
        <div className="border border-industrial-200 rounded-lg p-5 bg-industrial-50/50 space-y-4">
          <div className="flex items-center justify-between border-b border-industrial-200 pb-2">
            <span className="font-condensed font-bold text-xs uppercase tracking-wider text-terracota flex items-center gap-1.5">
              <span className="material-symbols-outlined text-sm">badge</span>
              Documento Nacional de Identidad
            </span>
            <span className="font-mono text-sm font-bold text-naranja bg-naranja-tint px-2.5 py-0.5 rounded border border-naranja/20">
              DNI: {idData.numero_dni || "-"}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Nombres
              </label>
              <p className="font-sans font-semibold text-concreto-dark mt-0.5 text-sm">
                {idData.nombres || "-"}
              </p>
            </div>
            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Apellidos
              </label>
              <p className="font-sans font-semibold text-concreto-dark mt-0.5 text-sm">
                {`${idData.apellido_paterno || ""} ${idData.apellido_materno || ""}`.trim() || "-"}
              </p>
            </div>

            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Fecha de Nacimiento
              </label>
              <p className="font-mono font-medium text-concreto-dark mt-0.5">
                {idData.fecha_nacimiento || "-"}
              </p>
            </div>
            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Sexo / Estado Civil
              </label>
              <p className="font-sans font-medium text-concreto-dark mt-0.5">
                {`${idData.sexo || "-"} / ${idData.estado_civil || "-"}`}
              </p>
            </div>

            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Fecha Emisión
              </label>
              <p className="font-mono text-concreto-dark mt-0.5">
                {idData.fecha_emision || "-"}
              </p>
            </div>
            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Fecha Caducidad
              </label>
              <p className="font-mono text-terracota font-bold mt-0.5">
                {idData.fecha_caducidad || "-"}
              </p>
            </div>

            <div className="col-span-2 pt-2 border-t border-industrial-200">
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Dirección / Ubicación
              </label>
              <p className="font-sans text-concreto-dark mt-0.5">
                {idData.direccion || `${idData.distrito || ""}, ${idData.provincia || ""}`.trim() || "-"}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (type === "insurance") {
    const ins = data as InsurancePolicyData;
    return (
      <div className="space-y-6">
        <div className="border border-industrial-200 rounded-lg p-5 bg-industrial-50/50 space-y-4">
          <div className="flex items-center justify-between border-b border-industrial-200 pb-2">
            <span className="font-condensed font-bold text-xs uppercase tracking-wider text-terracota flex items-center gap-1.5">
              <span className="material-symbols-outlined text-sm">shield</span>
              {ins.tipo_seguro || "Póliza de Seguro"}
            </span>
            <span className="font-mono text-xs font-bold text-concreto-dark bg-white px-2.5 py-0.5 rounded border border-industrial-200">
              N° {ins.numero_poliza || "S/N"}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Compañía Aseguradora
              </label>
              <p className="font-sans font-bold text-concreto-dark mt-0.5">
                {ins.compania_aseguradora || "-"}
              </p>
            </div>
            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Asegurado Titular
              </label>
              <p className="font-sans font-semibold text-concreto-dark mt-0.5">
                {ins.asegurado_nombre || "-"}
              </p>
            </div>

            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Documento Asegurado
              </label>
              <p className="font-mono text-concreto-dark mt-0.5">
                {ins.documento_asegurado || "-"}
              </p>
            </div>
            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Prima / Precio
              </label>
              <p className="font-mono font-bold text-naranja text-sm mt-0.5">
                {ins.precio !== undefined ? `${ins.precio}` : "-"}
              </p>
            </div>

            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Vigencia Desde
              </label>
              <p className="font-mono text-concreto-dark mt-0.5">
                {ins.fecha_inicio || "-"}
              </p>
            </div>
            <div>
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block">
                Vigencia Hasta
              </label>
              <p className="font-mono text-concreto-dark mt-0.5">
                {ins.fecha_fin || "-"}
              </p>
            </div>
          </div>

          {/* Vehicular specific */}
          {(ins.vehiculo_placa || ins.vehiculo_marca_modelo) && (
            <div className="pt-3 border-t border-industrial-200">
              <span className="font-condensed text-[11px] font-bold uppercase tracking-wider text-concreto block mb-2">
                Datos del Vehículo
              </span>
              <div className="grid grid-cols-3 gap-2 bg-white p-3 rounded border border-industrial-200 font-mono text-xs">
                <div>
                  <span className="text-[10px] text-concreto-light block">Placa:</span>
                  <span className="font-bold text-naranja">{ins.vehiculo_placa || "-"}</span>
                </div>
                <div>
                  <span className="text-[10px] text-concreto-light block">Marca / Modelo:</span>
                  <span className="font-semibold text-concreto-dark">{ins.vehiculo_marca_modelo || "-"}</span>
                </div>
                <div>
                  <span className="text-[10px] text-concreto-light block">Año:</span>
                  <span className="text-concreto-dark">{ins.vehiculo_ano || "-"}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Generic fallback for Licencias, Contratos or any generic document
  return (
    <div className="border border-industrial-200 rounded-lg p-5 bg-industrial-50/50 space-y-4">
      <div className="border-b border-industrial-200 pb-2 flex items-center justify-between">
        <span className="font-condensed font-bold text-xs uppercase tracking-wider text-concreto-dark flex items-center gap-1.5">
          <span className="material-symbols-outlined text-sm">description</span>
          Campos Extraídos ({type.toUpperCase()})
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        {Object.entries(data).map(([key, val]) => {
          if (typeof val === "object" && val !== null) return null;
          return (
            <div key={key} className="bg-white p-3 rounded border border-industrial-200">
              <label className="font-condensed text-[10px] font-bold uppercase tracking-wider text-concreto-light block truncate">
                {key.replace(/_/g, " ")}
              </label>
              <p className="font-mono font-medium text-concreto-dark mt-1 break-words">
                {String(val || "-")}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
