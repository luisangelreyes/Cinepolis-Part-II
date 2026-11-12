export interface Funcion {
  funcionId: number;
  horaInicio: string;
  formato: string;
  idioma: string;
  sala: string;
  tipoSala: string;
}

export interface CarteleraPelicula {
  peliculaId: number;
  titulo: string;
  clasificacion?: string;
  duracionMin?: number;
  posterUrl?: string;
  categoria?: string;
  funciones: Funcion[];
}

export interface CarteleraResponse {
  complejo: string;
  fechaConsulta: string;
  totalPeliculas: number;
  peliculas: CarteleraPelicula[];
}

export interface AsientoItem {
  asientoId: number;
  columna: number;
  etiqueta: string;
  tipo: string;
  estado: 'disponible' | 'bloqueado' | 'ocupado' | 'seleccionado';
  areaCode?: string;
}

export interface MapaSalaResponse {
  funcionId: number;
  peliculaId: number;
  pelicula: string;
  clasificacion?: string;
  duracionMin?: number;
  posterUrl?: string;
  sala: string;
  horaInicio: string;
  fechaFuncion: string;
  totalDisponibles: number;
  filas: { [fila: string]: AsientoItem[] };
}

export interface BloqueoAsientoRequest {
  funcionId: number;
  asientoId: number;
  codigoAsiento: string;
  usuarioId: string;
}

