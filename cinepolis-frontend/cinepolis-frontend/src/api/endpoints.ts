import { api } from "./client";
import type {
  CarteleraResponse,
  MapaAsientosResponse,
  PreciosFuncionResponse,
  CarritoCreado,
  CarritoResponse,
  PeliculaDetalle,
  MenuDulceriaResponse,
  AgregarProductoPayload,
} from "../types/api";

export async function getCartelera(complejoSlug: string, fecha?: string) {
  const { data } = await api.get<CarteleraResponse>(`/api/cartelera/${complejoSlug}`, {
    params: fecha ? { fecha } : undefined,
  });
  return data;
}

export async function getFechasCartelera(complejoSlug: string) {
  const { data } = await api.get<string[]>(`/api/cartelera/${complejoSlug}/fechas`);
  return data;
}

export async function getPelicula(peliculaId: number) {
  const { data } = await api.get<PeliculaDetalle>(`/api/pelicula/${peliculaId}`);
  return data;
}

export async function getAsientosPorFuncion(funcionId: number) {
  const { data } = await api.get<MapaAsientosResponse>(`/api/funcion/${funcionId}/asientos`);
  return data;
}

export async function getPreciosPorFuncion(funcionId: number) {
  const { data } = await api.get<PreciosFuncionResponse>(`/api/funcion/${funcionId}/precios`);
  return data;
}

export async function crearCarrito(payload: { sesion_id?: number; socio_id?: number }) {
  const { data } = await api.post<CarritoCreado>(`/api/carrito`, payload);
  return data;
}

export async function getCarrito(carritoId: number) {
  const { data } = await api.get<CarritoResponse>(`/api/carrito/${carritoId}`);
  return data;
}

export async function agregarAsientoCarrito(
  carritoId: number,
  payload: { asiento_id: number; tipo_boleto_id: number; precio_unitario: number }
) {
  const { data } = await api.post(`/api/carrito/${carritoId}/asientos`, payload);
  return data;
}

export async function eliminarItemCarrito(carritoId: number, detalleCarritoId: number) {
  const { data } = await api.delete(`/api/carrito/${carritoId}/items/${detalleCarritoId}`);
  return data;
}

export async function extenderCarrito(carritoId: number) {
  const { data } = await api.post(`/api/carrito/${carritoId}/extender`);
  return data;
}

export async function getDulceria(complejoSlug: string) {
  const { data } = await api.get<MenuDulceriaResponse>(`/api/dulceria/${complejoSlug}`);
  return data;
}

export async function agregarProductoCarrito(
  carritoId: number,
  payload: AgregarProductoPayload
) {
  const { data } = await api.post(`/api/carrito/${carritoId}/productos`, payload);
  return data;
}

export async function pagarCarrito(
  carritoId: number,
  payload: {
    forma_pago: string;
    tipo_venta?: string;
    nombre_comprador?: string;
    apellido_comprador?: string;
    correo_comprador?: string;
  }
) {
  const { data } = await api.post(`/api/carrito/${carritoId}/pagar`, payload);
  return data;
}
