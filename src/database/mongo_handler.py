import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from pymongo import ASCENDING, DESCENDING, MongoClient
    from pymongo.collection import Collection
    from pymongo.database import Database
    from pymongo.errors import ConnectionFailure, DuplicateKeyError, PyMongoError

    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

from ..models.dataset import Dataset
from ..models.experiment import Experiment
from ..models.result import Result

# Configure logging
logger = logging.getLogger(__name__)


class MongoHandler:
    """
    MongoDB Handler - manages database connections and operations.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 27017,
        database: str = "research_tracker",
        username: Optional[str] = None,
        password: Optional[str] = None,
        connection_string: Optional[str] = None,
    ):
        """
        Initialize MongoDB connection.

        Args:
            host: MongoDB host address
            port: MongoDB port number
            database: Database name
            username: MongoDB username for authentication
            password: MongoDB password for authentication
            connection_string: Optional full connection string (overrides other params)
        """
        self._host = host
        self._port = port
        self._database_name = database
        self._username = username
        self._password = password
        self._connection_string = connection_string

        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None
        self._connected = False

        # Try to connect
        self.connect()

    def connect(self) -> bool:
        """
        Establish connection to MongoDB.

        Returns:
            bool: True if connection successful, False otherwise
        """
        if not PYMONGO_AVAILABLE:
            logger.warning("pymongo not installed. Running in mock mode.")
            self._connected = False
            return False

        try:
            if self._connection_string:
                # Use full connection string if provided
                self._client = MongoClient(
                    self._connection_string, serverSelectionTimeoutMS=5000
                )
            elif self._username and self._password:
                # Use authentication credentials
                self._client = MongoClient(
                    host=self._host,
                    port=self._port,
                    username=self._username,
                    password=self._password,
                    authSource=self._database_name,
                    serverSelectionTimeoutMS=5000,
                )
            else:
                # Connect without authentication
                self._client = MongoClient(
                    host=self._host, port=self._port, serverSelectionTimeoutMS=5000
                )

            # Test connection
            self._client.admin.command("ping")

            # Get database
            self._db = self._client[self._database_name]
            self._connected = True

            # Create indexes for better performance
            self._create_indexes()

            logger.info(f"Connected to MongoDB: {self._database_name}")
            return True

        except ConnectionFailure as e:
            logger.warning(f"Could not connect to MongoDB: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            self._connected = False
            return False

    def _create_indexes(self) -> None:
        """Create indexes for improved query performance."""
        if not self._connected or not self._db:
            return

        try:
            # Experiments indexes
            self._db.experiments.create_index("name")
            self._db.experiments.create_index("author")
            self._db.experiments.create_index("status")
            self._db.experiments.create_index("created_at")

            # Datasets indexes
            self._db.datasets.create_index("name")
            self._db.datasets.create_index("format")

            # Results indexes
            self._db.results.create_index("experiment_id")
            self._db.results.create_index("run_number")

            logger.info("Database indexes created successfully")
        except PyMongoError as e:
            logger.warning(f"Could not create indexes: {e}")

    @property
    def is_connected(self) -> bool:
        """Check if connected to database."""
        return self._connected

    def close(self) -> None:
        """Close the database connection."""
        if self._client:
            self._client.close()
            self._connected = False
            logger.info("MongoDB connection closed")

    # ==================== EXPERIMENT OPERATIONS ====================

    def insert_experiment(self, experiment: Experiment) -> Optional[str]:
        """
        Insert a new experiment into the database.

        Args:
            experiment: Experiment instance to insert

        Returns:
            str: Inserted document ID, or None if failed
        """
        if not self._connected:
            logger.warning("Not connected to database")
            return experiment.id  # Return local ID for mock mode

        try:
            result = self._db.experiments.insert_one(experiment.to_dict())
            logger.info(f"Inserted experiment: {experiment.id}")
            return str(result.inserted_id) if result.inserted_id else experiment.id
        except DuplicateKeyError:
            logger.error(f"Experiment with ID {experiment.id} already exists")
            return None
        except PyMongoError as e:
            logger.error(f"Failed to insert experiment: {e}")
            return None

    def find_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """
        Find an experiment by ID.

        Args:
            experiment_id: The experiment ID to find

        Returns:
            Experiment: Found experiment, or None if not found
        """
        if not self._connected:
            return None

        try:
            doc = self._db.experiments.find_one({"_id": experiment_id})
            if doc:
                return Experiment.from_dict(doc)
            return None
        except PyMongoError as e:
            logger.error(f"Failed to find experiment: {e}")
            return None

    def find_experiments(
        self,
        query: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        ascending: bool = False,
        limit: int = 100,
    ) -> List[Experiment]:
        """
        Find experiments matching a query.

        Args:
            query: MongoDB query dictionary
            sort_by: Field to sort by
            ascending: Sort order
            limit: Maximum number of results

        Returns:
            List[Experiment]: List of matching experiments
        """
        if not self._connected:
            return []

        try:
            query = query or {}
            sort_order = ASCENDING if ascending else DESCENDING

            cursor = (
                self._db.experiments.find(query).sort(sort_by, sort_order).limit(limit)
            )

            return [Experiment.from_dict(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"Failed to find experiments: {e}")
            return []

    def update_experiment(self, experiment_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an experiment.

        Args:
            experiment_id: ID of experiment to update
            updates: Dictionary of fields to update

        Returns:
            bool: True if successful
        """
        if not self._connected:
            return False

        try:
            updates["updated_at"] = datetime.now().isoformat()
            result = self._db.experiments.update_one(
                {"_id": experiment_id}, {"$set": updates}
            )
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Failed to update experiment: {e}")
            return False

    def delete_experiment(self, experiment_id: str) -> bool:
        """
        Delete an experiment.

        Args:
            experiment_id: ID of experiment to delete

        Returns:
            bool: True if successful
        """
        if not self._connected:
            return False

        try:
            result = self._db.experiments.delete_one({"_id": experiment_id})

            # Also delete associated results
            self._db.results.delete_many({"experiment_id": experiment_id})

            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Failed to delete experiment: {e}")
            return False

    # ==================== DATASET OPERATIONS ====================

    def insert_dataset(self, dataset: Dataset) -> Optional[str]:
        """Insert a new dataset."""
        if not self._connected:
            return dataset.id

        try:
            result = self._db.datasets.insert_one(dataset.to_dict())
            logger.info(f"Inserted dataset: {dataset.id}")
            return str(result.inserted_id) if result.inserted_id else dataset.id
        except PyMongoError as e:
            logger.error(f"Failed to insert dataset: {e}")
            return None

    def find_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Find a dataset by ID."""
        if not self._connected:
            return None

        try:
            doc = self._db.datasets.find_one({"_id": dataset_id})
            if doc:
                return Dataset.from_dict(doc)
            return None
        except PyMongoError as e:
            logger.error(f"Failed to find dataset: {e}")
            return None

    def find_datasets(
        self, query: Optional[Dict[str, Any]] = None, limit: int = 100
    ) -> List[Dataset]:
        """Find datasets matching a query."""
        if not self._connected:
            return []

        try:
            query = query or {}
            cursor = self._db.datasets.find(query).limit(limit)
            return [Dataset.from_dict(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"Failed to find datasets: {e}")
            return []

    def update_dataset(self, dataset_id: str, updates: Dict[str, Any]) -> bool:
        """Update a dataset."""
        if not self._connected:
            return False

        try:
            updates["updated_at"] = datetime.now().isoformat()
            result = self._db.datasets.update_one(
                {"_id": dataset_id}, {"$set": updates}
            )
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(f"Failed to update dataset: {e}")
            return False

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset."""
        if not self._connected:
            return False

        try:
            result = self._db.datasets.delete_one({"_id": dataset_id})
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Failed to delete dataset: {e}")
            return False

    # ==================== RESULT OPERATIONS ====================

    def insert_result(self, result: Result) -> Optional[str]:
        """Insert a new result."""
        if not self._connected:
            return result.id

        try:
            db_result = self._db.results.insert_one(result.to_dict())
            logger.info(f"Inserted result: {result.id}")
            return str(db_result.inserted_id) if db_result.inserted_id else result.id
        except PyMongoError as e:
            logger.error(f"Failed to insert result: {e}")
            return None

    def find_result(self, result_id: str) -> Optional[Result]:
        """Find a result by ID."""
        if not self._connected:
            return None

        try:
            doc = self._db.results.find_one({"_id": result_id})
            if doc:
                return Result.from_dict(doc)
            return None
        except PyMongoError as e:
            logger.error(f"Failed to find result: {e}")
            return None

    def find_results_for_experiment(self, experiment_id: str) -> List[Result]:
        """Find all results for an experiment."""
        if not self._connected:
            return []

        try:
            cursor = self._db.results.find({"experiment_id": experiment_id}).sort(
                "run_number", ASCENDING
            )
            return [Result.from_dict(doc) for doc in cursor]
        except PyMongoError as e:
            logger.error(f"Failed to find results: {e}")
            return []

    def delete_result(self, result_id: str) -> bool:
        """Delete a result."""
        if not self._connected:
            return False

        try:
            result = self._db.results.delete_one({"_id": result_id})
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(f"Failed to delete result: {e}")
            return False

    def delete_results_for_experiment(self, experiment_id: str) -> int:
        """Delete all results for an experiment."""
        if not self._connected:
            return 0

        try:
            result = self._db.results.delete_many({"experiment_id": experiment_id})
            return result.deleted_count
        except PyMongoError as e:
            logger.error(f"Failed to delete results: {e}")
            return 0

    # ==================== UTILITY METHODS ====================

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        if not self._connected:
            return {"connected": False}

        try:
            return {
                "connected": True,
                "database": self._database_name,
                "experiments_count": self._db.experiments.count_documents({}),
                "datasets_count": self._db.datasets.count_documents({}),
                "results_count": self._db.results.count_documents({}),
            }
        except PyMongoError as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"connected": True, "error": str(e)}

    def clear_all(self) -> bool:
        """Clear all collections. Use with caution!"""
        if not self._connected:
            return False

        try:
            self._db.experiments.delete_many({})
            self._db.datasets.delete_many({})
            self._db.results.delete_many({})
            logger.warning("All collections cleared")
            return True
        except PyMongoError as e:
            logger.error(f"Failed to clear collections: {e}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the database connection."""
        if not self._connected:
            return {"status": "disconnected", "message": "Not connected to MongoDB"}

        try:
            # Ping the database
            self._client.admin.command("ping")

            return {
                "status": "healthy",
                "database": self._database_name,
                "host": self._host,
                "port": self._port,
            }
        except PyMongoError as e:
            return {"status": "unhealthy", "message": str(e)}

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        """String representation."""
        status = "connected" if self._connected else "disconnected"
        return f"MongoHandler(database='{self._database_name}', status='{status}')"
