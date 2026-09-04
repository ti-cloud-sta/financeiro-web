import { Observable } from 'rxjs';
import { AppNotification } from '../models/notification.model';

export abstract class INotificationsService {
  abstract getNotifications(): Observable<AppNotification[]>;
  abstract getUnreadCount(): Observable<number>;
  abstract markAsRead(notificationId: string): Observable<void>;
  abstract markAllAsRead(): Observable<void>;
}
