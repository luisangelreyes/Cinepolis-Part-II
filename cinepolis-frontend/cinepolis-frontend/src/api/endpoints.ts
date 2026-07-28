import { api } from "./client";
import type {
  CarteleraResponse,
  MapaAsientosResponse,
  PreciosFuncionResponse,
  CarritoCreado,
  CarritoResponse,
  PeliculaDetalle,
} from "../types/api";

export async function getCartelera(complejoSlug: string, fecha?: string) {
  const { data } = await api.get<CarteleraResponse>(`/api/cartelera/${complejoSlug}`, {
    params: fecha ? { fecha } : undefined,
  });
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
