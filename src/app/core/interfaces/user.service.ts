import { Observable } from 'rxjs';
import { User } from '../models/user.model';

export abstract class IUserService {
  abstract getUserProfile(): Observable<User>;
  abstract updateProfile(user: Partial<User>): Observable<User>;
}
