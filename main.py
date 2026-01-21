#!/usr/bin/env python3


import argparse
import logging
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.api.routes import create_app
from src.database.file_handler import FileHandler
from src.database.mongo_handler import MongoHandler
from src.models.dataset import Dataset, DatasetFormat
from src.models.experiment import Experiment, ExperimentStatus
from src.models.result import Result

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load configuration from YAML file."""
    config_path = os.path.join(os.path.dirname(__file__), "config", "settings.yaml")

    return FileHandler.load_yaml(config_path)


def create_db_handler(config: dict) -> MongoHandler:
    """
    Create a MongoDB handler from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        MongoHandler: Configured MongoDB handler
    """
    db_config = config.get("database", {})

    return MongoHandler(
        host=db_config.get("host", "localhost"),
        port=db_config.get("port", 27017),
        database=db_config.get("name", "research_tracker"),
        username=db_config.get("username"),
        password=db_config.get("password"),
        connection_string=db_config.get("connection_string"),
    )


def create_file_handler(config: dict) -> FileHandler:
    """
    Create a file handler from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        FileHandler: Configured file handler
    """
    export_config = config.get("export", {})
    output_dir = export_config.get("output_directory", "exports")

    return FileHandler(output_dir=output_dir)


def run_demo():
    """
    Run an interactive demonstration of the application.

    This function demonstrates all the key features:
    - Creating models (OOP)
    - File I/O operations
    - MongoDB operations (if available)
    """
    print("\n" + "=" * 60)
    print("Research Experiment Tracker - Demo")
    print("=" * 60)

    # Load configuration
    config = load_config()
    print(f"\n✓ Loaded configuration from YAML")

    # Initialize handlers
    file_handler = create_file_handler(config)
    db_handler = create_db_handler(config)

    # Create sample experiments
    print("\n--- Creating Sample Experiments ---")

    experiments = []

    # Experiment 1: CNN for Image Classification
    exp1 = Experiment(
        name="CNN Image Classification",
        description="Testing ResNet50 architecture on satellite imagery for vehicle detection",
        author="Kamel",
        tags=["deep-learning", "computer-vision", "satellite-imagery"],
        parameters={
            "model": "ResNet50",
            "learning_rate": 0.001,
            "batch_size": 32,
            "epochs": 100,
        },
    )
    exp1.start()
    exp1.complete(
        metrics={
            "accuracy": 0.943,
            "precision": 0.912,
            "recall": 0.895,
            "f1_score": 0.903,
        }
    )
    experiments.append(exp1)
    print(f"  ✓ Created: {exp1}")

    # Experiment 2: LSTM for Sequence Prediction
    exp2 = Experiment(
        name="LSTM Sequence Prediction",
        description="Time series forecasting using LSTM networks",
        author="Kamel",
        tags=["deep-learning", "time-series", "lstm"],
        parameters={
            "model": "LSTM",
            "hidden_size": 128,
            "num_layers": 2,
            "dropout": 0.2,
        },
    )
    exp2.start()
    experiments.append(exp2)
    print(f"  ✓ Created: {exp2}")

    # Experiment 3: Transformer for NLP
    exp3 = Experiment(
        name="Transformer NLP Model",
        description="Fine-tuning BERT for text classification",
        author="Kamel",
        tags=["nlp", "transformers", "bert"],
        parameters={
            "model": "bert-base-uncased",
            "max_length": 512,
            "learning_rate": 2e-5,
        },
    )
    experiments.append(exp3)
    print(f"  ✓ Created: {exp3}")

    # Create a dataset
    print("\n--- Creating Sample Dataset ---")

    dataset = Dataset(
        name="Satellite Vehicle Dataset",
        description="High-resolution satellite images for vehicle detection",
        source="Custom Collection",
        format=DatasetFormat.IMAGES,
        size_mb=2500.0,
        num_samples=15000,
        features=["image", "bounding_box", "vehicle_type", "confidence"],
    )
    print(f"  ✓ Created: {dataset}")

    # Create results
    print("\n--- Creating Experiment Results ---")

    result = Result(
        experiment_id=exp1.id,
        run_number=1,
        metrics={"accuracy": 0.943, "loss": 0.087, "training_time_hours": 4.5},
        artifacts=["/models/resnet50_best.pt", "/logs/training.log"],
        duration_seconds=16200.0,
    )
    print(f"  ✓ Created result for {exp1.name}")

    # Export to different formats
    print("\n--- Exporting Data ---")

    # JSON Export
    json_path = file_handler.export_to_json(experiments, "demo_experiments.json")
    print(f"  ✓ Exported to JSON: {json_path}")

    # CSV Export
    csv_path = file_handler.export_to_csv(experiments, "demo_experiments.csv")
    print(f"  ✓ Exported to CSV: {csv_path}")

    # Excel Export
    try:
        xlsx_path = file_handler.export_to_excel(experiments, "demo_experiments.xlsx")
        print(f"  ✓ Exported to Excel: {xlsx_path}")
    except ImportError:
        print("  ⚠ Excel export skipped (openpyxl not installed)")

    # Generate summary report
    try:
        report_path = file_handler.generate_summary_report(
            experiments, "demo_summary_report.xlsx"
        )
        print(f"  ✓ Generated summary report: {report_path}")
    except ImportError:
        print("  ⚠ Summary report skipped (openpyxl not installed)")

    # MongoDB operations
    print("\n--- Database Operations ---")

    if db_handler.is_connected:
        # Insert experiments
        for exp in experiments:
            db_handler.insert_experiment(exp)
        print(f"  ✓ Inserted {len(experiments)} experiments to MongoDB")

        # Insert dataset
        db_handler.insert_dataset(dataset)
        print(f"  ✓ Inserted dataset to MongoDB")

        # Insert result
        db_handler.insert_result(result)
        print(f"  ✓ Inserted result to MongoDB")

        # Query experiments
        found = db_handler.find_experiments({"author": "Kamel"})
        print(f"  ✓ Found {len(found)} experiments by Kamel")

        # Get statistics
        stats = db_handler.get_statistics()
        print(f"  ✓ Database stats: {stats}")

        # Health check
        health = db_handler.health_check()
        print(f"  ✓ Health check: {health['status']}")
    else:
        print("  ⚠ MongoDB not connected (running in demo mode)")
        print("  ⚠ Data saved to files only")

    # Display summary
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print(f"\nExperiments created: {len(experiments)}")
    print(f"Datasets created: 1")
    print(f"Results created: 1")
    print(f"\nExport files available in: {file_handler._output_dir}/")
    print("\nTo run the REST API server: python main.py --api")
    print("=" * 60 + "\n")


def run_api(config: dict):
    """Run the REST API server."""
    print("\n" + "=" * 60)
    print("Starting Research Experiment Tracker API Server")
    print("=" * 60 + "\n")

    api_config = config.get("api", {})
    host = api_config.get("host", "0.0.0.0")
    port = api_config.get("port", 5000)
    debug = api_config.get("debug", True)

    app = create_app(config)

    print(f"API Documentation:")
    print(f"  GET    /api/health                - Health check")
    print(f"  GET    /api/stats                 - Database statistics")
    print(f"  GET    /api/experiments           - List experiments")
    print(f"  GET    /api/experiments/<id>      - Get experiment")
    print(f"  POST   /api/experiments           - Create experiment")
    print(f"  PUT    /api/experiments/<id>      - Update experiment")
    print(f"  DELETE /api/experiments/<id>      - Delete experiment")
    print(f"  GET    /api/experiments/export/<format> - Export data")
    print(f"  POST   /api/experiments/<id>/start     - Start experiment")
    print(f"  POST   /api/experiments/<id>/complete  - Complete experiment")
    print()
    print(f"Server starting at http://{host}:{port}")
    print()

    app.run(host=host, port=port, debug=debug)


def run_export(format_type: str, config: dict):
    """Export experiments to specified format."""
    print(f"\nExporting experiments to {format_type}...")

    db_handler = create_db_handler(config)
    file_handler = create_file_handler(config)

    if db_handler.is_connected:
        experiments = db_handler.find_experiments()

        if not experiments:
            print("No experiments found in database.")
            return

        if format_type == "json":
            path = file_handler.export_to_json(experiments)
        elif format_type == "csv":
            path = file_handler.export_to_csv(experiments)
        elif format_type == "xlsx":
            path = file_handler.export_to_excel(experiments)
        else:
            print(f"Unsupported format: {format_type}")
            return

        print(f"✓ Exported {len(experiments)} experiments to: {path}")
    else:
        print("Cannot connect to MongoDB. Please ensure MongoDB is running.")
        print("You can start MongoDB with: docker-compose up -d")


def run_health_check(config: dict):
    """Run a health check on the database connection."""
    print("\nRunning health check...")

    db_handler = create_db_handler(config)
    health = db_handler.health_check()

    if health["status"] == "healthy":
        print(f"✓ Database: {health['status']}")
        print(f"  Host: {health['host']}:{health['port']}")
        print(f"  Database: {health['database']}")

        stats = db_handler.get_statistics()
        print(f"  Experiments: {stats.get('experiments_count', 0)}")
        print(f"  Datasets: {stats.get('datasets_count', 0)}")
        print(f"  Results: {stats.get('results_count', 0)}")
    else:
        print(f"✗ Database: {health['status']}")
        print(f"  Message: {health.get('message', 'Unknown error')}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Research Experiment Tracker - Manage your research experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py              Run interactive demo
  python main.py --api        Start REST API server
  python main.py --export csv Export experiments to CSV
  python main.py --health     Check database connection
        """,
    )

    parser.add_argument("--api", action="store_true", help="Run the REST API server")

    parser.add_argument(
        "--export",
        type=str,
        choices=["json", "csv", "xlsx"],
        help="Export experiments to specified format",
    )

    parser.add_argument(
        "--health", action="store_true", help="Check database connection health"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/settings.yaml",
        help="Path to configuration file",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config()

    if args.api:
        run_api(config)
    elif args.export:
        run_export(args.export, config)
    elif args.health:
        run_health_check(config)
    else:
        run_demo()


if __name__ == "__main__":
    main()
