"""
Tests de caracterización para el módulo de productos.
Capturan el comportamiento actual de listado, detalle, y actualización.
"""

import pytest
from fastapi import status


class TestListarProductos:
    """Tests para /productos"""
    
    def test_listar_productos_plus_user(self, client, plus_user, sample_producto, auth_headers_plus):
        response = client.get("/productos", headers=auth_headers_plus)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["descripcion"] == "Test Product"
    
    def test_listar_productos_free_user(self, client, free_user, sample_producto_free, auth_headers_free):
        """Free users get only 10 items per category with headers."""
        response = client.get("/productos", headers=auth_headers_free)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert response.headers["X-Free-Tier"] == "1"
        assert "X-Total-Count" in response.headers
    
    def test_listar_productos_no_auth(self, client):
        response = client.get("/productos")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_listar_productos_with_tienda_filter(self, client, plus_user, sample_producto, auth_headers_plus):
        response = client.get("/productos?tienda=Test", headers=auth_headers_plus)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_listar_productos_pagination(self, client, plus_user, sample_producto, auth_headers_plus):
        response = client.get("/productos?skip=0&limit=10", headers=auth_headers_plus)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10


class TestObtenerProducto:
    """Tests para /productos/{id}"""
    
    def test_get_producto_exists(self, client, sample_producto):
        response = client.get(f"/productos/{sample_producto.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_producto.id
        assert data["descripcion"] == "Test Product"
        assert data["codigo"] == "TEST001"
    
    def test_get_producto_not_found(self, client):
        response = client.get("/productos/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestActualizarAjustada:
    """Tests para /productos/{id}/ajustada"""
    
    def test_update_ajustada(self, client, admin_user, sample_producto, auth_headers_admin):
        response = client.put(
            f"/productos/{sample_producto.id}/ajustada",
            json={"descripcion_ajustada": "Updated Description", "categoria": "New Category"},
            headers=auth_headers_admin
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["descripcion_ajustada"] == "Updated Description"
        assert data["categoria"] == "New Category"
    
    def test_update_ajustada_not_admin(self, client, regular_user, sample_producto, auth_headers_user):
        response = client.put(
            f"/productos/{sample_producto.id}/ajustada",
            json={"descripcion_ajustada": "Updated"},
            headers=auth_headers_user
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_update_ajustada_not_found(self, client, admin_user, auth_headers_admin):
        response = client.put(
            "/productos/99999/ajustada",
            json={"descripcion_ajustada": "Updated"},
            headers=auth_headers_admin
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestInsumosCRUD:
    """Tests para /api/insumos (legacy)"""
    
    def test_listar_insumos(self, client, sample_producto):
        response = client.get("/api/insumos")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_crear_insumo(self, client, admin_user, auth_headers_admin):
        response = client.post("/api/insumos", json={
            "descripcion": "New Insumo",
            "un": "Kg",
            "valor": 5000.0
        }, headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["descripcion"] == "New Insumo"
        assert data["un"] == "Kg"
        assert data["valor"] == 5000.0
    
    def test_actualizar_insumo(self, client, admin_user, db_session, auth_headers_admin):
        from app.models import Insumo
        insumo = Insumo(descripcion="Old", un="Unidad", valor=100.0)
        db_session.add(insumo)
        db_session.commit()
        
        response = client.put(f"/api/insumos/{insumo.id}", json={
            "descripcion": "Updated",
            "un": "Kg",
            "valor": 200.0
        }, headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["descripcion"] == "Updated"
        assert data["valor"] == 200.0
    
    def test_eliminar_insumo(self, client, admin_user, db_session, auth_headers_admin):
        from app.models import Insumo
        insumo = Insumo(descripcion="To Delete", un="Unidad", valor=100.0)
        db_session.add(insumo)
        db_session.commit()
        
        response = client.delete(f"/api/insumos/{insumo.id}", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"ok": True}


class TestDebugSinCategoria:
    """Tests para /debug/sin-categoria"""
    
    def test_debug_sin_categoria(self, client, admin_user, auth_headers_admin):
        response = client.get("/debug/sin-categoria", headers=auth_headers_admin)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestStats:
    """Tests para /api/stats"""
    
    def test_stats(self, client, sample_producto):
        response = client.get("/api/stats")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total" in data
        assert "total_valor" in data
        assert "scrapeados_hoy" in data
        assert "tiendas" in data
        assert data["total"] >= 1


class TestCache:
    """Tests para verificar comportamiento de caché"""
    
    def test_cache_miss(self, client, plus_user, sample_producto, auth_headers_plus):
        response = client.get("/productos", headers=auth_headers_plus)
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["X-Cache"] == "MISS"
    
    def test_cache_hit(self, client, plus_user, sample_producto, auth_headers_plus):
        # First call
        client.get("/productos", headers=auth_headers_plus)
        # Second call should hit cache
        response = client.get("/productos", headers=auth_headers_plus)
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["X-Cache"] == "HIT"
