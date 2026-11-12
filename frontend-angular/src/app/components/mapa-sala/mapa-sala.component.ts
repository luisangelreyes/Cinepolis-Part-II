import { Component, OnInit, OnDestroy, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CarteleraService } from '../../services/cartelera.service';
import { SignalRService } from '../../services/signalr.service';
import { MapaSalaResponse, AsientoItem } from '../../models/cinepolis.models';

@Component({
  selector: 'app-mapa-sala',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './mapa-sala.component.html',
  styleUrls: ['./mapa-sala.component.css']
})
export class MapaSalaComponent implements OnInit, OnDestroy {
  private readonly carteleraService = inject(CarteleraService);
  public readonly signalR = inject(SignalRService);

  public readonly funcionId = signal<number>(101);
  public readonly mapa = signal<MapaSalaResponse | null>(null);
  public readonly cargando = signal<boolean>(true);
  public readonly error = signal<string | null>(null);

  // Asientos que el usuario local ha seleccionado
  public readonly misAsientosSeleccionados = signal<string[]>([]);
  public readonly precioBoleto = 85;

  // Señal calculada automáticamente sin costo de renderizado adicional
  public readonly totalPagar = computed(() => this.misAsientosSeleccionados().length * this.precioBoleto);

  public filasOrdenadas = computed(() => {
    const m = this.mapa();
    if (!m) return [];
    return Object.keys(m.filas).sort();
  });

  async ngOnInit(): Promise<void> {
    await this.cargarSala();
    await this.signalR.iniciarConexion(this.funcionId());
  }

  async ngOnDestroy(): Promise<void> {
    await this.signalR.salirDeSala(this.funcionId());
    await this.signalR.desconectar();
  }

  public async cargarSala(): Promise<void> {
    this.cargando.set(true);
    this.error.set(null);

    this.carteleraService.getMapaSala(this.funcionId()).subscribe({
      next: (data) => {
        this.mapa.set(data);
        this.cargando.set(false);
      },
      error: (err) => {
        // En caso de que no haya BD corriendo localmente, generamos una sala demo interactiva
        console.warn('Backend DB no disponible aún, cargando sala demo interactiva para visualización:', err);
        this.cargarSalaDemo();
        this.cargando.set(false);
      }
    });
  }

  public toggleAsiento(asiento: AsientoItem): void {
    const codigo = asiento.etiqueta;

    // Si está ocupado o bloqueado por otro usuario vía SignalR, no se puede seleccionar
    if (asiento.estado === 'ocupado' || this.signalR.asientosBloqueadosEnVivo().has(codigo)) {
      return;
    }

    const seleccionados = this.misAsientosSeleccionados();
    const yaSeleccionado = seleccionados.includes(codigo);

    if (yaSeleccionado) {
      this.misAsientosSeleccionados.update(lista => lista.filter(a => a !== codigo));
      this.carteleraService.liberarAsiento({
        funcionId: this.funcionId(),
        asientoId: asiento.asientoId,
        codigoAsiento: codigo,
        usuarioId: 'usuario_demo'
      }).subscribe();
    } else {
      if (seleccionados.length >= 8) {
        alert('Máximo 8 boletos por transacción.');
        return;
      }
      this.misAsientosSeleccionados.update(lista => [...lista, codigo]);
      this.carteleraService.bloquearAsiento({
        funcionId: this.funcionId(),
        asientoId: asiento.asientoId,
        codigoAsiento: codigo,
        usuarioId: 'usuario_demo'
      }).subscribe();
    }
  }

  public getEstadoAsiento(asiento: AsientoItem): string {
    const codigo = asiento.etiqueta;
    if (this.misAsientosSeleccionados().includes(codigo)) {
      return 'seleccionado';
    }
    if (this.signalR.asientosBloqueadosEnVivo().has(codigo)) {
      return 'bloqueado-tiempo-real';
    }
    return asiento.estado;
  }

  private cargarSalaDemo(): void {
    const filas: { [fila: string]: AsientoItem[] } = {};
    const letras = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'];

    letras.forEach((fila, fIndex) => {
      filas[fila] = [];
      for (let c = 1; c <= 14; c++) {
        const esOcupado = (fIndex === 4 && (c === 6 || c === 7)) || (fIndex === 7 && c === 8);
        filas[fila].push({
          asientoId: fIndex * 14 + c,
          columna: c,
          etiqueta: `${fila}${c}`,
          tipo: 'tradicional',
          estado: esOcupado ? 'ocupado' : 'disponible'
        });
      }
    });

    this.mapa.set({
      funcionId: 101,
      peliculaId: 1,
      pelicula: 'Avengers: Secret Wars',
      clasificacion: 'B15',
      duracionMin: 180,
      sala: 'Sala 4 - Macro XE',
      horaInicio: '19:30',
      fechaFuncion: '2026-11-12',
      totalDisponibles: 137,
      filas
    });
  }
}
