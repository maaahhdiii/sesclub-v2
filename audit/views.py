from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from users.permissions import IsVerified

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
	queryset = AuditLog.objects.all().order_by('-timestamp')
	serializer_class = AuditLogSerializer
	permission_classes = [permissions.IsAuthenticated, IsVerified]

	def get_queryset(self):
		if not getattr(self.request.user, 'is_administrator', False):
			raise PermissionDenied()
		return super().get_queryset()
