import { Observable } from 'rxjs';
import { MenuItem } from '../models/menu.model';

export abstract class IMenuService {
  abstract getMenu(): Observable<MenuItem[]>;
}
