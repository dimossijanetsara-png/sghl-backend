"""Authentication API tests."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import json

User = get_user_model()


@pytest.mark.django_db
class TestAuthenticationAPI:
    """Test authentication endpoints."""

    def test_login_success(self, client, doctor_user):
        """Test successful login with valid credentials."""
        response = client.post(
            '/api/v1/auth/login',
            {
                'email': 'doctor@sghl.test',
                'password': 'TestDoctor123!',
            },
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.json()
        assert 'access' in data
        assert 'refresh' in data
        assert data['role'] == 'DOCTOR'

    def test_login_invalid_credentials(self, client, doctor_user):
        """Test login with invalid password."""
        response = client.post(
            '/api/v1/auth/login',
            {
                'email': 'doctor@sghl.test',
                'password': 'WrongPassword',
            },
            content_type='application/json',
        )
        assert response.status_code == 401

    def test_login_non_existent_user(self, client):
        """Test login with non-existent email."""
        response = client.post(
            '/api/v1/auth/login',
            {
                'email': 'nonexistent@sghl.test',
                'password': 'SomePassword123!',
            },
            content_type='application/json',
        )
        assert response.status_code == 401

    def test_login_account_locked_after_5_attempts(self, client, doctor_user):
        """Test account lockout after 5 failed login attempts."""
        for _ in range(5):
            client.post(
                '/api/v1/auth/login',
                {
                    'email': 'doctor@sghl.test',
                    'password': 'WrongPassword',
                },
                content_type='application/json',
            )

        # 6th attempt should be locked
        response = client.post(
            '/api/v1/auth/login',
            {
                'email': 'doctor@sghl.test',
                'password': 'WrongPassword',
            },
            content_type='application/json',
        )
        assert response.status_code == 423  # Locked

    def test_refresh_token(self, client, doctor_user):
        """Test token refresh."""
        # Get initial tokens
        response = client.post(
            '/api/v1/auth/login',
            {
                'email': 'doctor@sghl.test',
                'password': 'TestDoctor123!',
            },
            content_type='application/json',
        )
        refresh_token = response.json()['refresh']

        # Refresh the token
        response = client.post(
            '/api/v1/auth/refresh',
            {'refresh': refresh_token},
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.json()
        assert 'access' in data
        assert 'refresh' in data

    def test_logout(self, client, doctor_user):
        """Test logout endpoint."""
        # Login first
        response = client.post(
            '/api/v1/auth/login',
            {
                'email': 'doctor@sghl.test',
                'password': 'TestDoctor123!',
            },
            content_type='application/json',
        )
        refresh_token = response.json()['refresh']
        access_token = response.json()['access']

        # Logout
        response = client.post(
            '/api/v1/auth/logout',
            {'refresh': refresh_token},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {access_token}',
        )
        assert response.status_code == 200

    def test_get_current_user(self, client, doctor_user):
        """Test getting current user info."""
        refresh = RefreshToken.for_user(doctor_user)

        response = client.get(
            '/api/v1/auth/me',
            HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}',
        )
        assert response.status_code == 200
        data = response.json()
        assert data['email'] == 'doctor@sghl.test'
        assert data['role'] == 'DOCTOR'

    def test_update_profile(self, client, doctor_user):
        """Test updating user profile."""
        refresh = RefreshToken.for_user(doctor_user)

        response = client.patch(
            '/api/v1/auth/me',
            {
                'first_name': 'Jean-Pierre',
                'phone': '+243987654321',
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}',
        )
        assert response.status_code == 200
        data = response.json()
        assert data['first_name'] == 'Jean-Pierre'
        assert data['phone'] == '+243987654321'

    def test_change_password(self, client, doctor_user):
        """Test changing user password."""
        refresh = RefreshToken.for_user(doctor_user)

        response = client.post(
            '/api/v1/auth/change-password',
            {
                'old_password': 'TestDoctor123!',
                'new_password': 'NewPassword123!',
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}',
        )
        assert response.status_code == 200

        # Verify old password no longer works
        response = client.post(
            '/api/v1/auth/login',
            {
                'email': 'doctor@sghl.test',
                'password': 'TestDoctor123!',
            },
            content_type='application/json',
        )
        assert response.status_code == 401

    @pytest.mark.slow
    def test_mfa_setup_and_verification(self, client, doctor_user):
        """Test MFA setup flow."""
        refresh = RefreshToken.for_user(doctor_user)

        # Setup MFA
        response = client.post(
            '/api/v1/auth/mfa/setup',
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}',
        )
        assert response.status_code == 200
        data = response.json()
        assert 'secret' in data
        assert 'qr_image_base64' in data

    def test_register_only_by_admin(self, client, admin_user, doctor_user):
        """Test that only admins can register new users."""
        # Admin can register
        admin_refresh = RefreshToken.for_user(admin_user)
        response = client.post(
            '/api/v1/auth/register',
            {
                'email': 'newuser@sghl.test',
                'password': 'NewUser123!',
                'first_name': 'New',
                'last_name': 'User',
                'role': 'DOCTOR',
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {str(admin_refresh.access_token)}',
        )
        assert response.status_code == 200

        # Non-admin cannot register
        doctor_refresh = RefreshToken.for_user(doctor_user)
        response = client.post(
            '/api/v1/auth/register',
            {
                'email': 'anotheruser@sghl.test',
                'password': 'AnotherUser123!',
                'first_name': 'Another',
                'last_name': 'User',
                'role': 'NURSE',
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {str(doctor_refresh.access_token)}',
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestTokenBlacklist:
    """Test JWT token blacklist functionality."""

    def test_refresh_token_blacklist_on_rotation(self, client, doctor_user):
        """Test that old refresh tokens are blacklisted after rotation."""
        from apps.authentication.models import RefreshTokenBlacklist

        # Get initial tokens
        response = client.post(
            '/api/v1/auth/login',
            {
                'email': 'doctor@sghl.test',
                'password': 'TestDoctor123!',
            },
            content_type='application/json',
        )
        old_refresh = response.json()['refresh']

        # Refresh token once
        response = client.post(
            '/api/v1/auth/refresh',
            {'refresh': old_refresh},
            content_type='application/json',
        )
        assert response.status_code == 200

        # Old token should be in blacklist
        assert RefreshTokenBlacklist.objects.filter(token=old_refresh).exists()

        # Using old refresh token should fail
        response = client.post(
            '/api/v1/auth/refresh',
            {'refresh': old_refresh},
            content_type='application/json',
        )
        assert response.status_code == 401
