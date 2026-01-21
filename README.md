# Research Tracker

A Python application for tracking research experiments, datasets, and results.

## Project Structure

```
research_tracker/
├── README.md                 # Project documentation
├── requirements.txt          # Python dependencies
├── .gitignore               # Git ignore rules
├── config/
│   └── settings.yaml        # Application configuration
├── src/
│   ├── models/              # OOP data models
│   │   ├── base.py          # Abstract base class
│   │   ├── experiment.py    # Experiment class
│   │   ├── dataset.py       # Dataset class
│   │   └── result.py        # Result class
│   ├── database/            # Data persistence layer
│   │   ├── mongo_handler.py # MongoDB CRUD operations
│   │   └── file_handler.py  # File I/O operations
│   ├── api/                 # REST API layer
│   │   └── routes.py        # Flask endpoints
│   └── utils/               # Utility modules
│       └── validators.py    # Input validation
├── tests/                   # Unit tests
│   ├── test_models.py
│   └── test_database.py
└── main.py
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Configuration

Edit `config/settings.yaml` to configure the application.
