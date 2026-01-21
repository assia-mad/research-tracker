import logging
import os
from typing import Optional

from flask import Blueprint, Flask, jsonify, request, send_file

from ..database.file_handler import FileHandler
from ..database.mongo_handler import MongoHandler
from ..models.experiment import Experiment, ExperimentStatus

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint for API routes
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Global handlers (initialized in create_app)
db_handler: Optional[MongoHandler] = None
file_handler: Optional[FileHandler] = None


def create_app(config: dict = None) -> Flask:
    """
    Create and configure the Flask application.
    """
    global db_handler, file_handler

    app = Flask(__name__)

    # Default configuration
    app.config.update({"JSON_SORT_KEYS": False, "JSONIFY_PRETTYPRINT_REGULAR": True})

    # Apply custom config if provided
    if config:
        app.config.update(config)

    # Initialize handlers
    db_config = config.get("database", {}) if config else {}
    db_handler = MongoHandler(
        host=db_config.get("host", "localhost"),
        port=db_config.get("port", 27017),
        database=db_config.get("name", "research_tracker"),
    )

    export_dir = (
        config.get("export", {}).get("output_directory", "exports")
        if config
        else "exports"
    )
    file_handler = FileHandler(output_dir=export_dir)

    # Register blueprint
    app.register_blueprint(api_bp)

    # Register error handlers
    register_error_handlers(app)

    logger.info("Flask application created successfully")
    return app


def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the application."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad Request", "message": str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify(
            {"error": "Not Found", "message": "The requested resource was not found"}
        ), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify(
            {
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
            }
        ), 500


# ==================== HEALTH & INFO ROUTES ====================


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy",
            "service": "Research Experiment Tracker API",
            "version": "1.0.0",
        }
    )


@api_bp.route("/stats", methods=["GET"])
def get_statistics():
    """Get database statistics."""
    if db_handler:
        stats = db_handler.get_statistics()
        return jsonify(stats)
    return jsonify({"error": "Database not connected"}), 503


# ==================== EXPERIMENT ROUTES ====================


@api_bp.route("/experiments", methods=["GET"])
def list_experiments():
    """
    List all experiments.

    Query Parameters:
        - status: Filter by status
        - author: Filter by author
        - limit: Maximum number of results (default: 100)
        - sort: Sort field (default: created_at)
        - order: Sort order (asc/desc, default: desc)

    Returns:
        JSON array of experiments
    """
    # Parse query parameters
    status = request.args.get("status")
    author = request.args.get("author")
    limit = request.args.get("limit", 100, type=int)
    sort_by = request.args.get("sort", "created_at")
    order = request.args.get("order", "desc")

    # Build query
    query = {}
    if status:
        query["status"] = status
    if author:
        query["author"] = author

    # Fetch experiments
    if db_handler:
        experiments = db_handler.find_experiments(
            query=query, sort_by=sort_by, ascending=(order == "asc"), limit=limit
        )
        return jsonify(
            {
                "experiments": [exp.to_dict() for exp in experiments],
                "count": len(experiments),
            }
        )

    return jsonify({"experiments": [], "count": 0})


@api_bp.route("/experiments/<experiment_id>", methods=["GET"])
def get_experiment(experiment_id: str):
    """
    Get a specific experiment by ID.

    Args:
        experiment_id: The experiment ID

    Returns:
        JSON representation of the experiment
    """
    if db_handler:
        experiment = db_handler.find_experiment(experiment_id)
        if experiment:
            return jsonify(experiment.to_dict())

    return jsonify(
        {"error": "Not Found", "message": f"Experiment {experiment_id} not found"}
    ), 404


@api_bp.route("/experiments", methods=["POST"])
def create_experiment():
    """
    Create a new experiment.

    Request Body:
        JSON object with experiment fields:
        - name (required): Experiment name
        - description: Description
        - author: Author name
        - tags: List of tags
        - parameters: Dictionary of parameters

    Returns:
        JSON representation of created experiment
    """
    data = request.get_json()

    if not data:
        return jsonify(
            {"error": "Bad Request", "message": "Request body must be JSON"}
        ), 400

    if "name" not in data:
        return jsonify(
            {"error": "Bad Request", "message": "Experiment name is required"}
        ), 400

    try:
        # Create experiment from request data
        experiment = Experiment(
            name=data["name"],
            description=data.get("description", ""),
            author=data.get("author", ""),
            status=data.get("status", "planned"),
            tags=data.get("tags", []),
            parameters=data.get("parameters", {}),
            metrics=data.get("metrics", {}),
            dataset_id=data.get("dataset_id"),
        )

        # Save to database
        if db_handler:
            exp_id = db_handler.insert_experiment(experiment)
            if exp_id:
                logger.info(f"Created experiment: {exp_id}")
                return jsonify(experiment.to_dict()), 201

        # Return experiment even if not saved to DB
        return jsonify(experiment.to_dict()), 201

    except ValueError as e:
        return jsonify({"error": "Validation Error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating experiment: {e}")
        return jsonify({"error": "Internal Error", "message": str(e)}), 500


@api_bp.route("/experiments/<experiment_id>", methods=["PUT"])
def update_experiment(experiment_id: str):
    """
    Update an existing experiment.

    Args:
        experiment_id: The experiment ID

    Request Body:
        JSON object with fields to update

    Returns:
        JSON representation of updated experiment
    """
    data = request.get_json()

    if not data:
        return jsonify(
            {"error": "Bad Request", "message": "Request body must be JSON"}
        ), 400

    if db_handler:
        # Check if experiment exists
        experiment = db_handler.find_experiment(experiment_id)
        if not experiment:
            return jsonify(
                {
                    "error": "Not Found",
                    "message": f"Experiment {experiment_id} not found",
                }
            ), 404

        # Update fields
        success = db_handler.update_experiment(experiment_id, data)

        if success:
            updated = db_handler.find_experiment(experiment_id)
            return jsonify(updated.to_dict())

    return jsonify(
        {"error": "Update Failed", "message": "Could not update experiment"}
    ), 500


@api_bp.route("/experiments/<experiment_id>", methods=["DELETE"])
def delete_experiment(experiment_id: str):
    """
    Delete an experiment.

    Args:
        experiment_id: The experiment ID

    Returns:
        Success message
    """
    if db_handler:
        success = db_handler.delete_experiment(experiment_id)
        if success:
            return jsonify(
                {"message": f"Experiment {experiment_id} deleted successfully"}
            )

    return jsonify(
        {"error": "Not Found", "message": f"Experiment {experiment_id} not found"}
    ), 404


# ==================== EXPORT ROUTES ====================


@api_bp.route("/experiments/export/<format_type>", methods=["GET"])
def export_experiments(format_type: str):
    """
    Export experiments to specified format.

    Args:
        format_type: Export format (json, csv, xlsx)

    Returns:
        File download or JSON response
    """
    if format_type not in ["json", "csv", "xlsx"]:
        return jsonify(
            {
                "error": "Bad Request",
                "message": f"Unsupported format: {format_type}. Use json, csv, or xlsx.",
            }
        ), 400

    # Get experiments
    experiments = []
    if db_handler:
        experiments = db_handler.find_experiments(limit=1000)

    if not experiments:
        return jsonify({"error": "No Data", "message": "No experiments to export"}), 404

    try:
        if file_handler:
            filename = f"experiments_export.{format_type}"

            if format_type == "json":
                filepath = file_handler.export_to_json(experiments, filename)
            elif format_type == "csv":
                filepath = file_handler.export_to_csv(experiments, filename)
            elif format_type == "xlsx":
                filepath = file_handler.export_to_excel(experiments, filename)

            # Return file for download
            return send_file(filepath, as_attachment=True, download_name=filename)

        return jsonify(
            {"error": "Export Failed", "message": "File handler not available"}
        ), 500

    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({"error": "Export Failed", "message": str(e)}), 500


# ==================== EXPERIMENT ACTIONS ====================


@api_bp.route("/experiments/<experiment_id>/start", methods=["POST"])
def start_experiment(experiment_id: str):
    """Mark an experiment as running."""
    if db_handler:
        success = db_handler.update_experiment(
            experiment_id, {"status": ExperimentStatus.RUNNING.value}
        )
        if success:
            experiment = db_handler.find_experiment(experiment_id)
            return jsonify(experiment.to_dict())

    return jsonify({"error": "Not Found"}), 404


@api_bp.route("/experiments/<experiment_id>/complete", methods=["POST"])
def complete_experiment(experiment_id: str):
    """Mark an experiment as completed with optional metrics."""
    data = request.get_json() or {}

    if db_handler:
        updates = {"status": ExperimentStatus.COMPLETED.value}
        if "metrics" in data:
            updates["metrics"] = data["metrics"]

        success = db_handler.update_experiment(experiment_id, updates)
        if success:
            experiment = db_handler.find_experiment(experiment_id)
            return jsonify(experiment.to_dict())

    return jsonify({"error": "Not Found"}), 404


# Convenience function for running the API
def run_api(host: str = "0.0.0.0", port: int = 5000, debug: bool = True):
    """Run the Flask API server."""
    app = create_app()
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_api()
