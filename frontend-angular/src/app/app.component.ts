import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MapaSalaComponent } from './components/mapa-sala/mapa-sala.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, MapaSalaComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent {
  title = 'Cinépolis Vision Web (Angular 19 + .NET 8)';
}
