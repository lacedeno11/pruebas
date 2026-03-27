"""Initial data seeding for PEI Platform database"""

import random
import logging
from datetime import datetime, timedelta

from backend.database.session import SessionLocal
from backend.database.models import Cuadrilla, OT, LogAgente
from backend.utils.constants import OT_STATUS, PROJECT_TYPES, CUADRILLA_TYPES

logger = logging.getLogger(__name__)


def seed_cuadrillas(db):
    """
    Seed database with 10 sample cuadrillas.

    Creates 5 Principal cuadrillas with capacity 10 and 5 Reserva cuadrillas with capacity 8,
    with realistic Ecuador centroids around Quito.

    Args:
        db: Database session
    """
    logger.info("Seeding cuadrillas...")

    cuadrillas = []

    # Create 5 Principal cuadrillas
    for i in range(1, 6):
        cuadrilla = Cuadrilla(
            name=f"Cuadrilla Norte {i}",
            type=CUADRILLA_TYPES["PRINCIPAL"],
            capacity=10,
            last_centroid_lat=round(random.uniform(-0.1800, -0.1900), 6),
            last_centroid_long=round(random.uniform(-78.4600, -78.5000), 6),
            active=True,
            created_at=datetime.now(),
        )
        cuadrillas.append(cuadrilla)
        logger.debug(f"Created Principal cuadrilla: {cuadrilla.name}")

    # Create 5 Reserva cuadrillas
    for i in range(1, 6):
        cuadrilla = Cuadrilla(
            name=f"Cuadrilla Reserva {i}",
            type=CUADRILLA_TYPES["RESERVA"],
            capacity=8,
            last_centroid_lat=round(random.uniform(-0.1800, -0.1900), 6),
            last_centroid_long=round(random.uniform(-78.4600, -78.5000), 6),
            active=False,  # Reserva teams start as inactive
            created_at=datetime.now(),
        )
        cuadrillas.append(cuadrilla)
        logger.debug(f"Created Reserva cuadrilla: {cuadrilla.name}")

    db.add_all(cuadrillas)
    db.commit()
    logger.info(f"Successfully seeded {len(cuadrillas)} cuadrillas")

    return cuadrillas


def seed_ots(db):
    """
    Seed database with 50 sample OTs distributed across all statuses.

    Distribution:
    - 10 PREPLANIFICADA
    - 15 PLANIFICADA
    - 12 ASIGNADO_TAREA
    - 8 DETENIDA
    - 3 ANULADA
    - 2 FINALIZADA

    OTs have realistic Ecuador coordinates and timestamps spanning the last 60 days.

    Args:
        db: Database session

    Returns:
        List of created OT objects
    """
    logger.info("Seeding OTs...")

    ots = []
    status_distribution = {
        OT_STATUS["PREPLANIFICADA"]: 10,
        OT_STATUS["PLANIFICADA"]: 15,
        OT_STATUS["ASIGNADO_TAREA"]: 12,
        OT_STATUS["DETENIDA"]: 8,
        OT_STATUS["ANULADA"]: 3,
        OT_STATUS["FINALIZADA"]: 2,
    }

    ot_counter = 0

    for status, count in status_distribution.items():
        for i in range(count):
            ot_counter += 1
            external_id = f"OT-2024-{1000 + ot_counter:04d}"

            # Random timestamp within last 60 days
            days_ago = random.randint(0, 60)
            created_at = datetime.now() - timedelta(days=days_ago)
            updated_at = created_at + timedelta(
                hours=random.randint(0, 48)
            )
            last_status_change = updated_at

            # Random project type
            project_type = random.choice(
                [
                    PROJECT_TYPES["PUBLICO"],
                    PROJECT_TYPES["PRIVADO"],
                    PROJECT_TYPES["TERCERIZADO"],
                ]
            )

            # Realistic Ecuador coordinates (Quito area)
            lat = round(random.uniform(-0.1800, -0.2200), 6)
            long = round(random.uniform(-78.4600, -78.5200), 6)

            # Random cliente and login IDs
            cliente_id = f"CLI-{random.randint(100, 999)}"
            login_id = f"LOG-{random.randint(10000, 99999)}"

            # For DETENIDA status, include detalle_detencion
            detalle_detencion = None
            if status == OT_STATUS["DETENIDA"]:
                detalle_detencion = random.choice(
                    [
                        "Esperando autorización del cliente",
                        "Falta de materiales",
                        "Inclemencia del tiempo",
                        "Reprogramación solicitada",
                        "En espera de documento",
                    ]
                )

            ot = OT(
                external_id=external_id,
                cliente_id=cliente_id,
                login_id=login_id,
                status=status,
                project_type=project_type,
                lat=lat,
                long=long,
                created_at=created_at,
                updated_at=updated_at,
                last_status_change=last_status_change,
                cuadrilla_id=None,  # Will be assigned during planning
                detalle_detencion=detalle_detencion,
            )
            ots.append(ot)
            logger.debug(
                f"Created OT: {external_id} (Status: {status}, "
                f"Project: {project_type})"
            )

    db.add_all(ots)
    db.commit()
    logger.info(f"Successfully seeded {len(ots)} OTs")

    return ots


def seed_logs(db):
    """
    Seed database with sample log entries for audit trail.

    Args:
        db: Database session

    Returns:
        List of created log entries
    """
    logger.info("Seeding log entries...")

    logs = []

    # Get all OTs for logging
    ots = db.query(OT).all()

    for ot in ots[:20]:  # Create logs for first 20 OTs
        # Create 1-3 log entries per OT
        num_logs = random.randint(1, 3)

        for i in range(num_logs):
            log = LogAgente(
                ot_id=ot.id,
                agente_name=random.choice(
                    [
                        "OTS_Agent",
                        "Planificacion_Agent",
                        "Gobernanza_Agent",
                        "Router_Agent",
                    ]
                ),
                accion=random.choice(
                    [
                        "ingestion",
                        "validation",
                        "planning",
                        "assignment",
                        "status_update",
                        "inactivity_check",
                    ]
                ),
                resultado=random.choice(
                    ["SUCCESS", "WARNING", "ERROR"]
                ),
                raw_llm_response=None,
                metadata={
                    "phase": random.choice(
                        ["phase_1", "phase_2", "phase_3"]
                    ),
                    "details": "Sample log entry",
                },
                timestamp=datetime.now() - timedelta(hours=random.randint(0, 24)),
            )
            logs.append(log)
            logger.debug(
                f"Created log entry for OT {ot.external_id}: "
                f"{log.accion} - {log.resultado}"
            )

    db.add_all(logs)
    db.commit()
    logger.info(f"Successfully seeded {len(logs)} log entries")

    return logs


def main():
    """
    Run all seeding functions in a transaction.

    Rolls back if any error occurs.
    """
    db = SessionLocal()

    try:
        logger.info("Starting database seeding...")

        # Check if data already exists
        existing_cuadrillas = db.query(Cuadrilla).count()
        if existing_cuadrillas > 0:
            logger.warning(
                f"Database already contains {existing_cuadrillas} cuadrillas. "
                "Skipping seeding."
            )
            return

        # Run seeding functions
        seed_cuadrillas(db)
        seed_ots(db)
        seed_logs(db)

        logger.info("Database seeding completed successfully!")

    except Exception as e:
        logger.error(f"Error during seeding: {str(e)}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run seeding
    try:
        main()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Seeding failed: {str(e)}")
        sys.exit(1)

