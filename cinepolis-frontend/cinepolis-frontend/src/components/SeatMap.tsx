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
  numeroLogico: number;
}

const COLOR_POR_ESTADO: Record<EstadoAsiento, string> = {
  disponible: "var(--color-cine-cream-dim)",
  reservado: "var(--color-cine-slate)",
  vendido: "var(--color-cine-crimson-dim)",
  bloqueado: "#3a3f52",
};


const VIEW_W = 1000;

function construirLayout(mapa: Record<string, AsientoAPI[]>) {
  const filas = Object.keys(mapa).sort();
  const posiciones: AsientoPosicionado[] = [];

  const ASIENTO_SIZE = 26;
  const GAP_X = 10;
  const GAP_Y = 12;

  let minCol = Infinity;
  let maxCol = -Infinity;

  Object.values(mapa).forEach((asientos) => {
    asientos.forEach((a) => {
      if (a.columna < minCol) minCol = a.columna;
      if (a.columna > maxCol) maxCol = a.columna;
    });
  });

  const numCols = maxCol - minCol + 1;
  const gridWidth = numCols * ASIENTO_SIZE + (numCols - 1) * GAP_X;
  const startX = (VIEW_W - gridWidth) / 2;
  const startY = 80;

  filas.forEach((fila, i) => {
    const asientos = mapa[fila];
    const y = startY + i * (ASIENTO_SIZE + GAP_Y);

    // Calcular X para cada asiento
    const asientosConX = asientos.map((asiento) => {
      // Cinépolis numera de derecha a izquierda, por lo que invertimos la columna física
      const x = startX + (maxCol - asiento.columna) * (ASIENTO_SIZE + GAP_X);
      return { ...asiento, x, y, fila };
    });

    // Ordenar de mayor X a menor X (de derecha a izquierda visualmente)
    asientosConX.sort((a, b) => b.x - a.x);

    // Asignar número lógico 1, 2, 3... a cada asiento visible
    asientosConX.forEach((asiento, index) => {
      posiciones.push({ ...asiento, numeroLogico: index + 1 });
    });
  });

  const alturaTotal = startY + filas.length * (ASIENTO_SIZE + GAP_Y) + 60;
  return { posiciones, filas, alturaTotal, startX, startY, ASIENTO_SIZE, GAP_Y };
}

export function SeatMap({ mapa, seleccionados, onToggle }: Props) {
  const { posiciones, filas, alturaTotal, startX, startY, ASIENTO_SIZE, GAP_Y } = useMemo(() => construirLayout(mapa), [mapa]);

  return (
    <div className="w-full">
      <svg
        viewBox={`0 0 ${VIEW_W} ${alturaTotal}`}
        className="w-full h-auto select-none"
        role="img"
        aria-label="Mapa de la sala"
      >
        {/* Pantalla recta */}
        <path
          d={`M ${startX - 40} 30 L ${VIEW_W - startX + 40} 30`}
          fill="none"
          stroke="var(--color-cine-gold)"
          strokeWidth={4}
          strokeLinecap="round"
          opacity={0.9}
        />
        <text
          x={VIEW_W / 2}
          y={20}
          textAnchor="middle"
          fill="var(--color-cine-gold)"
          fontSize={14}
          letterSpacing={6}
          fontFamily="var(--font-body)"
          opacity={0.85}
        >
          PANTALLA
        </text>

        {/* Etiquetas de fila a la izquierda */}
        {filas.map((fila, i) => {
          const y = startY + i * (ASIENTO_SIZE + GAP_Y) + ASIENTO_SIZE / 2 + 5;
          return (
            <text
              key={`label-${fila}`}
              x={startX - 30}
              y={y}
              fontFamily="var(--font-mono)"
              fontSize={14}
              fontWeight={600}
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
                x={0}
                y={0}
                width={ASIENTO_SIZE}
                height={ASIENTO_SIZE}
                rx={6}
                fill={estaSeleccionado ? color : "transparent"}
                stroke={color}
                strokeWidth={2}
                opacity={a.estado === "disponible" || estaSeleccionado ? 1 : 0.4}
              />
              <text
                x={ASIENTO_SIZE / 2}
                y={ASIENTO_SIZE / 2 + 4}
                textAnchor="middle"
                fontSize={11}
                fontFamily="var(--font-mono)"
                fontWeight="500"
                fill={estaSeleccionado ? "#111" : color}
                opacity={a.estado === "disponible" || estaSeleccionado ? 1 : 0.4}
                pointerEvents="none"
              >
                {a.numeroLogico}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="flex flex-wrap gap-4 justify-center mt-4 text-sm text-cine-cream-dim">
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
