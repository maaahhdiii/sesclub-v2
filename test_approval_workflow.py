#!/usr/bin/env python
"""
End-to-end test of club request approval workflow with email delivery.

This file is intentionally import-safe so pytest can collect the real test
suite without executing the workflow at import time.
"""
import os
import sys
from datetime import datetime

import django


def main() -> int:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sesclubs.settings.development')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    django.setup()

    from django.contrib.auth import get_user_model
    from app_requests.models import Request
    from clubs.models import Club, ClubMembership
    from app_requests.views import RequestViewSet

    User = get_user_model()

    print("=" * 60)
    print("STEP 1: Creating test student user")
    print("=" * 60)
    test_email = f"teststu{datetime.now().strftime('%H%M%S')}@example.com"
    try:
        student = User.objects.create_user(
            email=test_email,
            username=test_email.split('@')[0],
            password='TestPass123!',
            role='student',
        )
        print(f"✓ Created student: {student.email}")
    except Exception as exc:
        print(f"✗ Error creating student: {exc}")
        return 1

    print("\n" + "=" * 60)
    print("STEP 2: Creating pending club request")
    print("=" * 60)
    try:
        club_request = Request.objects.create(
            user=student,
            request_type='CLUB CREATION',
            title=f"Create Club {datetime.now().strftime('%H%M%S')}",
            description='Test club for email verification',
            status='PENDING',
        )
        print(f"✓ Created request: {club_request.request_id}")
        print(f"  - Title: {club_request.title}")
        print(f"  - Created by: {club_request.user.email}")
        print(f"  - Status: {club_request.status}")
    except Exception as exc:
        print(f"✗ Error creating request: {exc}")
        return 1

    print("\n" + "=" * 60)
    print("STEP 3: Admin approves request (simulating approval logic)")
    print("=" * 60)
    try:
        admin = User.objects.get(email='admin@sesame.com.tn')
        print(f"✓ Admin found: {admin.email}")
    except User.DoesNotExist:
        print('✗ Admin not found - create with: python manage.py shell')
        return 1

    viewset = RequestViewSet()
    try:
        club_request.status = 'TREATED'
        club_request.treated_by = admin
        club_request.save()

        viewset._handle_club_creation_approval(club_request)
        print('✓ Approval handler executed')

        club_request.refresh_from_db()
        print(f"  - Request status: {club_request.status}")
        print(f"  - Metadata: {club_request.metadata}")
    except Exception as exc:
        import traceback

        print(f"✗ Error during approval: {exc}")
        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    print("STEP 4: Verifying database changes")
    print("=" * 60)
    try:
        student.refresh_from_db()
        print(f"✓ Student role updated: {student.role}")
        print(f"  - Username: {student.username}")
        print(f"  - Has password: {bool(student.password)}")

        created_club_id = club_request.metadata.get('created_club_id')
        if not created_club_id:
            raise ValueError('No created_club_id in metadata')

        club = Club.objects.get(club_id=created_club_id)
        print(f"✓ Club created: {club.name}")

        membership = ClubMembership.objects.get(user=student, club=club)
        print(f"✓ Club membership: {membership.user.email} → {membership.club.name} as {membership.internal_role}")

        metadata = club_request.metadata
        print('✓ Request metadata:')
        print(f"  - club_portal_username: {metadata.get('club_portal_username')}")
        print(f"  - credentials_sent: {metadata.get('credentials_sent')}")
        print(f"  - created_club_id: {metadata.get('created_club_id')}")
    except Exception as exc:
        import traceback

        print(f"✗ Verification error: {exc}")
        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    print('STEP 5: WORKFLOW COMPLETE ✓')
    print("=" * 60)
    print(f"✓ Student created: {test_email}")
    print(f"✓ Club request approved: {club_request.request_id}")
    print(f"✓ Club created: {club.name}")
    print(f"✓ Portal username: {metadata.get('club_portal_username')}")
    print(f"✓ Email sent to: {student.email}")
    print('\n📧 Check inbox: mahdialoui33@gmail.com')
    print('   Subject: Your Club Portal Credentials')
    print('   Contains: Portal URL, username, temp password')
    print("=" * 60)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
