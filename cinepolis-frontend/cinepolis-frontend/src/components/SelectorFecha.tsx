interface Props {
  fechaSeleccionada: string;
  fechasDisponibles: string[];
  onSelect: (fecha: string) => void;
}

const DIAS = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
const MESES = [
  "Ene", "Feb", "Mar", "Abr", "May", "Jun",
  "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
];

function toISODate(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function parseDate(iso: string) {
  // ISO is YYYY-MM-DD
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function SelectorFecha({ fechaSeleccionada, fechasDisponibles, onSelect }: Props) {
  const hoyStr = toISODate(new Date());
  const hoyDate = parseDate(hoyStr);

  return (
    <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1 snap-x">
      {fechasDisponibles.map((iso) => {
        const d = parseDate(iso);
        const activo = iso === fechaSeleccionada;
        
        // Calculate difference in days safely
        const diffTime = d.getTime() - hoyDate.getTime();
        const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));
        
        let headerText = "";
        if (diffDays === 0) headerText = "Hoy";
        else if (diffDays === 1) headerText = "Mañana";
        else if (diffDays > 1 && diffDays < 7) headerText = DIAS[d.getDay()];

        const isShort = headerText === "";
        const dayStr = String(d.getDate());
        const monthStr = MESES[d.getMonth()];
        const bottomText = `${dayStr} ${monthStr}`;

        return (
          <button
            key={iso}
            onClick={() => onSelect(iso)}
            className={`flex flex-col items-center justify-center min-w-[80px] sm:min-w-[100px] h-14 rounded-lg border px-3 transition-colors snap-start shrink-0 ${
              activo
                ? "bg-cine-gold border-cine-gold text-cine-bg shadow-sm"
                : "bg-cine-bg-raised border-cine-line text-cine-cream-dim hover:border-cine-gold/50"
            }`}
          >
            {isShort ? (
              <span className="text-sm font-bold tracking-wide">
                {bottomText}
              </span>
            ) : (
              <>
                <span className={`text-[10px] uppercase font-bold tracking-wider mb-0.5 ${activo ? 'text-cine-bg/90' : 'text-cine-gold'}`}>
                  {headerText}
                </span>
                <span className="text-xs sm:text-sm font-bold tracking-wide leading-none">
                  {bottomText}
                </span>
              </>
            )}
          </button>
        );
      })}
    </div>
  );
}

export { toISODate };