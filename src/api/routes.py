import logging
import os
from typing import Optional

from flask import Blueprint, Flask, jsonify, request, send_file

from ..database.file_handler import FileHandler
from ..database.mongo_handler import MongoHandler
from ..models.dataset import Dataset, DatasetFormat
from ..models.experiment import Experiment, ExperimentStatus
from ..models.result import Result

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

    Args:
        config: Optional configuration dictionary

    Returns:
        Flask: Configured Flask application
    """
    global db_handler, file_handler

    app = Flask(__name__)

    # Default configuration
    app.config.update({"JSON_SORT_KEYS": False, "JSONIFY_PRETTYPRINT_REGULAR": True})

    # Apply custom config if provided
    if config:
        app.config.update(config)

    # Initialize database handler with authentication support
    db_config = config.get("database", {}) if config else {}
    db_handler = MongoHandler(
        host=db_config.get("host", "localhost"),
        port=db_config.get("port", 27017),
        database=db_config.get("name", "research_tracker"),
        username=db_config.get("username"),
        password=db_config.get("password"),
        connection_string=db_config.get("connection_string"),
    )

    # Initialize file handler
    export_config = config.get("export", {}) if config else {}
    export_dir = export_config.get("output_directory", "exports")
    file_handler = FileHandler(output_dir=export_dir)

    # Register blueprint
    app.register_blueprint(api_bp)

    # Register error handlers
    register_error_handlers(app)

    # Register root route
    @app.route("/")
    def index():
        return jsonify(
            {
                "name": "Research Experiment Tracker API",
                "version": "1.0.0",
                "endpoints": {
                    "health": "/api/health",
                    "stats": "/api/stats",
                    "experiments": "/api/experiments",
                    "datasets": "/api/datasets",
                },
            }
        )

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
    db_health = db_handler.health_check() if db_handler else {"status": "unknown"}

    return jsonify(
        {
            "status": "healthy",
            "service": "Research Experiment Tracker API",
            "version": "1.0.0",
            "database": db_health,
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
        - status: Filter by status (planned, running, completed, failed, paused)
        - author: Filter by author name
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
            # Also get associated results
            results = db_handler.find_results_for_experiment(experiment_id)
            exp_dict = experiment.to_dict()
            exp_dict["results"] = [r.to_dict() for r in results]
            return jsonify(exp_dict)

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
        # Check if experiment exists
        experiment = db_handler.find_experiment(experiment_id)
        if not experiment:
            return jsonify(
                {
                    "error": "Not Found",
                    "message": f"Experiment {experiment_id} not found",
                }
            ), 404

        success = db_handler.delete_experiment(experiment_id)
        if success:
            return jsonify(
                {"message": f"Experiment {experiment_id} deleted successfully"}
            )

    return jsonify(
        {"error": "Delete Failed", "message": "Could not delete experiment"}
    ), 500


# ==================== EXPERIMENT ACTIONS ====================


@api_bp.route("/experiments/<experiment_id>/start", methods=["POST"])
def start_experiment(experiment_id: str):
    """Mark an experiment as running."""
    if db_handler:
        experiment = db_handler.find_experiment(experiment_id)
        if not experiment:
            return jsonify({"error": "Not Found"}), 404

        success = db_handler.update_experiment(
            experiment_id, {"status": ExperimentStatus.RUNNING.value}
        )
        if success:
            updated = db_handler.find_experiment(experiment_id)
            return jsonify(updated.to_dict())

    return jsonify({"error": "Update Failed"}), 500


@api_bp.route("/experiments/<experiment_id>/complete", methods=["POST"])
def complete_experiment(experiment_id: str):
    """Mark an experiment as completed with optional metrics."""
    data = request.get_json() or {}

    if db_handler:
        experiment = db_handler.find_experiment(experiment_id)
        if not experiment:
            return jsonify({"error": "Not Found"}), 404

        updates = {"status": ExperimentStatus.COMPLETED.value}
        if "metrics" in data:
            updates["metrics"] = data["metrics"]

        success = db_handler.update_experiment(experiment_id, updates)
        if success:
            updated = db_handler.find_experiment(experiment_id)
            return jsonify(updated.to_dict())

    return jsonify({"error": "Update Failed"}), 500


@api_bp.route("/experiments/<experiment_id>/fail", methods=["POST"])
def fail_experiment(experiment_id: str):
    """Mark an experiment as failed with optional error message."""
    data = request.get_json() or {}

    if db_handler:
        experiment = db_handler.find_experiment(experiment_id)
        if not experiment:
            return jsonify({"error": "Not Found"}), 404

        updates = {"status": ExperimentStatus.FAILED.value}
        if "error" in data:
            metrics = experiment.metrics
            metrics["error"] = data["error"]
            updates["metrics"] = metrics

        success = db_handler.update_experiment(experiment_id, updates)
        if success:
            updated = db_handler.find_experiment(experiment_id)
            return jsonify(updated.to_dict())

    return jsonify({"error": "Update Failed"}), 500


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

    # Get filter parameters
    status = request.args.get("status")
    author = request.args.get("author")

    query = {}
    if status:
        query["status"] = status
    if author:
        query["author"] = author

    # Get experiments
    experiments = []
    if db_handler:
        experiments = db_handler.find_experiments(query=query, limit=1000)

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


# ==================== DATASET ROUTES ====================


@api_bp.route("/datasets", methods=["GET"])
def list_datasets():
    """List all datasets."""
    limit = request.args.get("limit", 100, type=int)

    if db_handler:
        datasets = db_handler.find_datasets(limit=limit)
        return jsonify(
            {"datasets": [ds.to_dict() for ds in datasets], "count": len(datasets)}
        )

    return jsonify({"datasets": [], "count": 0})


@api_bp.route("/datasets/<dataset_id>", methods=["GET"])
def get_dataset(dataset_id: str):
    """Get a specific dataset by ID."""
    if db_handler:
        dataset = db_handler.find_dataset(dataset_id)
        if dataset:
            return jsonify(dataset.to_dict())

    return jsonify(
        {"error": "Not Found", "message": f"Dataset {dataset_id} not found"}
    ), 404


@api_bp.route("/datasets", methods=["POST"])
def create_dataset():
    """Create a new dataset."""
    data = request.get_json()

    if not data:
        return jsonify(
            {"error": "Bad Request", "message": "Request body must be JSON"}
        ), 400

    if "name" not in data:
        return jsonify(
            {"error": "Bad Request", "message": "Dataset name is required"}
        ), 400

    try:
        dataset = Dataset(
            name=data["name"],
            description=data.get("description", ""),
            source=data.get("source", ""),
            format=data.get("format", "csv"),
            size_mb=data.get("size_mb", 0.0),
            num_samples=data.get("num_samples", 0),
            features=data.get("features", []),
            path=data.get("path", ""),
            metadata=data.get("metadata", {}),
        )

        if db_handler:
            ds_id = db_handler.insert_dataset(dataset)
            if ds_id:
                logger.info(f"Created dataset: {ds_id}")
                return jsonify(dataset.to_dict()), 201

        return jsonify(dataset.to_dict()), 201

    except ValueError as e:
        return jsonify({"error": "Validation Error", "message": str(e)}), 400


@api_bp.route("/datasets/<dataset_id>", methods=["PUT"])
def update_dataset(dataset_id: str):
    """Update a dataset."""
    data = request.get_json()

    if not data:
        return jsonify(
            {"error": "Bad Request", "message": "Request body must be JSON"}
        ), 400

    if db_handler:
        dataset = db_handler.find_dataset(dataset_id)
        if not dataset:
            return jsonify(
                {"error": "Not Found", "message": f"Dataset {dataset_id} not found"}
            ), 404

        success = db_handler.update_dataset(dataset_id, data)
        if success:
            updated = db_handler.find_dataset(dataset_id)
            return jsonify(updated.to_dict())

    return jsonify({"error": "Update Failed"}), 500


@api_bp.route("/datasets/<dataset_id>", methods=["DELETE"])
def delete_dataset(dataset_id: str):
    """Delete a dataset."""
    if db_handler:
        dataset = db_handler.find_dataset(dataset_id)
        if not dataset:
            return jsonify(
                {"error": "Not Found", "message": f"Dataset {dataset_id} not found"}
            ), 404

        success = db_handler.delete_dataset(dataset_id)
        if success:
            return jsonify({"message": f"Dataset {dataset_id} deleted successfully"})

    return jsonify({"error": "Delete Failed"}), 500


# ==================== RESULT ROUTES ====================


@api_bp.route("/experiments/<experiment_id>/results", methods=["GET"])
def list_results(experiment_id: str):
    """List all results for an experiment."""
    if db_handler:
        results = db_handler.find_results_for_experiment(experiment_id)
        return jsonify(
            {"results": [r.to_dict() for r in results], "count": len(results)}
        )

    return jsonify({"results": [], "count": 0})


@api_bp.route("/experiments/<experiment_id>/results", methods=["POST"])
def create_result(experiment_id: str):
    """Create a new result for an experiment."""
    data = request.get_json()

    if not data:
        return jsonify(
            {"error": "Bad Request", "message": "Request body must be JSON"}
        ), 400

    # Verify experiment exists
    if db_handler:
        experiment = db_handler.find_experiment(experiment_id)
        if not experiment:
            return jsonify(
                {
                    "error": "Not Found",
                    "message": f"Experiment {experiment_id} not found",
                }
            ), 404

    try:
        result = Result(
            experiment_id=experiment_id,
            run_number=data.get("run_number", 1),
            metrics=data.get("metrics", {}),
            artifacts=data.get("artifacts", []),
            notes=data.get("notes", ""),
            duration_seconds=data.get("duration_seconds", 0.0),
        )

        if db_handler:
            result_id = db_handler.insert_result(result)
            if result_id:
                logger.info(f"Created result: {result_id}")
                return jsonify(result.to_dict()), 201

        return jsonify(result.to_dict()), 201

    except ValueError as e:
        return jsonify({"error": "Validation Error", "message": str(e)}), 400


# ==================== UTILITY FUNCTIONS ====================


def run_api(host: str = "0.0.0.0", port: int = 5000, debug: bool = True):
    """Run the Flask API server."""
    app = create_app()
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_api()
