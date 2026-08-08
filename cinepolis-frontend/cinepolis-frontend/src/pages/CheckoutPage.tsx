import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getCarrito, pagarCarrito, getDulceria } from "../api/endpoints";
import { useAppStore } from "../store/useAppStore";
import { useAsientosFuncion, usePreciosFuncion } from "../hooks/useFuncion";

function formatFecha(fechaStr?: string): string {
  if (!fechaStr) return "";
  const MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio",
                 "Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
  const [, m, d] = fechaStr.split("-");
  return `${parseInt(d)} de ${MESES[parseInt(m) - 1]}`;
}
function formatHora(horario?: string): string {
  if (!horario) return "";
  const [h, min] = horario.split(":");
  let hour = parseInt(h, 10);
  const ampm = hour >= 12 ? "p.m." : "a.m.";
  hour = hour % 12 || 12;
  return `${hour}:${min} ${ampm}`;
}

export function CheckoutPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const carritoId = useAppStore((s) => s.carritoId);
  const setCarritoId = useAppStore((s) => s.setCarritoId);
  const complejoSlug = useAppStore((s) => s.complejoSlug);
  const carritoFuncionId = useAppStore((s) => s.carritoFuncionId);

  const [nombre, setNombre] = useState("");
  const [apellidos, setApellidos] = useState("");
  const [correo, setCorreo] = useState("");
  
  // Payment state (dummy)
  const [tarjeta, setTarjeta] = useState("");
  const [expiracion, setExpiracion] = useState("");
  const [cvv, setCvv] = useState("");

  const { data: carritoData, isLoading: isLoadingCarrito } = useQuery({
    queryKey: ["carrito", carritoId],
    queryFn: () => getCarrito(carritoId!),
    enabled: !!carritoId,
    retry: false,
  });

  const { data: mapaData } = useAsientosFuncion(carritoFuncionId || 0);
  const { data: preciosData } = usePreciosFuncion(carritoFuncionId || 0);
  const { data: menuData } = useQuery({
    queryKey: ["dulceria", complejoSlug],
    queryFn: () => getDulceria(complejoSlug),
    enabled: !!complejoSlug,
  });

  const mutPagar = useMutation({
    mutationFn: async () => {
      if (!carritoId) throw new Error("No hay carrito activo");
      return pagarCarrito(carritoId, {
        forma_pago: "Tarjeta",
        nombre_comprador: nombre,
        apellido_comprador: apellidos,
        correo_comprador: correo,
      });
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["carrito"] });
      const stateToPass = { 
        ticket: data, 
        carritoData, 
        carritoFuncionId,
        complejoSlug
      };
      setCarritoId(null);
      navigate("/ticket", { state: stateToPass });
    },
    onError: (e: Error) => {
      alert("Error procesando pago: " + e.message);
    },
  });

  // Derived data
  const boletos = useMemo(() => {
    if (!carritoData || !mapaData || !preciosData) return [];
    const flatAsientos = Object.values(mapaData.mapa).flat();
    const asientosEnMapa = new Map(flatAsientos.map((a: any) => [a.asiento_id, a]));
    
    return carritoData.items
      .filter((i: any) => i.tipo_item === "boleto")
      .map((i: any) => {
        const asiento = asientosEnMapa.get(i.asiento_id);
        const tarifa = preciosData.tarifas.find(t => t.tipo_boleto_id === i.tipo_boleto_id);
        return {
          ...i,
          etiqueta: asiento ? asiento.etiqueta : `Asiento ${i.asiento_id}`,
          tipoNombre: tarifa ? tarifa.tipo_boleto : "Boleto",
        };
      });
  }, [carritoData, mapaData, preciosData]);

  const dulceria = useMemo(() => {
    if (!carritoData || !menuData || !menuData.menu) return [];
    const flatProductos = menuData.menu.flatMap((c: any) => c.productos);
    const productosMap = new Map(flatProductos.map((p: any) => [p.producto_id, p]));
    
    return carritoData.items
      .filter((i: any) => i.tipo_item === "producto")
      .map((i: any) => {
        const prod = productosMap.get(i.producto_id);
        return {
          ...i,
          nombre: prod ? prod.nombre : `Producto ${i.producto_id}`,
          imagen_url: prod?.imagen_url,
        };
      });
  }, [carritoData, menuData]);

  if (!carritoId) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center text-cine-slate">
        <p className="font-display text-2xl mb-4">No tienes un carrito activo.</p>
        <button onClick={() => navigate("/")} className="text-cine-gold hover:underline">
          Volver a cartelera
        </button>
      </div>
    );
  }

  if (isLoadingCarrito) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-cine-slate font-mono animate-pulse">Cargando carrito…</p>
      </div>
    );
  }
  
  const subtotal = carritoData?.subtotal || 0;
  const numBoletos = boletos.reduce((acc, b) => acc + b.cantidad, 0);
  const cargoServicio = numBoletos * 6.0;
  const totalPagado = subtotal + cargoServicio;

  const isFormValid = nombre.trim() && apellidos.trim() && correo.trim() && tarjeta.trim() && expiracion.trim() && cvv.trim();
  const posterFallback = mapaData ? `https://placehold.co/60x80/1a1d2e/c8a96a?text=${encodeURIComponent(mapaData.pelicula.slice(0, 2))}` : "";

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 grid lg:grid-cols-[1fr_380px] gap-8 items-start">
      {/* ── LEFT PANEL: Formulario de Pago ── */}
      <div>
        <button
          onClick={() => navigate(-1)}
          className="text-cine-slate text-sm mb-4 hover:text-cine-gold transition-colors font-mono"
        >
          ← Volver a dulcería
        </button>
        <h1 className="font-display text-4xl tracking-wide leading-none mb-8">Pago y Contacto</h1>

        <div className="bg-cine-bg-raised border border-cine-line rounded-xl p-6 mb-8">
          <h2 className="text-xl font-display mb-4 text-cine-cream">Tus Datos</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs uppercase text-cine-slate mb-1">Nombre</label>
              <input
                type="text"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                className="w-full bg-cine-bg border border-cine-line rounded-md px-3 py-2 text-sm text-cine-cream outline-none focus:border-cine-gold transition-colors"
                placeholder="Ej. Luis"
              />
            </div>
            <div>
              <label className="block text-xs uppercase text-cine-slate mb-1">Apellidos</label>
              <input
                type="text"
                value={apellidos}
                onChange={(e) => setApellidos(e.target.value)}
                className="w-full bg-cine-bg border border-cine-line rounded-md px-3 py-2 text-sm text-cine-cream outline-none focus:border-cine-gold transition-colors"
                placeholder="Ej. Pérez"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-xs uppercase text-cine-slate mb-1">Correo Electrónico</label>
              <input
                type="email"
                value={correo}
                onChange={(e) => setCorreo(e.target.value)}
                className="w-full bg-cine-bg border border-cine-line rounded-md px-3 py-2 text-sm text-cine-cream outline-none focus:border-cine-gold transition-colors"
                placeholder="tu@correo.com"
              />
            </div>
          </div>
        </div>

        <div className="bg-cine-bg-raised border border-cine-line rounded-xl p-6 relative overflow-hidden">
          {/* Decorative element */}
          <div className="absolute top-0 right-0 w-32 h-32 bg-cine-gold/5 rounded-full -translate-y-1/2 translate-x-1/4 blur-2xl pointer-events-none"></div>
          
          <h2 className="text-xl font-display mb-4 text-cine-cream">Método de Pago</h2>
          <div className="space-y-4 relative z-10">
            <div>
              <label className="block text-xs uppercase text-cine-slate mb-1">Número de Tarjeta</label>
              <input
                type="text"
                value={tarjeta}
                onChange={(e) => setTarjeta(e.target.value)}
                className="w-full bg-cine-bg border border-cine-line rounded-md px-3 py-2 text-sm text-cine-cream outline-none focus:border-cine-gold transition-colors font-mono tracking-widest"
                placeholder="0000 0000 0000 0000"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs uppercase text-cine-slate mb-1">Expiración</label>
                <input
                  type="text"
                  value={expiracion}
                  onChange={(e) => setExpiracion(e.target.value)}
                  className="w-full bg-cine-bg border border-cine-line rounded-md px-3 py-2 text-sm text-cine-cream outline-none focus:border-cine-gold transition-colors font-mono tracking-widest"
                  placeholder="MM/YY"
                />
              </div>
              <div>
                <label className="block text-xs uppercase text-cine-slate mb-1">CVV</label>
                <input
                  type="text"
                  value={cvv}
                  onChange={(e) => setCvv(e.target.value)}
                  className="w-full bg-cine-bg border border-cine-line rounded-md px-3 py-2 text-sm text-cine-cream outline-none focus:border-cine-gold transition-colors font-mono tracking-widest"
                  placeholder="123"
                  maxLength={4}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── RIGHT PANEL: "Tu pedido" sidebar ── */}
      <aside className="lg:sticky lg:top-8 h-fit">
        <div className="bg-cine-bg-raised border border-cine-line rounded-xl overflow-hidden shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-[#0a182b] border-b border-cine-line">
            <span className="text-sm font-bold text-white tracking-wide">Tu pedido</span>
            <span className="font-display text-lg text-white">${totalPagado.toFixed(2)}</span>
          </div>

          {/* Movie info */}
          {mapaData && (
            <>
              <div className="p-4 border-b border-cine-line flex gap-3 bg-cine-bg">
                <img
                  src={mapaData.poster_url || posterFallback}
                  alt={mapaData.pelicula}
                  className="w-14 h-20 object-cover rounded-md flex-shrink-0 border border-cine-line"
                  onError={(e) => { (e.target as HTMLImageElement).src = posterFallback; }}
                />
                <div className="min-w-0">
                  <p className="font-bold text-cine-cream text-sm leading-tight mb-2 line-clamp-2">{mapaData.pelicula}</p>
                  <div className="flex items-center gap-2 flex-wrap">
                    {mapaData.clasificacion && (
                      <span className="text-[10px] font-bold border border-[#009c4a] text-[#009c4a] bg-[#009c4a]/10 px-1.5 py-0.5 rounded">
                        {mapaData.clasificacion}
                      </span>
                    )}
                    {mapaData.duracion_min && (
                      <span className="text-[10px] text-cine-slate font-mono bg-cine-bg-raised px-1.5 py-0.5 rounded border border-cine-line">
                        {mapaData.duracion_min} min
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Function details */}
              <div className="px-4 py-3 border-b border-cine-line space-y-2 bg-cine-bg">
                <div className="flex justify-between text-xs">
                  <span className="text-cine-slate">Cine</span>
                  <span className="text-cine-cream-dim font-medium capitalize text-right">{complejoSlug.replace(/-/g, " ")}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-cine-slate">Fecha y hora</span>
                  <span className="text-cine-cream-dim font-medium text-right">
                    {formatFecha(mapaData.fecha_funcion)} a las {formatHora(mapaData.horario)}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-cine-slate">Sala</span>
                  <span className="text-cine-cream-dim font-medium font-display text-sm">{mapaData.sala.replace("Sala ", "")}</span>
                </div>
              </div>
            </>
          )}

          {/* Seats section */}
          <div className="px-4 py-3 border-b border-cine-line">
            <p className="text-[10px] text-cine-slate uppercase font-bold tracking-widest mb-3">
              Asientos ({numBoletos})
            </p>
            {boletos.length === 0 ? (
              <p className="text-xs text-cine-slate italic">Sin boletos</p>
            ) : (
              <div className="space-y-4">
                {boletos.map((b, idx) => (
                  <div key={b.detalle_carrito_id || idx} className="border-b border-cine-line/50 pb-3 last:border-0 last:pb-0">
                    <div className="flex items-center gap-2 text-sm font-bold text-cine-cream mb-1">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-cine-slate" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                      </svg>
                      {b.tipoNombre}
                    </div>
                    <div className="flex justify-between items-end">
                      <p className="text-[10px] text-cine-slate font-mono ml-6">
                        {b.etiqueta} &middot; {b.cantidad} persona{b.cantidad > 1 ? "s" : ""}
                      </p>
                      <span className="text-cine-gold font-mono text-xs">${(Number(b.precio_unitario) * b.cantidad).toFixed(2)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Alimentos section */}
          <div className="px-4 py-3 border-b border-cine-line">
            <p className="text-[10px] text-cine-slate uppercase font-bold tracking-widest mb-3">
              Alimentos ({dulceria.length})
            </p>
            {dulceria.length === 0 ? (
              <div className="flex items-center gap-2 text-cine-slate text-xs py-2 bg-cine-bg rounded-lg px-3">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 opacity-50 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 2a8 8 0 100 16A8 8 0 0010 2zm1 5a1 1 0 10-2 0v4a1 1 0 102 0V7zm-1 8a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" clipRule="evenodd" />
                </svg>
                <span>No has agregado alimentos a tu orden</span>
              </div>
            ) : (
              <div className="space-y-3">
                {dulceria.map((d, idx) => (
                  <div key={d.detalle_carrito_id || idx} className="flex gap-3">
                    {d.imagen_url ? (
                      <img src={d.imagen_url} alt={d.nombre} className="w-10 h-10 object-cover rounded bg-cine-bg border border-cine-line" />
                    ) : (
                      <div className="w-10 h-10 rounded bg-cine-bg border border-cine-line flex items-center justify-center flex-shrink-0">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-cine-slate opacity-50" viewBox="0 0 20 20" fill="currentColor">
                          <path d="M4 3a2 2 0 100 4h12a2 2 0 100-4H4z" />
                          <path fillRule="evenodd" d="M3 8h14v7a2 2 0 01-2 2H5a2 2 0 01-2-2V8zm5 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" clipRule="evenodd" />
                        </svg>
                      </div>
                    )}
                    <div className="flex-1 min-w-0 flex flex-col justify-center">
                      <p className="text-xs text-cine-cream font-medium line-clamp-1">{d.nombre}</p>
                      <div className="flex justify-between items-center mt-1">
                        <span className="text-[10px] text-cine-slate font-mono">{d.cantidad}x</span>
                        <span className="text-cine-gold font-mono text-xs">${(Number(d.precio_unitario) * d.cantidad).toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Totals */}
          <div className="px-4 py-3 bg-cine-bg">
            <div className="space-y-1.5 mb-3">
              <div className="flex justify-between text-sm text-cine-slate">
                <span>Subtotal</span>
                <span className="font-mono text-cine-cream-dim">${subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm text-cine-slate">
                <span>Cargo por servicio</span>
                <span className="font-mono text-cine-cream-dim">${cargoServicio.toFixed(2)}</span>
              </div>
            </div>
            <div className="flex justify-between text-base font-bold text-cine-cream pt-2 border-t border-cine-line/50">
              <span className="uppercase tracking-wide">Total</span>
              <span className="text-cine-gold font-display text-2xl">${totalPagado.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="mt-4">
          <button
            onClick={() => mutPagar.mutate()}
            disabled={!isFormValid || mutPagar.isPending}
            className="w-full bg-[#e31837] hover:bg-[#c41530] disabled:opacity-40 disabled:cursor-not-allowed transition-colors rounded-xl py-4 font-body font-bold tracking-wide text-white text-sm shadow-md"
          >
            {mutPagar.isPending ? "Procesando..." : `Pagar $${totalPagado.toFixed(2)}`}
          </button>
          <p className="text-center text-[10px] text-cine-slate mt-2 uppercase tracking-widest">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 inline-block mr-1 -mt-0.5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
            </svg>
            Pago 100% seguro
          </p>
        </div>
      </aside>
    </div>
  );
}
