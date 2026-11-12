import { Injectable, signal } from '@angular/core';
import * as signalR from '@microsoft/signalr';

export interface EventoAsiento {
  codigoAsiento: string;
  usuarioId?: string;
  tipo: 'bloqueado' | 'liberado';
  timestamp: Date;
}

@Injectable({
  providedIn: 'root'
})
export class SignalRService {
  private hubConnection: signalR.HubConnection | null = null;
  private readonly hubUrl = 'http://localhost:5000/hub/sala';

  // Angular Signals para reactividad directa sin pasar por Virtual DOM
  public readonly estadoConexion = signal<'desconectado' | 'conectando' | 'conectado' | 'error'>('desconectado');
  public readonly ultimoEvento = signal<EventoAsiento | null>(null);
  public readonly asientosBloqueadosEnVivo = signal<Set<string>>(new Set());

  public async iniciarConexion(funcionId: number): Promise<void> {
    if (this.hubConnection && this.hubConnection.state === signalR.HubConnectionState.Connected) {
      await this.unirseASala(funcionId);
      return;
    }

    this.estadoConexion.set('conectando');

    this.hubConnection = new signalR.HubConnectionBuilder()
      .withUrl(this.hubUrl, {
        transport: signalR.HttpTransportType.WebSockets | signalR.HttpTransportType.LongPolling,
        skipNegotiation: false
      })
      .withAutomaticReconnect([0, 2000, 5000, 10000])
      .configureLogging(signalR.LogLevel.Information)
      .build();

    // Escuchar eventos emitidos por el backend ASP.NET Core
    this.hubConnection.on('AsientoBloqueado', (codigoAsiento: string, usuarioId: string) => {
      console.log(`[SignalR] Asiento bloqueado: ${codigoAsiento} por ${usuarioId}`);
      this.ultimoEvento.set({
        codigoAsiento,
        usuarioId,
        tipo: 'bloqueado',
        timestamp: new Date()
      });

      this.asientosBloqueadosEnVivo.update(actuales => {
        const nuevo = new Set(actuales);
        nuevo.add(codigoAsiento);
        return nuevo;
      });
    });

    this.hubConnection.on('AsientoLiberado', (codigoAsiento: string) => {
      console.log(`[SignalR] Asiento liberado: ${codigoAsiento}`);
      this.ultimoEvento.set({
        codigoAsiento,
        tipo: 'liberado',
        timestamp: new Date()
      });

      this.asientosBloqueadosEnVivo.update(actuales => {
        const nuevo = new Set(actuales);
        nuevo.delete(codigoAsiento);
        return nuevo;
      });
    });

    this.hubConnection.onclose(() => {
      this.estadoConexion.set('desconectado');
    });

    this.hubConnection.onreconnecting(() => {
      this.estadoConexion.set('conectando');
    });

    this.hubConnection.onreconnected(async () => {
      this.estadoConexion.set('conectado');
      await this.unirseASala(funcionId);
    });

    try {
      await this.hubConnection.start();
      this.estadoConexion.set('conectado');
      console.log('[SignalR] Conectado exitosamente al Hub de Salas');
      await this.unirseASala(funcionId);
    } catch (err) {
      console.error('[SignalR] Error al conectar con el servidor:', err);
      this.estadoConexion.set('error');
    }
  }

  public async unirseASala(funcionId: number): Promise<void> {
    if (this.hubConnection?.state === signalR.HubConnectionState.Connected) {
      await this.hubConnection.invoke('UnirseASala', funcionId);
    }
  }

  public async salirDeSala(funcionId: number): Promise<void> {
    if (this.hubConnection?.state === signalR.HubConnectionState.Connected) {
      await this.hubConnection.invoke('SalirDeSala', funcionId);
    }
  }

  public async desconectar(): Promise<void> {
    if (this.hubConnection) {
      await this.hubConnection.stop();
      this.hubConnection = null;
      this.estadoConexion.set('desconectado');
    }
  }
}

