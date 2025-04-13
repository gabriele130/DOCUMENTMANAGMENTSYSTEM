from app import app, db

with app.app_context():
    print("Resetting database...")
    db.session.rollback()
    db.drop_all()
    db.create_all()
    print("Database reset completed.")