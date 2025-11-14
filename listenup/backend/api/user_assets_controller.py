from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os

# Environment-configurable storage root
STORAGE_ROOT = os.getenv("STORAGE_ROOT", "/app/storage")

bp = Blueprint("user_assets", __name__)
# FIXME: instead of a host like user:// we need to check the environment
# and either upload to the local storage dir or a yet-to-be-implemented remote storage
# like S3
@bp.route("/users/<user_id>/assets", methods=["POST"])
def upload_user_asset(user_id):
    """
    Upload an asset for a user.
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
            
        # Get optional folder from form data
        folder = request.form.get('folder', None)
        
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Create user upload directory structure
        if folder:
            upload_dir = f"{STORAGE_ROOT}/users/{user_id}/uploads/{folder}"
        else:
            upload_dir = f"{STORAGE_ROOT}/users/{user_id}/uploads"
            
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Create asset URI
        if folder:
            asset_uri = f"user://uploads/{folder}/{filename}"
        else:
            asset_uri = f"user://uploads/{filename}"
        
        return jsonify({
            "asset_uri": asset_uri,
            "filename": filename,
            "folder": folder,
            "user_id": user_id,
            "storage_path": file_path
        }), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/users/<user_id>/assets", methods=["GET"])
def list_user_assets(user_id):
    """
    List assets for a user.
    """
    try:
        folder = request.args.get('folder', None)
        
        # Build directory path
        if folder:
            asset_dir = f"{STORAGE_ROOT}/users/{user_id}/uploads/{folder}"
        else:
            asset_dir = f"{STORAGE_ROOT}/users/{user_id}/uploads"
            
        assets = []
        
        if os.path.exists(asset_dir):
            for item in os.listdir(asset_dir):
                item_path = os.path.join(asset_dir, item)
                
                if os.path.isfile(item_path):
                    # It's a file
                    if folder:
                        asset_uri = f"user://uploads/{folder}/{item}"
                    else:
                        asset_uri = f"user://uploads/{item}"
                        
                    assets.append({
                        "name": item,
                        "asset_uri": asset_uri,
                        "type": "file",
                        "size": os.path.getsize(item_path)
                    })
                elif os.path.isdir(item_path):
                    # It's a folder
                    file_count = len([f for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f))])
                    assets.append({
                        "name": item,
                        "type": "folder",
                        "file_count": file_count
                    })
        
        return jsonify({
            "user_id": user_id,
            "folder": folder,
            "assets": assets
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/users/<user_id>/jobs", methods=["GET"])
def list_user_jobs(user_id):
    """
    List completed jobs for a user.
    """
    try:
        jobs_dir = f"{STORAGE_ROOT}/users/{user_id}/jobs"
        jobs = []
        
        if os.path.exists(jobs_dir):
            for job_id in os.listdir(jobs_dir):
                job_dir = os.path.join(jobs_dir, job_id)
                if os.path.isdir(job_dir):
                    # Get final outputs
                    final_output_dir = os.path.join(job_dir, "final_output")
                    final_outputs = []
                    
                    if os.path.exists(final_output_dir):
                        for output_file in os.listdir(final_output_dir):
                            if os.path.isfile(os.path.join(final_output_dir, output_file)):
                                final_outputs.append({
                                    "name": output_file,
                                    "uri": f"user://jobs/{job_id}/final_output/{output_file}"
                                })
                    
                    # Get step directories
                    step_dirs = []
                    for item in os.listdir(job_dir):
                        item_path = os.path.join(job_dir, item)
                        if os.path.isdir(item_path) and item.startswith("step_"):
                            step_dirs.append(item)
                    
                    jobs.append({
                        "job_id": job_id,
                        "final_outputs": final_outputs,
                        "step_count": len(step_dirs),
                        "has_intermediate_steps": len(step_dirs) > 0
                    })
        
        return jsonify({
            "user_id": user_id,
            "jobs": jobs
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500