"""
Tests de caracterización para el módulo de pagos.
Capturan el comportamiento actual de pagos, webhooks y Bold.
"""

import pytest
from fastapi import status
import json
import hmac
import hashlib
import base64


class TestCrearLinkPago:
    """Tests para /api/pagos/crear-link"""
    
    def test_crear_link_admin(self, client, admin_user, regular_user, auth_headers_admin):
        response = client.post(
            "/api/pagos/crear-link",
            json={
                "usuario_id": regular_user.id,
                "amount": 10000,
                "description": "Test payment",
                "expiration_minutes": 60
            },
            headers=auth_headers_admin
        )
        # Bold API fails in test - endpoint catches exception and returns 502
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
    
    def test_crear_link_not_admin(self, client, regular_user, auth_headers_user):
        response = client.post(
            "/api/pagos/crear-link",
            json={
                "usuario_id": regular_user.id,
                "amount": 10000,
            },
            headers=auth_headers_user
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_crear_link_user_not_found(self, client, admin_user, auth_headers_admin):
        response = client.post(
            "/api/pagos/crear-link",
            json={
                "usuario_id": 99999,
                "amount": 10000,
            },
            headers=auth_headers_admin
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_crear_link_invalid_amount(self, client, admin_user, regular_user, auth_headers_admin):
        response = client.post(
            "/api/pagos/crear-link",
            json={
                "usuario_id": regular_user.id,
                "amount": 500,
            },
            headers=auth_headers_admin
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestListarPagos:
    """Tests para /api/pagos"""
    
    def test_listar_pagos_admin(self, client, admin_user, sample_pago, auth_headers_admin):
        response = client.get("/api/pagos", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_listar_pagos_by_user(self, client, admin_user, regular_user, sample_pago, auth_headers_admin):
        response = client.get(f"/api/pagos?usuario_id={regular_user.id}", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_listar_pagos_not_admin(self, client, regular_user, auth_headers_user):
        response = client.get("/api/pagos", headers=auth_headers_user)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestObtenerPago:
    """Tests para /api/pagos/{id}"""
    
    def test_get_pago(self, client, admin_user, sample_pago, auth_headers_admin):
        response = client.get(f"/api/pagos/{sample_pago.id}", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_pago.id
        assert data["reference"] == sample_pago.reference
    
    def test_get_pago_not_found(self, client, admin_user, auth_headers_admin):
        response = client.get("/api/pagos/99999", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestEliminarPago:
    """Tests para DELETE /api/pagos/{id}"""
    
    def test_delete_pago(self, client, admin_user, sample_pago, auth_headers_admin):
        response = client.delete(f"/api/pagos/{sample_pago.id}", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}
    
    def test_delete_pago_not_admin(self, client, regular_user, sample_pago, auth_headers_user):
        response = client.delete(f"/api/pagos/{sample_pago.id}", headers=auth_headers_user)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestWebhookBold:
    """Tests para /api/webhooks/bold"""
    
    def test_webhook_invalid_signature(self, client):
        body = json.dumps({"type": "SALE_APPROVED"})
        response = client.post(
            "/api/webhooks/bold",
            content=body,
            headers={"Content-Type": "application/json", "x-bold-signature": "invalid"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_webhook_ignored_event_type(self, client):
        body = json.dumps({"type": "SALE_CREATED", "subject": "test"})
        body_str = body.encode("utf-8")
        encoded = base64.b64encode(body_str)
        
        import os
        secret = os.getenv("BOLD_SECRET_KEY", "test_bold_secret_key")
        computed = hmac.new(
            key=secret.encode(),
            digestmod=hashlib.sha256,
            msg=encoded,
        ).hexdigest()
        
        response = client.post(
            "/api/webhooks/bold",
            content=body,
            headers={"Content-Type": "application/json", "x-bold-signature": computed}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ignored"
    
    def test_webhook_no_reference(self, client):
        body = json.dumps({"type": "SALE_APPROVED", "data": {"metadata": {}}})
        body_str = body.encode("utf-8")
        encoded = base64.b64encode(body_str)
        
        import os
        secret = os.getenv("BOLD_SECRET_KEY", "test_bold_secret_key")
        computed = hmac.new(
            key=secret.encode(),
            digestmod=hashlib.sha256,
            msg=encoded,
        ).hexdigest()
        
        response = client.post(
            "/api/webhooks/bold",
            content=body,
            headers={"Content-Type": "application/json", "x-bold-signature": computed}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "no_reference"
    
    def test_webhook_pago_not_found(self, client):
        body = json.dumps({
            "type": "SALE_APPROVED",
            "data": {"metadata": {"reference": "nonexistent_ref"}}
        })
        body_str = body.encode("utf-8")
        encoded = base64.b64encode(body_str)
        
        import os
        secret = os.getenv("BOLD_SECRET_KEY", "test_bold_secret_key")
        computed = hmac.new(
            key=secret.encode(),
            digestmod=hashlib.sha256,
            msg=encoded,
        ).hexdigest()
        
        response = client.post(
            "/api/webhooks/bold",
            content=body,
            headers={"Content-Type": "application/json", "x-bold-signature": computed}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "pago_no_encontrado"
    
    def test_webhook_invalid_json(self, client):
        body = "not json"
        body_str = body.encode("utf-8")
        encoded = base64.b64encode(body_str)
        
        import os
        secret = os.getenv("BOLD_SECRET_KEY", "test_bold_secret_key")
        computed = hmac.new(
            key=secret.encode(),
            digestmod=hashlib.sha256,
            msg=encoded,
        ).hexdigest()
        
        response = client.post(
            "/api/webhooks/bold",
            content=body,
            headers={"Content-Type": "application/json", "x-bold-signature": computed}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestComprarPlan:
    """Tests para /api/auth/comprar-plan"""
    
    def test_comprar_plan_validation(self, client, free_user, auth_headers_free):
        response = client.post(
            "/api/auth/comprar-plan",
            json={"plan": "invalid"},
            headers=auth_headers_free
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUpgradePlan:
    """Tests para /api/auth/upgrade-plan"""
    
    def test_upgrade_plan_not_basico(self, client, free_user, auth_headers_free):
        response = client.post(
            "/api/auth/upgrade-plan",
            headers=auth_headers_free
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_upgrade_plan_expired(self, client, db_session, auth_headers_free):
        from app.models import Usuario
        from datetime import datetime, timezone, timedelta
        
        user = Usuario(
            email="expired@test.com",
            token="expired_token",
            activo=True,
            tipo="usuario",
            plan="basico",
            fecha_pago=datetime.now(timezone.utc) - timedelta(days=40)
        )
        db_session.add(user)
        db_session.commit()
        
        headers = {"Authorization": f"Bearer {user.token}"}
        response = client.post("/api/auth/upgrade-plan", headers=headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "vencio" in response.json()["detail"].lower() or "upgrade" in response.json()["detail"].lower()
