import { Observable } from 'rxjs';
import { AppModule } from '../models/module.model';

export abstract class IModulesService {
  abstract getAvailableModules(): Observable<AppModule[]>;
  abstract getActiveModules(): Observable<AppModule[]>;
}
