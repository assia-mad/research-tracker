"""Main entry point for the Research Tracker application."""

from src.api.routes import create_app


def main():
    """Initialize and run the application."""
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
