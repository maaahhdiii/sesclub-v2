from communications.models import Notification


def notify(user, title, body):
    return Notification.objects.create(user=user, title=title, body=body)