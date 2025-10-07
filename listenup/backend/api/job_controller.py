from flask import Blueprint, request, jsonify, current_app
from backend.modules.job.job_orchestrator_service import JobOrchestratorService

bp = Blueprint("job_controller", __name__)


@bp.route("/jobs", methods=["POST"])
def create_job():
    """
    Create a new job and enqueue it for processing.

    job_payload = {
        "steps": [
            {
            "name": "convert_audio",
            "service": "audio_service",
            "command_spec": {
                "program": "ffmpeg",
                "flags": {
                "-i": "{{input_file}}",
                "-ar": "44100",
                "-ac": "2"
                },
                "args": ["{{output_file}}"]
            },
            "inputs": {
                "input_file": "s3://bucket/audio/input.wav"
            },
            "outputs": {
                "output_file": "s3://bucket/audio/output.wav"
            }
            },
            {
            "name": "extract_features",
            "service": "ml_service",
            "command_spec": {
                "program": "feature_extractor",
                "flags": {
                "--input": "{{audio_file}}"
                },
                "args": ["--format", "csv", "{{features_output}}"]
            },
            "inputs": {
                "audio_file": "{{steps.convert_audio.outputs.output_file}}"
            },
            "outputs": {
                "features_output": "s3://bucket/features/output.csv"
            }
            }
        ],
        "step_transitions": [
            {
            "from_step_name": "convert_audio",
            "to_step_name": "extract_features",
            "output_to_input_mapping": {
                "output_file": "audio_file"
            }
            }
        ]
        }

    """
    try:
        payload = request.get_json(force=True)
        # The payload should contain both 'steps' and optionally 'step_transitions'
        steps_data = payload.get("steps")
        # Basic request validation
        if not steps_data or not isinstance(steps_data, list):
            return jsonify({"error": "Invalid or missing 'steps' field"}), 400
        # Get MongoDB instance from Flask app context
        from backend.app import mongo
        
        # Create orchestrator service and delegate all business logic
        orchestrator = JobOrchestratorService(mongo.db)
        # Pass the full payload to support step_transitions
        result = orchestrator.create_job(payload)
        return jsonify(result), 201

    except ValueError as e:
        # Validation errors (from Pydantic models in orchestrator)
        return jsonify({"error": f"Validation error: {str(e)}"}), 400
    except Exception as e:
        # Other errors
        return jsonify({"error": str(e)}), 500


@bp.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    """
    Fetch job details from MongoDB.
    """
    try:
        # Get MongoDB instance from Flask app context
        from backend.app import mongo
        
        # Create orchestrator service and delegate business logic
        orchestrator = JobOrchestratorService(mongo.db)
        job = orchestrator.get_job(job_id)
        
        if not job:
            return jsonify({"error": "Job not found"}), 404

        return jsonify(job), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/jobs/<job_id>/retry", methods=["POST"])
def retry_job(job_id):
    """
    Retry a failed or incomplete job from the first non-complete step.
    """
    try:
        # Get MongoDB instance from Flask app context
        from backend.app import mongo
        
        # Create orchestrator service and delegate retry logic
        orchestrator = JobOrchestratorService(mongo.db)
        result = orchestrator.retry_job(job_id)
        
        return jsonify(result), 200
        
    except ValueError as e:
        # Business logic errors (job not found, invalid state, etc.)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        # System errors
        return jsonify({"error": str(e)}), 500
