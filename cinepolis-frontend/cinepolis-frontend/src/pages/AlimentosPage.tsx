import { useState, useMemo, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAppStore } from "../store/useAppStore";
import { getDulceria, getCarrito, agregarProductoCarrito, eliminarItemCarrito, crearCarrito } from "../api/endpoints";
import type { ProductoDulceria } from "../types/api";
import { ModalPersonalizacion } from "../components/ModalPersonalizacion";
import { CartSummary } from "../components/CartSummary";
import { ConfirmChangeComplexModal } from "../components/ConfirmChangeComplexModal";

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

/* ─── Tarjeta de Producto ─── */
interface ProductoCardProps {
  producto: ProductoDulceria;
  cantidadEnCarrito: number;
  onAgregar: () => void;
  onQuitar: () => void;
  isLoading: boolean;
}

function ProductoCard({ producto, cantidadEnCarrito, onAgregar, onQuitar, isLoading }: ProductoCardProps) {
  return (
    <article className="w-[200px] sm:w-[240px] shrink-0 bg-cine-bg-raised border border-cine-line rounded-xl overflow-hidden flex flex-col hover:border-cine-gold/40 transition-all snap-start group">
      <div className="aspect-[4/3] bg-cine-line/30 relative overflow-hidden">
        {producto.imagen_url ? (
          <img
            src={producto.imagen_url}
            alt={producto.nombre}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-cine-slate text-xs">Sin imagen</div>
        )}
        {producto.personalizacion.length > 0 && (
          <span className="absolute top-2 left-2 bg-cine-gold text-cine-bg text-[9px] font-black px-1.5 py-0.5 rounded-full uppercase tracking-wider">
            Personalizable
          </span>
        )}
      </div>
      <div className="p-3 flex flex-col flex-1">
        <h3 className="font-bold text-cine-cream text-sm leading-tight mb-1 line-clamp-2">{producto.nombre}</h3>
        <p className="text-cine-slate text-[10px] mb-3 line-clamp-2 flex-1 leading-relaxed">{producto.descripcion}</p>

        <div className="flex items-center justify-between mt-auto pt-2 border-t border-cine-line/50">
          <span className="font-mono text-base text-cine-gold font-bold">${producto.precio.toFixed(2)}</span>

          {cantidadEnCarrito === 0 ? (
            <button
              onClick={onAgregar}
              disabled={isLoading}
              className="bg-cine-gold text-cine-bg hover:bg-[#e5b33e] disabled:opacity-50 transition-colors px-3 py-1.5 rounded-lg text-xs font-black uppercase tracking-wider"
            >
              + Agregar
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={onQuitar}
                disabled={isLoading}
                className="w-6 h-6 rounded-full border border-cine-line text-cine-cream hover:border-cine-crimson hover:text-cine-crimson transition-colors text-sm font-bold flex items-center justify-center"
              >
                −
              </button>
              <span className="font-mono text-cine-cream font-bold text-sm w-4 text-center">{cantidadEnCarrito}</span>
              <button
                onClick={onAgregar}
                disabled={isLoading}
                className="w-6 h-6 rounded-full bg-cine-gold text-cine-bg hover:bg-cine-gold/80 transition-colors text-sm font-bold flex items-center justify-center"
              >
                +
              </button>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

/* ─── Main Page ─── */
export function AlimentosPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const complejoSlug = useAppStore((s) => s.complejoSlug);
  const setComplejoSlug = useAppStore((s) => s.setComplejoSlug);
  const carritoId = useAppStore((s) => s.carritoId);
  const carritoFuncionId = useAppStore((s) => s.carritoFuncionId);
  const setCarritoId = useAppStore((s) => s.setCarritoId);
  const setCarritoModoAlimentos = useAppStore((s) => s.setCarritoModoAlimentos);

  const [productoSeleccionado, setProductoSeleccionado] = useState<ProductoDulceria | null>(null);
  const catRefs = useRef<Record<string, HTMLElement | null>>({});
  const [pendingSlug, setPendingSlug] = useState<string | null>(null);

  // Crear carrito si no existe
  const mutCrear = useMutation({
    mutationFn: () => crearCarrito({ complejo_slug: complejoSlug }),
    onSuccess: (data) => {
      setCarritoId(data.carrito_id, null);
      setCarritoModoAlimentos(true);
    },
  });

  useEffect(() => {
    if (!carritoId && !mutCrear.isPending) {
      mutCrear.mutate();
    }
  }, [carritoId]);

  const { data: menuData, isLoading: isLoadingMenu } = useQuery({
    queryKey: ["dulceria", complejoSlug],
    queryFn: () => getDulceria(complejoSlug),
  });

  const { data: carritoData } = useQuery({
    queryKey: ["carrito", carritoId],
    queryFn: () => getCarrito(carritoId!),
    enabled: !!carritoId,
  });

  const handleCambioComplejo = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const slug = e.target.value;
    const hasItems = carritoData?.items && carritoData.items.length > 0;
    
    if (carritoId && hasItems) {
      setPendingSlug(slug);
    } else {
      setComplejoSlug(slug);
      setCarritoId(null);
    }
  };

  const confirmComplexChange = () => {
    if (pendingSlug) {
      setComplejoSlug(pendingSlug);
      setCarritoId(null);
      setPendingSlug(null);
    }
  };

  const mutAgregar = useMutation({
    mutationFn: (payload: any) => agregarProductoCarrito(carritoId!, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["carrito"] }),
  });
  const mutEliminar = useMutation({
    mutationFn: (detalleId: number) => eliminarItemCarrito(carritoId!, detalleId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["carrito"] }),
  });

  const categorias = menuData?.menu ?? [];

  // Cuántos de cada producto hay en el carrito (por producto_id)
  const cantidadesPorProducto = useMemo(() => {
    const map = new Map<number, number>();
    if (!carritoData?.items) return map;
    carritoData.items.forEach(item => {
      if (item.tipo_item === "producto" && item.producto_id != null) {
        map.set(item.producto_id, (map.get(item.producto_id) ?? 0) + item.cantidad);
      }
    });
    return map;
  }, [carritoData]);



  const handleAgregarProducto = (prod: ProductoDulceria) => {
    if (prod.personalizacion && prod.personalizacion.length > 0) {
      setProductoSeleccionado(prod);
    } else {
      mutAgregar.mutate({
        producto_id: prod.producto_id,
        cantidad: 1,
        precio_unitario: prod.precio,
        personalizaciones: [],
      });
    }
  };

  const handleQuitarProducto = (prod: ProductoDulceria) => {
    // Find the last detalle_carrito_id for this product and remove it
    const items = carritoData?.items.filter((i: any) => i.tipo_item === "producto" && i.producto_id === prod.producto_id) ?? [];
    if (items.length > 0) {
      const last = items[items.length - 1];
      mutEliminar.mutate(last.detalle_carrito_id);
    }
  };

  const handlePersonalizacionConfirmada = (
    prod: ProductoDulceria,
    personalizaciones: { opcion_id: number; porcentaje?: number; cantidad: number }[],
    precioFinal: number
  ) => {
    mutAgregar.mutate({
      producto_id: prod.producto_id,
      cantidad: 1,
      precio_unitario: precioFinal,
      personalizaciones,
    });
    setProductoSeleccionado(null);
  };

  const scrollToCategoria = (nombre: string) => {
    catRefs.current[nombre]?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

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

  if (isLoadingMenu) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-cine-slate font-mono animate-pulse">Cargando dulcería…</p>
      </div>
    );
  }


  return (
    <>
      {/* Modal de Personalización */}
      {productoSeleccionado && (
        <ModalPersonalizacion
          producto={productoSeleccionado}
          onAgregar={(sel, precioFinal) => handlePersonalizacionConfirmada(productoSeleccionado, sel, precioFinal)}
          onCerrar={() => setProductoSeleccionado(null)}
        />
      )}

      <div className="max-w-7xl mx-auto px-4 py-8 grid lg:grid-cols-[1fr_320px] gap-8 items-start">
        {/* ── LEFT: Catálogo ── */}
        <div className="min-w-0">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm text-cine-slate mb-4 font-mono">
            {carritoFuncionId ? (
              <button onClick={() => navigate(-1)} className="hover:text-cine-gold transition-colors">← Asientos</button>
            ) : (
              <button onClick={() => navigate("/")} className="hover:text-cine-gold transition-colors">← Inicio</button>
            )}
            <span className="text-cine-line">›</span>
            <span className="text-cine-cream font-bold">Alimentos</span>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-6 gap-4">
            <h1 className="font-display text-4xl tracking-wide leading-none">Alimentos</h1>
            {!carritoFuncionId && (
              <div className="flex flex-col">
                <label htmlFor="complejo-select" className="text-xs uppercase text-cine-slate mb-1 font-bold">Selecciona tu cine</label>
                <select
                  id="complejo-select"
                  value={complejoSlug}
                  onChange={handleCambioComplejo}
                  className="bg-cine-bg-raised border border-cine-line rounded-lg px-3 py-2 text-sm text-cine-cream outline-none focus:border-cine-gold transition-colors min-w-[200px]"
                >
                  {COMPLEJOS.map(c => (
                    <option key={c.slug} value={c.slug}>{c.nombre}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Category Tabs */}
          <div className="sticky top-0 z-10 bg-cine-bg/95 backdrop-blur-sm border-b border-cine-line pb-3 mb-8 pt-2">
            <div className="flex overflow-x-auto gap-2 hide-scrollbar">
              {categorias.map(cat => (
                <button
                  key={cat.categoria}
                  onClick={() => scrollToCategoria(cat.categoria)}
                  className="whitespace-nowrap px-4 py-2 rounded-full font-semibold text-xs transition-colors border bg-cine-bg-raised text-cine-slate border-cine-line hover:border-cine-gold hover:text-cine-cream flex-shrink-0"
                >
                  {cat.categoria}
                </button>
              ))}
            </div>
          </div>

          {/* Products by category */}
          <div className="space-y-12">
            {categorias.map(cat => (
              <section
                key={cat.categoria}
                ref={el => { catRefs.current[cat.categoria] = el; }}
                className="scroll-mt-24"
              >
                <h2 className="font-display text-2xl tracking-wide text-cine-cream mb-4">{cat.categoria}</h2>
                <div className="flex overflow-x-auto gap-4 pb-4 hide-scrollbar snap-x snap-mandatory">
                  {cat.productos.map(prod => (
                    <ProductoCard
                      key={prod.producto_id}
                      producto={prod}
                      cantidadEnCarrito={cantidadesPorProducto.get(prod.producto_id) ?? 0}
                      onAgregar={() => handleAgregarProducto(prod)}
                      onQuitar={() => handleQuitarProducto(prod)}
                      isLoading={mutAgregar.isPending || mutEliminar.isPending}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
        </div>

      {/* Columna Derecha: Sidebar Resumen */}
        {/* ── RIGHT: Sidebar ── */}
        <aside className="lg:sticky lg:top-6 h-[calc(100vh-6rem)]">
          <CartSummary />
        </aside>
      </div>

      <ConfirmChangeComplexModal 
        isOpen={pendingSlug !== null}
        onConfirm={confirmComplexChange}
        onCancel={() => setPendingSlug(null)}
      />
    </>
  );
}
