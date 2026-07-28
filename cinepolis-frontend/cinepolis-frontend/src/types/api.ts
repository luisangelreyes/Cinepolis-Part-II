// Tipos calcados de las respuestas de main.py (FastAPI)

export interface FuncionCartelera {
  funcion_id: number;
  hora_inicio: string;
  formato: string;
  idioma: string;
  sala: string;
  tipo_sala: string;
}

export interface PeliculaCartelera {
  pelicula_id: number;
  titulo: string;
  clasificacion: string;
  duracion_min: number;
  poster_url: string | null;
  categoria: string;
  funciones: FuncionCartelera[];
}

export interface CarteleraResponse {
  complejo: string;
  fecha_consulta: string;
  total_peliculas: number;
  peliculas: PeliculaCartelera[];
  mensaje?: string;
}

export type EstadoAsiento = "disponible" | "reservado" | "vendido" | "bloqueado";

export interface AsientoAPI {
  asiento_id: number;
  columna: number;
  etiqueta: string;
  tipo: string;
  estado: EstadoAsiento;
}

export interface MapaAsientosResponse {
  funcion_id: number;
  pelicula: string;
  sala: string;
  horario: string;
  asientos_disponibles: number;
  mapa: Record<string, AsientoAPI[]>;
}

export interface TarifaBoleto {
  tipo_boleto_id: number;
  tipo_boleto: string;
  precio: number;
  cargo_servicio: number;
  total_online: number;
}

export interface PreciosFuncionResponse {
  funcion_id: number;
  tarifas: TarifaBoleto[];
}

export interface CarritoCreado {
  carrito_id: number;
  fecha_creacion: string;
  fecha_expiracion: string;
}

export interface DetalleCarritoItem {
  detalle_carrito_id: number;
  tipo_item: "boleto" | "producto";
  cantidad: number;
  precio_unitario: number;
  asiento_id: number | null;
  producto_id: number | null;
  tipo_boleto_id: number | null;
}

export interface CarritoResponse {
  carrito_id: number;
  estado: string;
  fecha_expiracion: string;
  items: DetalleCarritoItem[];
  subtotal: number;
}

export interface PeliculaDetalle {
  pelicula_id: number;
  titulo: string;
  slug: string;
  clasificacion: string;
  genero: string;
  duracion_min: number;
  sinopsis: string;
  categoria: string;
  poster_url: string | null;
  banner_url: string | null;
  trailer_url: string | null;
  director: string | null;
  actores: string[];
}
