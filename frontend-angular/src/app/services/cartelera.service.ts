import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CarteleraResponse, MapaSalaResponse, BloqueoAsientoRequest } from '../models/cinepolis.models';

@Injectable({
  providedIn: 'root'
})
export class CarteleraService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = 'http://localhost:5000/api/v1';

  public getCartelera(complejoSlug: string = 'cinepolis-plaza-las-americas', fecha?: string): Observable<CarteleraResponse> {
    const url = fecha 
      ? `${this.apiUrl}/cartelera/${complejoSlug}?fecha=${fecha}`
      : `${this.apiUrl}/cartelera/${complejoSlug}`;
    return this.http.get<CarteleraResponse>(url);
  }

  public getMapaSala(funcionId: number): Observable<MapaSalaResponse> {
    return this.http.get<MapaSalaResponse>(`${this.apiUrl}/asientos/funcion/${funcionId}`);
  }

  public bloquearAsiento(request: BloqueoAsientoRequest): Observable<any> {
    return this.http.post(`${this.apiUrl}/asientos/bloquear`, request);
  }

  public liberarAsiento(request: BloqueoAsientoRequest): Observable<any> {
    return this.http.post(`${this.apiUrl}/asientos/liberar`, request);
  }
}
