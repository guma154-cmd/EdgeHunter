"""
EdgeHunter Backend — Entry Point
"""
from app import create_app, db
from app.data.scheduler import start_scheduler

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("[OK] Database inicializado")
    
    start_scheduler(app)
    print("[OK] Scheduler iniciado")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
