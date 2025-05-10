from app import app
from routes_maintenance import register_maintenance_blueprint

# Registra il blueprint di manutenzione
register_maintenance_blueprint(app)

# Log informativo sull'utilizzo del sistema semplificato
app.logger.info("Utilizzo del sistema di storage semplificato per i documenti")
app.logger.info(f"Directory di upload: {app.config['UPLOAD_FOLDER']}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
