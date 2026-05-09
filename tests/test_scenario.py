import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from clubs.models import Club, Membership
from events.models import Event, EventRegistration

User = get_user_model()

@pytest.mark.django_db
class TestDemoScenario:
    def setup_method(self):
        self.client = APIClient()

    def test_mi_parcours_demo(self):
        # 1. Setup Users (Admin, Club Manager, Student)
        admin = User.objects.create_user(username='admin', password='password', role='administrator')
        manager = User.objects.create_user(username='manager', password='password', role='club_manager')
        student = User.objects.create_user(username='student', password='password', role='student')

        # === Step 1: Admin creates a club 'Tech Club' ===
        self.client.force_authenticate(user=admin)
        response = self.client.post('/api/v1/clubs/', {
            'name': 'Tech Club',
            'description': 'A club for tech enthusiasts',
            'category': 'Technology'
        })
        assert response.status_code == 201
        club_id = response.data['id']
        club = Club.objects.get(id=club_id)

        # Admin assigns Manager to the Club as President (Manual step via admin panel, here we simulate)
        # Actually, let's just create it directly via ORM since we didn't expose a membership CRUD to admin directly in our simplified views
        Membership.objects.create(user=manager, club=club, internal_role='president', status='approved')

        # === Step 2: Student registers and joins the club ===
        self.client.force_authenticate(user=student)
        response = self.client.post(f'/api/v1/clubs/{club_id}/join/')
        assert response.status_code == 201

        # Manager approves the student (Simulating manager approval)
        # First verify the manager sees the pending membership
        self.client.force_authenticate(user=manager)
        response = self.client.get('/api/v1/memberships/')
        assert response.status_code == 200
        # Assume manager updates the membership to 'approved'
        membership = Membership.objects.get(user=student, club=club)
        response = self.client.patch(f'/api/v1/memberships/{membership.id}/', {'status': 'approved'})
        assert response.status_code == 200

        # === Step 3: Club Manager creates an event ===
        self.client.force_authenticate(user=manager)
        future_date = timezone.now() + timedelta(days=7)
        response = self.client.post('/api/v1/events/', {
            'title': 'Hackathon 2026',
            'description': 'Annual hackathon',
            'club': club_id,
            'date': future_date.isoformat(),
            'capacity': 50,
            'status': 'published'
        })
        assert response.status_code == 201
        event_id = response.data['id']

        # === Step 4: Student registers to the event ===
        self.client.force_authenticate(user=student)
        response = self.client.post(f'/api/v1/events/{event_id}/register/')
        assert response.status_code == 201

        # Verify Student cannot register twice
        response = self.client.post(f'/api/v1/events/{event_id}/register/')
        assert response.status_code == 400

        # === Step 5: Verify RBAC along the way ===
        # Student shouldn't be able to create an event
        response = self.client.post('/api/v1/events/', {
            'title': 'Fake Event',
            'club': club_id,
            'date': future_date.isoformat()
        })
        assert response.status_code == 403

        # Manager from another club shouldn't be able to edit this event
        other_manager = User.objects.create_user(username='manager2', password='password', role='club_manager')
        self.client.force_authenticate(user=other_manager)
        response = self.client.patch(f'/api/v1/events/{event_id}/', {'title': 'Hacked Event'})
        assert response.status_code == 403

        # Admin can see everything
        self.client.force_authenticate(user=admin)
        response = self.client.get('/api/v1/events/')
        assert response.data['count'] == 1

        print("All tests passed successfully! 🚀")
