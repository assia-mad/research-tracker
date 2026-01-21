import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from src.api.routes import create_app
from src.database.file_handler import FileHandler
from src.database.mongo_handler import MongoHandler
from src.models.dataset import Dataset, DatasetFormat
from src.models.experiment import Experiment, ExperimentStatus
from src.models.result import Result

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "config", "settings.yaml")
    return FileHandler.load_yaml(config_path)


def run_demo():
    print("\n" + "=" * 60)
    print("Research Experiment Tracker - Demo")
    print("=" * 60)

    config = load_config()
    print(f"\n✓ Loaded configuration from YAML")

    file_handler = FileHandler(
        output_dir=config.get("export", {}).get("output_directory", "exports")
    )
    db_handler = MongoHandler(
        host=config.get("database", {}).get("host", "localhost"),
        port=config.get("database", {}).get("port", 27017),
        database=config.get("database", {}).get("name", "research_tracker"),
    )

    print("\n--- Creating Sample Experiments ---")
    experiments = []

    exp1 = Experiment(
        name="CNN Image Classification",
        description="Testing ResNet50 on satellite imagery",
        author="Kamel",
        tags=["deep-learning", "computer-vision"],
    )
    exp1.start()
    exp1.complete({"accuracy": 0.943, "f1_score": 0.903})
    experiments.append(exp1)
    print(f"  ✓ Created: {exp1}")

    exp2 = Experiment(
        name="LSTM Sequence Prediction",
        author="Kamel",
        tags=["deep-learning", "time-series"],
    )
    exp2.start()
    experiments.append(exp2)
    print(f"  ✓ Created: {exp2}")

    print("\n--- Exporting Data ---")
    json_path = file_handler.export_to_json(experiments, "demo_experiments.json")
    print(f"  ✓ Exported to JSON: {json_path}")

    csv_path = file_handler.export_to_csv(experiments, "demo_experiments.csv")
    print(f"  ✓ Exported to CSV: {csv_path}")

    try:
        xlsx_path = file_handler.export_to_excel(experiments, "demo_experiments.xlsx")
        print(f"  ✓ Exported to Excel: {xlsx_path}")
    except ImportError:
        print("  ⚠ Excel export skipped (openpyxl not installed)")

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)


def run_api(config: dict):
    print("\nStarting REST API Server...")
    api_config = config.get("api", {})
    app = create_app(config)
    app.run(
        host=api_config.get("host", "0.0.0.0"),
        port=api_config.get("port", 5000),
        debug=api_config.get("debug", True),
    )


def main():
    parser = argparse.ArgumentParser(description="Research Experiment Tracker")
    parser.add_argument("--api", action="store_true", help="Run REST API server")
    parser.add_argument("--export", type=str, choices=["json", "csv", "xlsx"])
    args = parser.parse_args()

    config = load_config()

    if args.api:
        run_api(config)
    else:
        run_demo()


if __name__ == "__main__":
    main()
