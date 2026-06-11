import os
import sys
import hmac
import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from typing import Generator

# Force test database before importing app
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ADMIN_EMAIL"] = "admin@test.com"
os.environ["ADMIN_TOKEN"] = "test_admin_token_12345678901234567890"
os.environ["SHEET_URL"] = "https://docs.google.com/spreadsheets/d/test/edit"
os.environ["ALLOWED_ORIGINS"] = "https://localhost"
os.environ["FORCE_HTTPS"] = "false"
os.environ["BOLD_API_KEY"] = "test_bold_api_key"
os.environ["BOLD_SECRET_KEY"] = "test_bold_secret_key"
os.environ["BOLD_WEBHOOK_IPS"] = ""

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, get_db
from app.models import Producto, Insumo, Usuario, Pago, UsoCalculo, RateLimit, CacheEntry
from app.main import app

# Create in-memory engine with shared connection (single connection pool)
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create tables
Base.metadata.create_all(bind=engine)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Shared session for tests - all tests use the same session
_shared_session = None


def get_shared_session():
    global _shared_session
    if _shared_session is None:
        _shared_session = TestingSessionLocal()
    return _shared_session


def override_get_db():
    """Override get_db for tests - use shared session."""
    db = get_shared_session()
    try:
        yield db
    finally:
        pass  # Don't close - shared session


# Override dependency
app.dependency_overrides[get_db] = override_get_db

# Mock rate limiting functions to avoid DB issues in tests
# We monkeypatch the dependencies module functions directly
import app.dependencies as deps_module


def mock_rate_limit_login(request, db=None):
    pass


def mock_rate_limit_scrape(request, db=None):
    pass


deps_module.rate_limit_login = mock_rate_limit_login
deps_module.rate_limit_scrape = mock_rate_limit_scrape

# Also patch the local bindings in routers that imported these functions
import app.routers.auth as auth_router
import app.routers.payments as payments_router
import app.routers.scraping as scraping_router

auth_router.rate_limit_login = mock_rate_limit_login
auth_router.rate_limit_scrape = mock_rate_limit_scrape
payments_router.rate_limit_scrape = mock_rate_limit_scrape
scraping_router.rate_limit_scrape = mock_rate_limit_scrape


@pytest.fixture(scope="session")
def db_engine():
    """Create a test engine for the session."""
    yield engine


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Provide a fresh database session for each test."""
    global _shared_session
    
    # Close old shared session if exists
    if _shared_session is not None:
        _shared_session.close()
        _shared_session = None
    
    # Create new shared session
    db = get_shared_session()
    
    # Clear all tables before each test
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    
    yield db


@pytest.fixture(scope="function")
def client(db_session) -> Generator[TestClient, None, None]:
    """Provide a test client with fresh database."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_user(db_session) -> Usuario:
    """Create an admin user."""
    user = Usuario(
        email="admin@test.com",
        token="test_admin_token_12345678901234567890",
        activo=True,
        tipo="admin"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session) -> Usuario:
    """Create a regular user."""
    user = Usuario(
        email="user@test.com",
        token="test_user_token_12345678901234567890",
        activo=True,
        tipo="usuario"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def free_user(db_session) -> Usuario:
    """Create a free user (no payment)."""
    user = Usuario(
        email="free@test.com",
        token="free_user_token_12345678901234567890",
        activo=True,
        tipo="usuario",
        plan=None,
        fecha_pago=None
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def plus_user(db_session) -> Usuario:
    """Create a Plus user with recent payment."""
    from datetime import datetime, timezone
    user = Usuario(
        email="plus@test.com",
        token="plus_user_token_12345678901234567890",
        activo=True,
        tipo="usuario",
        plan="plus",
        fecha_pago=datetime.now(timezone.utc)
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_producto(db_session) -> Producto:
    """Create a sample product."""
    product = Producto(
        codigo="TEST001",
        descripcion="Test Product",
        unidad="Unidad",
        valor=1000.0,
        tienda="Test Store",
        url_origen="https://test.com/product/1",
        categoria="Category",
        n01="N01",
        n02="N02",
        n03="N03",
        proveedor="Test Supplier",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def sample_producto_free(db_session) -> Producto:
    """Create a sample product for free tier."""
    product = Producto(
        codigo="FREE001",
        descripcion="Free Product",
        unidad="Unidad",
        valor=500.0,
        tienda="Free Store",
        url_origen="https://test.com/product/2",
        n01="Category",
        n02="Sub",
        n03="Item",
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def sample_pago(db_session, regular_user) -> Pago:
    """Create a sample payment."""
    pago = Pago(
        usuario_id=regular_user.id,
        payment_link="link_test",
        url="https://bold.co/pay/test",
        reference="basico_usr_1_1234567890",
        amount=10000.0,
        status="ACTIVE",
    )
    db_session.add(pago)
    db_session.commit()
    db_session.refresh(pago)
    return pago


@pytest.fixture
def auth_headers_admin(admin_user):
    """Generate admin auth headers."""
    return {"Authorization": f"Bearer {admin_user.token}"}


@pytest.fixture
def auth_headers_user(regular_user):
    """Generate regular user auth headers."""
    return {"Authorization": f"Bearer {regular_user.token}"}


@pytest.fixture
def auth_headers_free(free_user):
    """Generate free user auth headers."""
    return {"Authorization": f"Bearer {free_user.token}"}


@pytest.fixture
def auth_headers_plus(plus_user):
    """Generate plus user auth headers."""
    return {"Authorization": f"Bearer {plus_user.token}"}
