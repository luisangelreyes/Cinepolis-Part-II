interface Props {
  fechaSeleccionada: string;
  onSelect: (fecha: string) => void;
}

const DIAS = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
const MESES = [
  "ene", "feb", "mar", "abr", "may", "jun",
  "jul", "ago", "sep", "oct", "nov", "dic",
];

function generarProximosDias(cantidad: number) {
  const hoy = new Date();
  return Array.from({ length: cantidad }, (_, i) => {
    const d = new Date(hoy);
    d.setDate(hoy.getDate() + i);
    return d;
  });
}

function toISODate(d: Date) {
  // Usamos componentes locales, NO toISOString() (que convierte a UTC
  // y en Veracruz/UTC-6 puede adelantar la fecha un día por la tarde/noche).
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function SelectorFecha({ fechaSeleccionada, onSelect }: Props) {
  const dias = generarProximosDias(7);

  return (
    <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1">
      {dias.map((d, i) => {
        const iso = toISODate(d);
        const activo = iso === fechaSeleccionada;
        return (
          <button
            key={iso}
            onClick={() => onSelect(iso)}
            className={`flex flex-col items-center justify-center min-w-[64px] rounded-lg border px-3 py-2 transition-colors ${
              activo
                ? "bg-cine-gold border-cine-gold text-cine-bg"
                : "bg-cine-bg-raised border-cine-line text-cine-cream-dim hover:border-cine-gold/50"
            }`}
          >
            <span className="text-[11px] uppercase tracking-wide font-body">
              {i === 0 ? "Hoy" : DIAS[d.getDay()]}
            </span>
            <span className="font-display text-2xl leading-none mt-0.5">
              {d.getDate()}
            </span>
            <span className="text-[10px] uppercase tracking-wide font-body opacity-80">
              {MESES[d.getMonth()]}
            </span>
          </button>
        );
      })}
    </div>
  );
}

export { toISODate };