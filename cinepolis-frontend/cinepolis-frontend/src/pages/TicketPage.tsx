import { useLocation, useNavigate, Navigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAsientosFuncion } from "../hooks/useFuncion";
import { getDulceria } from "../api/endpoints";
import { useMemo } from "react";
import type { AsientoAPI } from "../types/api";

export function TicketPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const { ticket, carritoData, carritoFuncionId, complejoSlug } = location.state || {};

  // If no ticket, redirect home
  if (!ticket) {
    return <Navigate to="/" replace />;
  }

  // Fetch function data (for movie, room, time, seats mapping)
  const { data: mapaData } = useAsientosFuncion(carritoFuncionId);

  // Fetch dulceria data (for product mapping)
  const { data: menuData } = useQuery({
    queryKey: ["dulceria", complejoSlug],
    queryFn: () => getDulceria(complejoSlug),
    enabled: !!complejoSlug,
  });

  // Calculate seat labels
  const asientosEtiquetas = useMemo(() => {
    if (!mapaData || !carritoData) return "";
    const flatAsientos = Object.values(mapaData.mapa).flat();
    const asientosEnMapa = new Map(flatAsientos.map((a: any) => [a.asiento_id, a as AsientoAPI]));
    
    const etiquetas = carritoData.items
      .filter((i: any) => i.tipo_item === "boleto" && i.asiento_id)
      .map((i: any) => asientosEnMapa.get(i.asiento_id)?.etiqueta || `ID ${i.asiento_id}`);
    
    return etiquetas.join(", ");
  }, [mapaData, carritoData]);

  // Calculate product names
  const productosNombres = useMemo(() => {
    if (!menuData || !carritoData) return "";
    const flatProductos = menuData.menu.flatMap((c: any) => c.productos);
    const productosMap = new Map(flatProductos.map((p: any) => [p.producto_id, p]));
    
    const nombres = carritoData.items
      .filter((i: any) => i.tipo_item === "producto" && i.producto_id)
      .map((i: any) => {
        const prod = productosMap.get(i.producto_id);
        const name = prod ? prod.nombre : `Producto ${i.producto_id}`;
        return `${i.cantidad} ${name}`;
      });
      
    return nombres.join(", ");
  }, [menuData, carritoData]);

  // Format date and time
  const formatDateTime = (horario: string) => {
    if (!horario) return "";
    // horario comes in as "HH:MM:SS", we want a more readable format, 
    // but the screenshot says "7 de Noviembre, 6:40 p.m."
    // Let's use a standard format for the example
    const [h, m] = horario.split(":");
    let hour = parseInt(h, 10);
    const ampm = hour >= 12 ? "p.m." : "a.m.";
    hour = hour % 12 || 12;
    // For the date, we can just use "Hoy" since we don't have the date in mapaData easily accessible here.
    return `Hoy, ${hour}:${m} ${ampm}`;
  };

  // The code for the QR is WQ2N9W9 or similar. We can generate one based on venta_id.
  const codeStr = `WQ2N${ticket.venta_id}W9`.toUpperCase();

  return (
    <div className="min-h-screen bg-[#3B79F6] flex flex-col items-center py-10 font-sans text-white">
      {/* Top Logo */}
      <div className="mb-6">
        <svg viewBox="0 0 100 100" className="w-12 h-12 fill-white">
          <path d="M50 0C22.4 0 0 22.4 0 50s22.4 50 50 50 50-22.4 50-50S77.6 0 50 0zm0 76c-14.4 0-26-11.6-26-26s11.6-26 26-26 26 11.6 26 26-11.6 26-26 26z"/>
          <path d="M72 41c-3.1-6.1-9.4-10-16.5-10-10.2 0-18.5 8.3-18.5 18.5S45.3 68 55.5 68c7.1 0 13.4-3.9 16.5-10l-12.8-7.4c-.6 2.1-2.5 3.6-4.9 3.6-2.8 0-5.1-2.3-5.1-5.1s2.3-5.1 5.1-5.1c2.4 0 4.3 1.5 4.9 3.6L72 41z"/>
        </svg>
      </div>

      <h1 className="text-2xl font-bold mb-6 text-center max-w-sm">
        {mapaData?.pelicula || "Cargando..."}
      </h1>

      {/* QR Box */}
      <div className="bg-white text-black rounded-3xl p-6 mb-8 w-64 shadow-lg flex flex-col items-center relative">
        <div className="w-full aspect-square border-[10px] border-black p-2 flex flex-wrap gap-1 mb-4">
            {/* Simulación de un QR real */}
            {Array.from({ length: 100 }).map((_, i) => (
            <div 
                key={i} 
                className={`w-[8%] h-[8%] ${Math.random() > 0.4 ? 'bg-black' : 'bg-white'}`} 
            />
            ))}
        </div>
        <p className="text-lg tracking-[0.2em] font-medium text-gray-700">
          {codeStr}
        </p>
      </div>

      <div className="flex items-center gap-2 text-lg font-medium mb-8">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M2 5a2 2 0 012-2h12a2 2 0 012 2v2a1 1 0 01-1 1v4a1 1 0 011 1v2a2 2 0 01-2 2H4a2 2 0 01-2-2v-2a1 1 0 011-1V8a1 1 0 01-1-1V5zm3 3v4h2V8H5zm4 0v4h1V8H9zm3 0v4h2V8h-2z" clipRule="evenodd" />
        </svg>
        <span>Orden: {ticket.venta_id}</span>
      </div>

      {/* Ticket Details */}
      <div className="w-full max-w-sm px-6 flex flex-col gap-5 text-left mb-10">
        <div>
          <p className="text-white/70 text-sm mb-1">Fecha y hora de la función</p>
          <p className="font-bold text-lg">{mapaData ? formatDateTime(mapaData.horario) : "..."}</p>
        </div>
        
        <div>
          <p className="text-white/70 text-sm mb-1">Cine y sala</p>
          <p className="font-bold text-lg">{mapaData ? `${mapaData.sala.replace('Sala', '')} ${mapaData.sala}` : "..."}</p>
        </div>

        {ticket.boletos_confirmados > 0 && (
          <div>
            <p className="text-white/70 text-sm mb-1">Boletos ({ticket.boletos_confirmados})</p>
            <p className="font-bold text-lg">{ticket.boletos_confirmados} Adulto</p>
          </div>
        )}

        {asientosEtiquetas && (
          <div>
            <p className="text-white/70 text-sm mb-1">Asientos</p>
            <p className="font-bold text-lg">{asientosEtiquetas}</p>
          </div>
        )}

        {ticket.productos_confirmados > 0 && (
          <div>
            <p className="text-white/70 text-sm mb-1">Alimentos ({ticket.productos_confirmados})</p>
            <p className="font-bold text-lg truncate w-full">{productosNombres || "Cargando..."}</p>
          </div>
        )}
      </div>

      <button
        onClick={() => navigate("/")}
        className="mt-4 px-8 py-3 bg-white/20 hover:bg-white/30 text-white rounded-xl transition-colors font-bold text-sm tracking-wide"
      >
        Volver a Cartelera
      </button>
    </div>
  );
}
