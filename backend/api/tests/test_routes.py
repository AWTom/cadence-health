"""Guards the routes the frontend depends on."""
from api.main import app

EXPECTED = {
    ("GET", "/api/units/{unit_id}"),
    ("GET", "/api/patients/{patient_id}"),
    ("POST", "/api/pt-plan"),
}


def test_frontend_routes_registered():
    registered = {(m, r.path) for r in app.routes for m in getattr(r, "methods", ())}
    assert EXPECTED <= registered
