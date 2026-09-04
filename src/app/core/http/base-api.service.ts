import { Observable } from 'rxjs';
import { HttpService, RequestOptions } from './http.service';
import { inject } from '@angular/core';

export abstract class BaseApiService<T> {
  protected http = inject(HttpService);
  
  constructor(protected resourceUrl: string) {}

  getAll(options?: RequestOptions): Observable<T[]> {
    return this.http.get<T[]>(this.resourceUrl, options);
  }

  getById(id: string | number, options?: RequestOptions): Observable<T> {
    return this.http.get<T>(`${this.resourceUrl}/${id}`, options);
  }

  create(data: Partial<T>, options?: RequestOptions): Observable<T> {
    return this.http.post<T>(this.resourceUrl, data, options);
  }

  update(id: string | number, data: Partial<T>, options?: RequestOptions): Observable<T> {
    return this.http.put<T>(`${this.resourceUrl}/${id}`, data, options);
  }

  delete(id: string | number, options?: RequestOptions): Observable<void> {
    return this.http.delete<void>(`${this.resourceUrl}/${id}`, options);
  }
}
