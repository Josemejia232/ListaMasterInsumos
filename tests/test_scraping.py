"""
Tests de caracterización para el módulo de scraping.
Capturan el comportamiento actual de los endpoints de scraping.
"""

import pytest
from fastapi import status


class TestScrapeSync:
    """Tests para /scrape/sync"""
    
    def test_scrape_sync_unsupported_url(self, client, admin_user, auth_headers_admin):
        response = client.get(
            "/scrape/sync?url=https://unsupported.com/product",
            headers=auth_headers_admin
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "dominio" in response.json()["detail"].lower() or "no soportada" in response.json()["detail"].lower()
    
    def test_scrape_sync_admin_required(self, client, regular_user, auth_headers_user):
        response = client.get(
            "/scrape/sync?url=https://easy.com.co/product",
            headers=auth_headers_user
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_scrape_sync_no_auth(self, client):
        response = client.get("/scrape/sync?url=https://easy.com.co/product")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestScrapeFromSheet:
    """Tests para /scrape"""
    
    def test_scrape_from_sheet_invalid_url(self, client, admin_user, auth_headers_admin):
        response = client.post(
            "/scrape",
            json={"sheet_url": "https://invalid.com/sheet"},
            headers=auth_headers_admin
        )
        # Pydantic validation rejects non-Google URLs
        assert response.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    def test_scrape_from_sheet_not_admin(self, client, regular_user, auth_headers_user):
        response = client.post(
            "/scrape",
            json={"sheet_url": "https://docs.google.com/spreadsheets/d/test/edit"},
            headers=auth_headers_user
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestScrapeDaily:
    """Tests para /scrape/daily"""
    
    def test_scrape_daily_not_admin(self, client, regular_user, auth_headers_user):
        response = client.post("/scrape/daily", headers=auth_headers_user)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestSyncCategories:
    """Tests para /sync/categories"""
    
    def test_sync_categories_not_admin(self, client, regular_user, auth_headers_user):
        response = client.post("/sync/categories", headers=auth_headers_user)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestURLValidation:
    """Tests para la validación de URLs (SSRF prevention)"""
    
    def test_validate_scrape_url_blocked(self, client, admin_user, auth_headers_admin):
        response = client.get(
            "/scrape/sync?url=https://evil.com/product",
            headers=auth_headers_admin
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "dominio" in response.json()["detail"].lower()
    
    def test_validate_sheet_url_blocked(self, client, admin_user, auth_headers_admin):
        response = client.post(
            "/scrape",
            json={"sheet_url": "https://evil.com/sheet"},
            headers=auth_headers_admin
        )
        # Pydantic validation rejects non-Google URLs
        assert response.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY)


class TestRateLimiting:
    """Tests para rate limiting - disabled in test mode"""
    
    def test_rate_limit_disabled_in_tests(self, client):
        # Rate limiting is mocked in tests, so 11 requests should all succeed
        for i in range(11):
            response = client.post("/api/auth/register", json={
                "email": f"test{i}@test.com",
                "token": "any"
            })
        
        # All requests should succeed because rate limiting is mocked
        assert response.status_code == status.HTTP_200_OK
