import { Injectable } from '@angular/core';
import { Observable, delay, of } from 'rxjs';
import { INotificationsService } from '../interfaces/notifications.service';
import { AppNotification } from '../models/notification.model';
import { MOCK_NOTIFICATIONS } from '../mock/notifications.mock';

@Injectable({
  providedIn: 'root'
})
export class MockNotificationsService implements INotificationsService {
  private notifications = [...MOCK_NOTIFICATIONS];

  getNotifications(): Observable<AppNotification[]> {
    return of(this.notifications).pipe(delay(500));
  }

  getUnreadCount(): Observable<number> {
    const count = this.notifications.filter(n => !n.isRead).length;
    return of(count).pipe(delay(200));
  }

  markAsRead(notificationId: string): Observable<void> {
    this.notifications = this.notifications.map(n => 
      n.id === notificationId ? { ...n, isRead: true } : n
    );
    return of(void 0).pipe(delay(200));
  }

  markAllAsRead(): Observable<void> {
    this.notifications = this.notifications.map(n => ({ ...n, isRead: true }));
    return of(void 0).pipe(delay(400));
  }
}
