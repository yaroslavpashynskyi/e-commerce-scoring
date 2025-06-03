from logging.config import dictConfig
from flask import Flask
from backend.data.database import initialize_database
from api.products import products_bp
from api.ranking import rank_bp

def create_app():
    """Створює Flask-додаток, реєструє API-блютпринти та налаштовує логування."""
    dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'default'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'app.log',
                'maxBytes': 10*1024*1024,
                'backupCount': 3,
                'formatter': 'default'
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console', 'file']
        }
    })

    app = Flask(__name__)
    initialize_database()
    app.register_blueprint(products_bp)
    app.register_blueprint(rank_bp)
    return app

if __name__ == '__main__':
    create_app().run(debug=True, port=8000)
