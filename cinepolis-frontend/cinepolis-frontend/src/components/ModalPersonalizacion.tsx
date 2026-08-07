import { useState, useMemo } from "react";
import type { ProductoDulceria, PersonalizacionRegla } from "../types/api";

interface ModalPersonalizacionProps {
  producto: ProductoDulceria;
  onAgregar: (seleccion: { opcion_id: number; porcentaje: number; cantidad: number }[]) => void;
  onCerrar: () => void;
}

const COLORS = ["bg-yellow-400", "bg-orange-500", "bg-purple-500", "bg-green-500"];

export function ModalPersonalizacion({ producto, onAgregar, onCerrar }: ModalPersonalizacionProps) {
  // If it's a single group and the group has no explicit title in CSV, it defaults to "Personaliza tu producto"
  // For simple products like Magnum, we skip the summary step.
  const isSimple = producto.personalizacion.length <= 1;
  const [step, setStep] = useState(isSimple ? 1 : 0);
  const totalPasos = producto.personalizacion.length;
  
  // Activar sabores toggle
  const [saboresExtrasActivo, setSaboresExtrasActivo] = useState<Record<number, boolean>>({});

  const [seleccion, setSeleccion] = useState<Record<number, number[]>>(() => {
    const init: Record<number, number[]> = {};
    producto.personalizacion.forEach(paso => {
      paso.reglas.forEach(r => { init[r.regla_id] = []; });
    });
    return init;
  });

  const pasoActual = step > 0 ? producto.personalizacion[step - 1] : null;

  // Lógica Dinámica de Límite (Específico para Palomitas en Combos)
  const getDynamicLimit = (regla: PersonalizacionRegla): number => {
    // Si la regla es de sabores y estamos en Palomitas (asumimos por el max_items=4 y la existencia de tamaño)
    if (regla.limite_maximo > 1 && regla.titulo.toLowerCase().includes("sabor")) {
      // Buscar si en este mismo paso hay una regla de tamaño (max=1)
      const reglaTamaño = pasoActual?.reglas.find(r => r.limite_maximo === 1 && r.titulo.toLowerCase().includes("tama"));
      if (reglaTamaño) {
        const seleccionTamaño = seleccion[reglaTamaño.regla_id]?.[0];
        if (seleccionTamaño) {
          const opcion = reglaTamaño.opciones.find(o => o.opcion_id === seleccionTamaño);
          if (opcion?.nombre.toLowerCase().includes("jumbo")) {
            return 2;
          }
        }
      }
    }
    return regla.limite_maximo;
  };

  const toggleOpcion = (regla: PersonalizacionRegla, opcionId: number) => {
    const limit = getDynamicLimit(regla);
    
    setSeleccion(prev => {
      const current = prev[regla.regla_id] ?? [];
      
      // Regla exclusiva (Radio)
      if (limit === 1) {
        // Al cambiar de tamaño, si el nuevo límite de sabores es menor a la cantidad seleccionada, reseteamos sabores
        const newSelection = { ...prev, [regla.regla_id]: current[0] === opcionId ? [] : [opcionId] };
        
        if (regla.titulo.toLowerCase().includes("tama")) {
            const reglaSabor = pasoActual?.reglas.find(r => r.limite_maximo > 1 && r.titulo.toLowerCase().includes("sabor"));
            if (reglaSabor) {
                const isJumbo = regla.opciones.find(o => o.opcion_id === opcionId)?.nombre.toLowerCase().includes("jumbo");
                if (isJumbo) {
                    // Si se seleccionó jumbo, recortar sabores a max 2 si hay más
                    if ((newSelection[reglaSabor.regla_id] || []).length > 2) {
                        newSelection[reglaSabor.regla_id] = newSelection[reglaSabor.regla_id].slice(0, 2);
                    }
                }
            }
        }
        return newSelection;
      }
      
      // Múltiples opciones (Checkbox)
      if (current.includes(opcionId)) {
        return { ...prev, [regla.regla_id]: current.filter(id => id !== opcionId) };
      }
      if (current.length >= limit) return prev;
      return { ...prev, [regla.regla_id]: [...current, opcionId] };
    });
  };

  const pasoValido = () => {
    if (step === 0) return true;
    return pasoActual!.reglas.every(regla => {
      // Si es la regla de sabores extras y el toggle no está activo, no es obligatoria
      if (regla.limite_maximo > 1 && regla.titulo.toLowerCase().includes("sabor") && !saboresExtrasActivo[step]) {
          return true; // Se asume sabor tradicional
      }
      const count = (seleccion[regla.regla_id] ?? []).length;
      return count >= regla.limite_minimo;
    });
  };

  const handleSiguiente = () => {
    if (step < totalPasos) {
      setStep(step + 1);
    } else {
      // Confirmar
      const personalizaciones: { opcion_id: number; porcentaje: number; cantidad: number }[] = [];
      producto.personalizacion.forEach(paso => {
        paso.reglas.forEach(regla => {
          const ids = seleccion[regla.regla_id] ?? [];
          const numSabores = ids.length;
          ids.forEach(opcionId => {
            // Lógica de porcentajes: si hay 1->100, 2->50/50, 3->50/25/25, 4->25/25/25/25
            let pct = 0;
            if (regla.limite_maximo > 1) {
                if (numSabores === 1) pct = 100;
                else if (numSabores === 2) pct = 50;
                else if (numSabores === 3) {
                    pct = ids.indexOf(opcionId) === 0 ? 50 : 25;
                } else if (numSabores === 4) pct = 25;
            }
            personalizaciones.push({
              opcion_id: opcionId,
              porcentaje: pct,
              cantidad: 1,
            });
          });
        });
      });
      onAgregar(personalizaciones);
    }
  };

  const precioTotal = useMemo(() => {
    let basePrice = producto.precio;
    let additions = 0;

    producto.personalizacion.forEach(paso => {
      paso.reglas.forEach(regla => {
        const selectedOpts = (seleccion[regla.regla_id] ?? [])
          .map(id => regla.opciones.find(o => o.opcion_id === id))
          .filter(Boolean);

        // SOLO sumar el precio_extra. Ya no usamos Math.max porque rompía el flujo de combos.
        selectedOpts.forEach(o => { 
            // Ignoramos los precios base que están mapeados como precio extra enorme.
            // Si el precio extra es mayor o igual al precio del combo, es un error de mapeo del CSV de Cinépolis.
            // Para el clon, asumimos que si el precio extra >= precio combo, en realidad es 0 (precio base).
            let extra = o!.precio_extra;
            if (extra >= producto.precio) {
                // Solo para el Magnum moonlight/etc donde la variante costaba casi igual al producto base
                if (isSimple && extra > 0) {
                    // Si es un producto simple (Magnum), el precio extra SÍ reemplaza el precio base si es mayor
                    if (extra > basePrice) basePrice = extra;
                    extra = 0; 
                } else {
                    extra = 0;
                }
            }
            additions += extra; 
        });
      });
    });
    return basePrice + additions;
  }, [seleccion, producto, isSimple]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4 pt-10 pb-4">
      <button 
        onClick={onCerrar} 
        className="absolute top-4 right-4 bg-white/20 hover:bg-white/40 text-white rounded-full px-4 py-2 font-bold text-sm backdrop-blur-md transition-colors flex items-center gap-2 z-[60]"
      >
        Cerrar <span className="text-lg">×</span>
      </button>

      <div className="bg-white rounded-[32px] w-full max-w-5xl shadow-2xl overflow-hidden flex flex-col h-full max-h-[90vh] relative animate-in zoom-in-95 duration-200">
        
        {/* Cabecera / Imagen */}
        {step === 0 ? (
          // Paso 0: Resumen (Estilo Cinépolis Original)
          <div className="flex-1 overflow-y-auto">
             <div className="w-full h-80 bg-[#16213e] relative">
               {producto.imagen_url && (
                  <img src={producto.imagen_url} alt={producto.nombre} className="w-full h-full object-cover opacity-60 mix-blend-screen blur-xl scale-125" />
               )}
               <div className="absolute inset-0 flex flex-col items-center justify-center pt-8">
                  <h2 className="text-4xl font-black text-white mb-6 tracking-wide drop-shadow-lg">{producto.nombre.toUpperCase()}</h2>
                  {producto.imagen_url && (
                    <img src={producto.imagen_url} alt={producto.nombre} className="h-56 object-contain drop-shadow-2xl hover:scale-105 transition-transform" />
                  )}
               </div>
             </div>
             <div className="max-w-2xl mx-auto px-6 py-12 text-center">
                <p className="text-gray-500 text-base leading-relaxed mb-10">{producto.descripcion}</p>
                
                <div className="space-y-6 text-left border border-gray-100 rounded-2xl p-8 bg-gray-50/50">
                    <h3 className="font-bold text-gray-800 text-lg border-b pb-4 mb-4">¿Qué incluye tu combo?</h3>
                    {producto.personalizacion.map((paso, idx) => (
                        <div key={idx} className="flex justify-between items-center text-sm">
                            <span className="font-semibold text-gray-700">{paso.grupo_titulo.replace("Selecciona el sabor de", "").trim().toUpperCase()}</span>
                            <span className="text-[#3e7af0] font-bold">{paso.grupo_titulo}</span>
                        </div>
                    ))}
                </div>
             </div>
          </div>
        ) : (
          // Pasos de personalización
          <div className="flex-1 overflow-y-auto pb-32">
             <div className="w-full text-center py-8 bg-white border-b sticky top-0 z-10">
                <p className="text-xs text-gray-400 uppercase font-bold tracking-widest mb-1">{producto.nombre}</p>
                <h2 className="text-3xl font-display text-[#0b162c]">{pasoActual?.grupo_titulo}</h2>
             </div>
             
             <div className="max-w-4xl mx-auto px-6 py-8 space-y-12">
                {pasoActual?.reglas.map(regla => {
                    const isFlavor = regla.limite_maximo > 1 && regla.titulo.toLowerCase().includes("sabor");
                    const limit = getDynamicLimit(regla);
                    const isToggleActive = saboresExtrasActivo[step];

                    return (
                        <div key={regla.regla_id}>
                            <div className="flex items-center gap-4 mb-6">
                                <div className="h-px bg-gray-300 flex-1"></div>
                                <h3 className="font-bold text-gray-500 text-xs uppercase tracking-wider">{regla.titulo}</h3>
                                <div className="h-px bg-gray-300 flex-1"></div>
                            </div>
                            
                            {isFlavor && (
                                <div className="mb-6 bg-gray-50 rounded-xl p-4 border border-gray-100">
                                    <div className="flex justify-between items-center mb-4">
                                        <div>
                                            <h4 className="font-bold text-sm text-gray-800">Personaliza el sabor de tus productos desde: $25.00</h4>
                                            <p className="text-xs text-gray-500 mt-1">Puedes elegir hasta {limit}</p>
                                        </div>
                                        <button 
                                            onClick={() => {
                                                setSaboresExtrasActivo(p => ({...p, [step]: !p[step]}));
                                                if(saboresExtrasActivo[step]) {
                                                    // Si se desactiva, limpiamos selección
                                                    setSeleccion(prev => ({...prev, [regla.regla_id]: []}));
                                                }
                                            }}
                                            className={`w-12 h-6 rounded-full transition-colors flex items-center px-1 ${isToggleActive ? 'bg-[#3e7af0]' : 'bg-gray-300'}`}
                                        >
                                            <div className={`w-4 h-4 bg-white rounded-full transition-transform ${isToggleActive ? 'translate-x-6' : ''}`}></div>
                                        </button>
                                    </div>
                                    
                                    {/* Barra de colores */}
                                    {isToggleActive && (seleccion[regla.regla_id] ?? []).length > 0 && (
                                        <div className="w-full h-8 flex rounded-md overflow-hidden mb-4">
                                            {(seleccion[regla.regla_id] ?? []).map((id, idx, arr) => {
                                                let w = "w-full";
                                                let pct = "100%";
                                                if (arr.length === 2) { w = "w-1/2"; pct = "50%"; }
                                                if (arr.length === 3) { w = idx === 0 ? "w-1/2" : "w-1/4"; pct = idx===0 ? "50%" : "25%"; }
                                                if (arr.length === 4) { w = "w-1/4"; pct = "25%"; }
                                                
                                                return (
                                                    <div key={id} className={`h-full ${COLORS[idx]} flex items-center justify-center ${w} transition-all`}>
                                                        <span className="text-white text-[10px] font-bold">{pct}</span>
                                                    </div>
                                                )
                                            })}
                                        </div>
                                    )}
                                </div>
                            )}

                            {(!isFlavor || isToggleActive) && (
                                <div className="flex flex-wrap gap-4 justify-center">
                                {regla.opciones.map(opcion => {
                                    const isSelected = (seleccion[regla.regla_id] ?? []).includes(opcion.opcion_id);
                                    const selectIndex = (seleccion[regla.regla_id] ?? []).indexOf(opcion.opcion_id);
                                    
                                    // Corregir display de precio
                                    let priceText = "";
                                    let extra = opcion.precio_extra;
                                    if (extra >= producto.precio) extra = 0; // Error de mapeo CSV
                                    
                                    if (regla.limite_maximo === 1) {
                                        // Tamaños (muestran el precio base del componente + extra, o al menos el extra, el CSV dice ej. $116)
                                        priceText = `$${extra.toFixed(2)}`;
                                    } else {
                                        // Sabores (muestran +$25.00)
                                        if (extra > 0) priceText = `+ $${extra.toFixed(2)}`;
                                    }
                                    
                                    // Hack para ocultar el 0.00 de mantequilla que dice el usuario
                                    if (extra === 0 && isFlavor) priceText = "";

                                    return (
                                    <button
                                        key={opcion.opcion_id}
                                        onClick={() => toggleOpcion(regla, opcion.opcion_id)}
                                        className={`relative w-28 h-36 rounded-xl border-2 flex flex-col items-center justify-center p-2 transition-all ${
                                        isSelected
                                            ? "border-[#3e7af0] bg-[#3e7af0]/5 shadow-sm"
                                            : "border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm"
                                        }`}
                                    >
                                        {isSelected && (
                                        <div className={`absolute -top-2 -right-2 text-white w-6 h-6 rounded-md flex items-center justify-center shadow-md ${isFlavor ? COLORS[selectIndex] : 'bg-[#3e7af0]'}`}>
                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                            </svg>
                                        </div>
                                        )}
                                        
                                        <div className="w-16 h-16 mb-2 flex items-center justify-center overflow-hidden rounded-lg">
                                        {opcion.imagen_url ? (
                                            <img
                                            src={opcion.imagen_url}
                                            alt={opcion.nombre}
                                            className="w-full h-full object-contain mix-blend-multiply"
                                            onError={(e) => {
                                                (e.target as HTMLImageElement).style.display = "none";
                                                (e.target as HTMLImageElement).nextElementSibling?.classList.remove("hidden");
                                            }}
                                            />
                                        ) : null}
                                        <svg viewBox="0 0 24 24" fill="currentColor" className={`w-10 h-10 text-gray-300 ${opcion.imagen_url ? "hidden" : ""}`}>
                                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" />
                                        </svg>
                                        </div>
                                        
                                        <span className="text-[11px] font-bold text-gray-800 text-center leading-tight mb-1">{opcion.nombre}</span>
                                        <span className="text-[10px] text-gray-500 font-mono">{priceText}</span>
                                    </button>
                                    );
                                })}
                                </div>
                            )}
                        </div>
                    );
                })}
             </div>
          </div>
        )}

        {/* Footer Fixed Bar */}
        <div className="absolute bottom-0 left-0 right-0 bg-white border-t border-gray-200 px-6 sm:px-10 py-5 flex items-center justify-between shadow-[0_-10px_20px_-10px_rgba(0,0,0,0.1)]">
          <div className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-2">
            <span className="font-display text-3xl font-black text-[#0b162c]">${precioTotal.toFixed(2)}<span className="text-xl text-gray-400 font-sans">*</span></span>
            <span className="text-gray-400 text-[10px]">*El precio puede variar según tu personalización.</span>
          </div>
          
          <div className="flex flex-col items-center">
              {step > 0 && <span className="text-xs text-gray-400 font-bold mb-1">Paso {step} de {totalPasos}</span>}
              <button
                onClick={handleSiguiente}
                disabled={!pasoValido()}
                className="bg-[#417df7] hover:bg-[#3263c9] disabled:opacity-50 disabled:cursor-not-allowed transition-colors rounded-xl px-12 py-3 font-bold text-white text-sm shadow-md"
              >
                {step === 0 ? "Personalizar" : (step === totalPasos ? "Agregar al Carrito" : "Siguiente")}
              </button>
          </div>
        </div>
      </div>
    </div>
  );
}
