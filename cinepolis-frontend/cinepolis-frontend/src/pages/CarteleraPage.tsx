import { useState, useEffect } from "react";
import { SelectorFecha, toISODate } from "../components/SelectorFecha";
import { PeliculaCard } from "../components/PeliculaCard";
import { useCartelera, useFechasCartelera } from "../hooks/useCartelera";
import { useAppStore } from "../store/useAppStore";
 
// Los 19 slugs confirmados en Vision (complejo_id 1-19). Si tu base
// existente solo tiene funciones sembradas para algunos, verás "sin
// funciones" en los demás hasta que se pueble el resto.
const COMPLEJOS = [
  { slug: "cinepolis-la-florida-acayucan", nombre: "La Florida (Acayucan)" },
  { slug: "cinepolis-vip-el-dorado-veracruz", nombre: "VIP El Dorado Veracruz" },
  { slug: "cinepolis-las-americas-veracruz", nombre: "Las Américas Veracruz" },
  { slug: "cinepolis-vip-las-americas-veracruz", nombre: "VIP Las Américas Veracruz" },
  { slug: "cinepolis-el-dorado-coatzacoalcos", nombre: "Dorado Coatzacoalcos" },
  { slug: "cinepolis-acaya-coatzacoalcos", nombre: "Acaya Coatzacoalcos" },
  { slug: "cinepolis-plaza-shangri-la-cordoba", nombre: "Plaza Shangri-La" },
  { slug: "cinepolis-plaza-museo-xalapa", nombre: "Plaza Museo (Xalapa)" },
  { slug: "cinepolis-plaza-crystal-xalapa", nombre: "Plaza Cristal (Xalapa)" },
  { slug: "cinepolis-vip-las-americas-xalapa", nombre: "VIP Xalapa" },
  { slug: "cinepolis-plaza-las-americas-xalapa", nombre: "Xalapa Las Américas" },
  { slug: "cinepolis-chedraui-martinez-de-la-torre", nombre: "Martínez de la Torre" },
  { slug: "cinepolis-plaza-minatitlan", nombre: "Minatitlán" },
  { slug: "cinepolis-plaza-valle-orizaba", nombre: "Valle Orizaba" },
  { slug: "cinepolis-rio-blanco-orizaba", nombre: "Río Blanco" },
  { slug: "cinepolis-plaza-crystal-tuxpan", nombre: "Tuxpan" },
  { slug: "cinepolis-portal-veracruz", nombre: "Portal Veracruz" },
  { slug: "cinepolis-plaza-del-puerto-veracruz", nombre: "Plaza del Puerto" },
  { slug: "cinepolis-el-dorado-veracruz", nombre: "El Dorado Veracruz" }
];
 
export function CarteleraPage() {
  const [fecha, setFecha] = useState(toISODate(new Date()));
  const complejoSlug = useAppStore((s) => s.complejoSlug);
  const setComplejoSlug = useAppStore((s) => s.setComplejoSlug);
  const { data: fechas, isLoading: isFechasLoading } = useFechasCartelera(complejoSlug);
  
  // If we get a new list of dates and the current selected date is not in it, select the first available date.
  // We use useEffect to sync the state when `fechas` changes.
  useEffect(() => {
    if (fechas && fechas.length > 0 && !fechas.includes(fecha)) {
      setFecha(fechas[0]);
    }
  }, [fechas, fecha]);

  const { data, isLoading, isError, error } = useCartelera(complejoSlug, fecha);
 
  // Filtrar las películas y funciones basándonos en la hora actual
  const now = new Date();
  const [y, m, d] = fecha.split("-").map(Number);
  
  const peliculasActivas = data?.peliculas.map(p => {
    const funcionesActivas = p.funciones.filter((f) => {
      const [h, min] = f.hora_inicio.split(":").map(Number);
      const functionTime = new Date(y, m - 1, d, h, min);
      const hideTime = new Date(functionTime.getTime() + 15 * 60000);
      return hideTime >= now;
    });
    return { ...p, funciones: funcionesActivas };
  }).filter(p => p.funciones.length > 0) || [];

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <header className="mb-6">
        <p className="text-cine-gold text-xs uppercase tracking-[0.2em] font-semibold mb-1">
          Cartelera
        </p>
        <h1 className="font-display text-5xl sm:text-6xl leading-none tracking-wide">
          ¿Qué se proyecta hoy?
        </h1>
 
        <select
          value={complejoSlug}
          onChange={(e) => setComplejoSlug(e.target.value)}
          className="mt-3 bg-cine-bg-raised border border-cine-line rounded-md px-3 py-1.5 text-sm text-cine-cream-dim focus:border-cine-gold outline-none"
        >
          {COMPLEJOS.map((c) => (
            <option key={c.slug} value={c.slug}>
              {c.nombre}
            </option>
          ))}
        </select>
      </header>
 
      {fechas && fechas.length > 0 ? (
        <SelectorFecha 
          fechaSeleccionada={fecha} 
          fechasDisponibles={fechas} 
          onSelect={setFecha} 
        />
      ) : (
        isFechasLoading && <div className="h-14 animate-pulse bg-cine-bg-raised rounded-lg border border-cine-line"></div>
      )}
 
      <div className="mt-6 space-y-4">
        {isLoading && (
          <p className="text-cine-slate font-mono text-sm">Cargando funciones…</p>
        )}
 
        {isError && (
          <div className="border border-cine-crimson rounded-lg p-4 text-sm">
            <p className="text-cine-crimson font-semibold mb-1">
              No se pudo cargar la cartelera.
            </p>
            <p className="text-cine-slate">{(error as Error).message}</p>
          </div>
        )}
 
        {data && !isLoading && peliculasActivas.length === 0 && (
          <div className="border border-dashed border-cine-line rounded-lg p-8 text-center">
            <p className="text-cine-cream-dim">
              No hay funciones programadas para esta fecha en este complejo.
            </p>
          </div>
        )}
 
        {peliculasActivas.map((p) => (
          <PeliculaCard key={p.pelicula_id} pelicula={p} />
        ))}
      </div>
    </div>
  );
} 