"""
EdgeHunter — Rotas de Modelos e IA
"""
from flask import Blueprint, jsonify
from app.models import ModelVersion

models_bp = Blueprint('models', __name__)


@models_bp.route('/', methods=['GET'])
def list_models():
    """Lista versões de modelos."""
    models = ModelVersion.query.order_by(ModelVersion.trained_at.desc()).limit(20).all()
    return jsonify({'models': [m.to_dict() for m in models]})


@models_bp.route('/active', methods=['GET'])
def active_model():
    """Modelo atualmente em produção."""
    model = ModelVersion.query.filter_by(is_active=True).first()
    if not model:
        return jsonify({
            'is_trained': False,
            'version': None,
            'message': 'Nenhum modelo treinado ainda. Execute o retraining inicial.',
            'metrics': {},
            'weights': {}
        })

    result = model.to_dict()

    from app.engine.ensemble import _get_global_ensemble
    ensemble = _get_global_ensemble()
    if ensemble:
        result['live_weights'] = ensemble.ensemble.weights

    return jsonify(result)


@models_bp.route('/weights', methods=['GET'])
def model_weights():
    """Pesos atuais do ensemble."""
    from app.engine.ensemble import _get_global_ensemble
    ensemble = _get_global_ensemble()

    if not ensemble:
        return jsonify({'weights': {}, 'is_ready': False})

    return jsonify({
        'weights': ensemble.ensemble.weights,
        'is_ready': ensemble.is_ready,
        'brier_history': {
            model: len(hist)
            for model, hist in ensemble.ensemble.brier_history.items()
        }
    })


@models_bp.route('/drift', methods=['GET'])
def drift_status():
    """Status do drift detector."""
    from app.engine.drift import _get_global_drift_detector
    detector = _get_global_drift_detector()

    if not detector:
        return jsonify({'status': 'não inicializado'})

    return jsonify(detector.get_summary())


@models_bp.route('/train', methods=['POST'])
def trigger_train():
    """Dispara retraining manual."""
    try:
        from app.data.scheduler import _retrain_task
        from flask import current_app
        import threading

        thread = threading.Thread(
            target=_retrain_task,
            args=(current_app._get_current_object(),)
        )
        thread.daemon = True
        thread.start()

        return jsonify({'message': 'Retraining iniciado em background'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
