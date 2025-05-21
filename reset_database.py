"""Utility script to drop and recreate all database tables."""

from app import app, db

# Import models so that SQLAlchemy is aware of them
import models


def reset_database(seed: bool = False) -> None:
    """Drop all tables and recreate them.

    Args:
        seed: When True, populate tables with initial seed data.
    """
    with app.app_context():
        db.drop_all()
        db.create_all()
        if seed:
            from seed_data import create_seed_data
            create_seed_data(app)
        db.session.commit()
        print("Database reset complete." + (" Seed data loaded." if seed else ""))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Reset the application's database")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Load seed data after recreating tables",
    )
    args = parser.parse_args()

    reset_database(seed=args.seed)
