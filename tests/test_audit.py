from audit.models import AuditLog


def test_only_admin_can_read_logs(auth_client, admin_client, auth_user):
    AuditLog.objects.create(
        action=AuditLog.AuditAction.USER_LOGIN,
        user=auth_user,
    )

    forbidden = auth_client.get('/api/v1/audit-logs/')
    assert forbidden.status_code == 403

    allowed = admin_client.get('/api/v1/audit-logs/')
    assert allowed.status_code == 200
    assert allowed.data['count'] == 1
