"""
Tests de caracterización para el módulo de autenticación.
Estos tests capturan el comportamiento actual sin modificar código.
"""

import pytest
from fastapi import status


class TestCheckEmail:
    """Tests para /api/check-email"""
    
    def test_email_exists(self, client, regular_user):
        response = client.get("/api/check-email?email=user@test.com")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"registrado": True}
    
    def test_email_not_exists(self, client):
        response = client.get("/api/check-email?email=nonexistent@test.com")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"registrado": False}


class TestRegister:
    """Tests para /api/auth/register"""
    
    def test_register_success(self, client):
        response = client.post("/api/auth/register", json={
            "email": "new@test.com",
            "token": "any_token"
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "new@test.com"
        assert data["tipo"] == "usuario"
        assert data["plan"] == "free"
        assert data["plan_activo"] is False
        assert data["token"] == ""  # token no se expone al frontend
    
    def test_register_duplicate_email(self, client, regular_user):
        response = client.post("/api/auth/register", json={
            "email": "user@test.com",
            "token": "any_token"
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ya registrado" in response.json()["detail"]
    
    def test_register_invalid_email(self, client):
        response = client.post("/api/auth/register", json={
            "email": "invalid-email",
            "token": "any_token"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLogin:
    """Tests para /api/auth/login"""
    
    def test_login_success(self, client, regular_user):
        response = client.post("/api/auth/login", json={
            "email": "user@test.com",
            "token": regular_user.token
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "user@test.com"
        assert data["tipo"] == "usuario"
        assert data["plan_activo"] is False
    
    def test_login_wrong_token(self, client, regular_user):
        response = client.post("/api/auth/login", json={
            "email": "user@test.com",
            "token": "wrong_token"
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_wrong_email(self, client, regular_user):
        response = client.post("/api/auth/login", json={
            "email": "wrong@test.com",
            "token": regular_user.token
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_inactive_user(self, client, db_session):
        from app.models import Usuario
        user = Usuario(email="inactive@test.com", token="inactive_token", activo=False)
        db_session.add(user)
        db_session.commit()
        
        response = client.post("/api/auth/login", json={
            "email": "inactive@test.com",
            "token": "inactive_token"
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthMe:
    """Tests para /api/auth/me"""
    
    def test_me_success(self, client, regular_user, auth_headers_user):
        response = client.get("/api/auth/me", headers=auth_headers_user)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "user@test.com"
        assert data["tipo"] == "usuario"
    
    def test_me_no_token(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_me_invalid_token(self, client):
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPlanes:
    """Tests para /api/auth/planes"""
    
    def test_planes_free_user(self, client, free_user, auth_headers_free):
        response = client.get("/api/auth/planes", headers=auth_headers_free)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["plan"] == "free"
        assert data["activo"] is True
        assert data["puede_upgradear"] is True
        assert "upgrade" in data
        assert data["upgrade"]["basico"] == 10000
        assert data["upgrade"]["plus"] == 15000
    
    def test_planes_plus_user(self, client, plus_user, auth_headers_plus):
        response = client.get("/api/auth/planes", headers=auth_headers_plus)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["plan"] == "plus"
        assert data["activo"] is True
        assert data["puede_upgradear"] is False


class TestComprarPlan:
    """Tests para /api/auth/comprar-plan"""
    
    def test_comprar_plan_free_user(self, client, free_user, auth_headers_free):
        response = client.post("/api/auth/comprar-plan", json={
            "plan": "basico"
        }, headers=auth_headers_free)
        assert response.status_code == status.HTTP_502_BAD_GATEWAY  # Bold API fails in test
    
    def test_comprar_plan_already_active(self, client, plus_user, auth_headers_plus):
        response = client.post("/api/auth/comprar-plan", json={
            "plan": "plus"
        }, headers=auth_headers_plus)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ya tienes un plan" in response.json()["detail"].lower()


class TestUsuariosAdmin:
    """Tests para /api/usuarios (admin only)"""
    
    def test_listar_usuarios_admin(self, client, admin_user, auth_headers_admin):
        response = client.get("/api/usuarios", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_listar_usuarios_no_admin(self, client, regular_user, auth_headers_user):
        response = client.get("/api/usuarios", headers=auth_headers_user)
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_crear_usuario(self, client, admin_user, auth_headers_admin):
        response = client.post("/api/usuarios", json={
            "email": "newadmin@test.com",
            "token": "new_token",
            "activo": True,
            "tipo": "usuario"
        }, headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "newadmin@test.com"
        assert data["token"].startswith("****")
        assert len(data["token"]) == 8
        assert data["activo"] is True
    
    def test_crear_usuario_duplicate(self, client, admin_user, regular_user, auth_headers_admin):
        response = client.post("/api/usuarios", json={
            "email": "user@test.com",
            "token": "token",
            "activo": True,
            "tipo": "usuario"
        }, headers=auth_headers_admin)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_actualizar_usuario(self, client, admin_user, regular_user, auth_headers_admin):
        response = client.put(f"/api/usuarios/{regular_user.id}", json={
            "email": "updated@test.com",
            "token": "updated_token",
            "activo": True,
            "tipo": "usuario"
        }, headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "updated@test.com"
        assert data["token"].startswith("****")
        assert len(data["token"]) == 8
    
    def test_eliminar_usuario(self, client, admin_user, regular_user, auth_headers_admin):
        response = client.delete(f"/api/usuarios/{regular_user.id}", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"ok": True}
    
    def test_renovar_pago(self, client, admin_user, regular_user, auth_headers_admin):
        response = client.post(f"/api/usuarios/{regular_user.id}/pago", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["fecha_pago"] is not None
    
    def test_reset_token(self, client, admin_user, regular_user, auth_headers_admin):
        response = client.post(f"/api/usuarios/{regular_user.id}/reset-token", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["ok"] is True


class TestTokenMasking:
    """Tests para verificar que tokens se enmascaran en listados"""
    
    def test_usuario_response_masks_token(self, client, admin_user, auth_headers_admin):
        response = client.get("/api/usuarios", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for user in data:
            if len(user["token"]) > 8:
                assert user["token"].startswith("****")
