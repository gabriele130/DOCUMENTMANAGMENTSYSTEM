from app import app
from routes_maintenance import register_maintenance_blueprint

# Registra il blueprint di manutenzione
register_maintenance_blueprint(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
