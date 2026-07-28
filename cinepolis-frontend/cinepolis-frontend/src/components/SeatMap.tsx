import { useMemo } from "react";
import type { AsientoAPI, EstadoAsiento } from "../types/api";

interface Props {
  mapa: Record<string, AsientoAPI[]>;
  seleccionados: Set<number>;
  onToggle: (asiento: AsientoAPI) => void;
}

interface AsientoPosicionado extends AsientoAPI {
  x: number;
  y: number;
  fila: string;
}

const COLOR_POR_ESTADO: Record<EstadoAsiento, string> = {
  disponible: "var(--color-cine-cream-dim)",
  reservado: "var(--color-cine-slate)",
  vendido: "var(--color-cine-crimson-dim)",
  bloqueado: "#3a3f52",
};

const CENTRO = { x: 500, y: 40 };
const RADIO_INICIAL = 130;
const PASO_RADIO = 46;
const ANCHO_ASIENTO = 25;
const VIEW_W = 1000;

function construirLayout(mapa: Record<string, AsientoAPI[]>) {
  const filas = Object.keys(mapa).sort();
  const posiciones: AsientoPosicionado[] = [];

  filas.forEach((fila, i) => {
    const asientos = [...mapa[fila]].sort((a, b) => a.columna - b.columna);
    const radio = RADIO_INICIAL + i * PASO_RADIO;
    const anguloPorAsiento = ANCHO_ASIENTO / radio; // radianes
    const anguloTotal = anguloPorAsiento * (asientos.length - 1);
    const anguloInicio = -anguloTotal / 2;

    asientos.forEach((asiento, j) => {
      const angulo = anguloInicio + j * anguloPorAsiento;
      const x = CENTRO.x + radio * Math.sin(angulo);
      const y = CENTRO.y + radio * Math.cos(angulo);
      posiciones.push({ ...asiento, x, y, fila });
    });
  });

  const alturaTotal = CENTRO.y + RADIO_INICIAL + filas.length * PASO_RADIO + 40;
  return { posiciones, filas, alturaTotal };
}

export function SeatMap({ mapa, seleccionados, onToggle }: Props) {
  const { posiciones, filas, alturaTotal } = useMemo(() => construirLayout(mapa), [mapa]);

  return (
    <div className="w-full">
      <svg
        viewBox={`0 -20 ${VIEW_W} ${alturaTotal}`}
        className="w-full h-auto select-none"
        role="img"
        aria-label="Mapa de la sala"
      >
        {/* Pantalla curva */}
        <path
          d={`M ${CENTRO.x - 260} 10 Q ${CENTRO.x} -30 ${CENTRO.x + 260} 10`}
          fill="none"
          stroke="var(--color-cine-gold)"
          strokeWidth={4}
          strokeLinecap="round"
          opacity={0.9}
        />
        <text
          x={CENTRO.x}
          y={-10}
          textAnchor="middle"
          fill="var(--color-cine-gold)"
          fontSize={13}
          letterSpacing={4}
          fontFamily="var(--font-body)"
          opacity={0.85}
        >
          PANTALLA
        </text>

        {/* Etiquetas de fila a la izquierda */}
        {filas.map((fila, i) => {
          const radio = RADIO_INICIAL + i * PASO_RADIO;
          return (
            <text
              key={`label-${fila}`}
              x={CENTRO.x - radio - 26}
              y={CENTRO.y + radio + 4}
              fontFamily="var(--font-mono)"
              fontSize={12}
              fill="var(--color-cine-slate)"
              textAnchor="middle"
            >
              {fila}
            </text>
          );
        })}

        {/* Asientos */}
        {posiciones.map((a) => {
          const estaSeleccionado = seleccionados.has(a.asiento_id);
          const clickeable = a.estado === "disponible";
          const color = estaSeleccionado ? "var(--color-cine-gold)" : COLOR_POR_ESTADO[a.estado];

          return (
            <g
              key={a.asiento_id}
              transform={`translate(${a.x}, ${a.y})`}
              onClick={() => clickeable && onToggle(a)}
              style={{ cursor: clickeable ? "pointer" : "not-allowed" }}
              tabIndex={clickeable ? 0 : -1}
              role="button"
              aria-label={`Asiento ${a.etiqueta}, ${estaSeleccionado ? "seleccionado" : a.estado}`}
              onKeyDown={(e) => {
                if (clickeable && (e.key === "Enter" || e.key === " ")) onToggle(a);
              }}
            >
              <rect
                x={-9}
                y={-9}
                width={18}
                height={18}
                rx={4}
                fill={estaSeleccionado ? color : "transparent"}
                stroke={color}
                strokeWidth={1.6}
                opacity={a.estado === "disponible" || estaSeleccionado ? 1 : 0.5}
              />
            </g>
          );
        })}
      </svg>

      <div className="flex flex-wrap gap-4 justify-center mt-4 text-xs text-cine-cream-dim">
        <Leyenda color="var(--color-cine-cream-dim)" etiqueta="Disponible" outline />
        <Leyenda color="var(--color-cine-gold)" etiqueta="Seleccionado" />
        <Leyenda color="var(--color-cine-slate)" etiqueta="Reservado" outline />
        <Leyenda color="var(--color-cine-crimson-dim)" etiqueta="Vendido" outline />
      </div>
    </div>
  );
}

function Leyenda({ color, etiqueta, outline }: { color: string; etiqueta: string; outline?: boolean }) {
  return (
    <div className="flex items-center gap-1.5">
      <span
        className="inline-block w-3.5 h-3.5 rounded-[3px]"
        style={{
          backgroundColor: outline ? "transparent" : color,
          border: `1.6px solid ${color}`,
        }}
      />
      {etiqueta}
    </div>
  );
}
