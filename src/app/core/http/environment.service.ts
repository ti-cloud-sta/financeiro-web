import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';

export abstract class IEnvironmentService {
  abstract get apiUrl(): string;
  abstract get defaultTimeout(): number;
  abstract get maxRetries(): number;
}

@Injectable({
  providedIn: 'root'
})
export class EnvironmentService implements IEnvironmentService {
  get apiUrl(): string {
    return environment.apiUrl;
  }

  get defaultTimeout(): number {
    return 30000; // 30 segundos
  }

  get maxRetries(): number {
    return 2;
  }
}
