// mongo-init.js
// This script runs when the container is first created

db = db.getSiblingDB("research_tracker");

// Create collections
db.createCollection("experiments");
db.createCollection("datasets");
db.createCollection("results");

// Create indexes for better performance
db.experiments.createIndex({ name: 1 });
db.experiments.createIndex({ author: 1 });
db.experiments.createIndex({ status: 1 });
db.experiments.createIndex({ created_at: -1 });

db.datasets.createIndex({ name: 1 });
db.datasets.createIndex({ format: 1 });

db.results.createIndex({ experiment_id: 1 });
db.results.createIndex({ run_number: 1 });

// Create application user
db.createUser({
  user: "researcher",
  pwd: "researcher123",
  roles: [{ role: "readWrite", db: "research_tracker" }],
});

print("Database initialized successfully!");
