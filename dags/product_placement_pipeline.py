"""
Product Placement Optimisation: daily data pipeline.

    load_raw_to_oltp >> oltp_to_warehouse >> run_quality_checks
                     >> update_artifacts >> done

Five tasks in a straight line. Each one wraps a script that also runs standalone
from the command line, so nothing about the logic is Airflow-specific and the
same code can be demonstrated with or without the scheduler running.

Why five and not fifteen:
    Every task here earns its place. Splitting the warehouse load into one task
    per dimension would look busier on the graph view but would add nothing
    except more places for a run to half-fail. Five tasks that all go green and
    can each be explained is worth more than fifteen where two are decoration.

Re-running is safe:
    Every load carries ON CONFLICT DO NOTHING against a natural key, so a second
    run of the whole DAG inserts nothing and the row counts do not move. That is
    the property the quality checks verify, and it is what makes a backfill or a
    retry harmless.

Schedule:
    @daily, but the DAG starts paused=false with catchup=False, so it will not
    stampede through months of historical runs the moment it is unpaused. The
    store's data is a fixed historical export for this project, so in practice
    the DAG is triggered manually to demonstrate the pipeline.
"""

from __future__ import annotations

import pendulum
from airflow.sdk import dag, task

DEFAULT_ARGS = {
    "owner": "Samikshya Baniya",
    "retries": 1,
    "retry_delay": pendulum.duration(minutes=2),
}


def _run(module_path: str, label: str) -> str:
    """Import a pipeline module and run its main(), failing the task on non-zero.

    The import happens inside the task rather than at module level so that DAG
    parsing stays fast and does not need pandas loaded on every scheduler heartbeat.
    """
    import importlib

    module = importlib.import_module(module_path)
    exit_code = module.main()
    if exit_code != 0:
        raise RuntimeError(
            f"{label} failed with exit code {exit_code}. See the task log above "
            f"for the specific check or step that failed."
        )
    return f"{label} completed"


@dag(
    dag_id="product_placement_pipeline",
    description="Load POS data into Postgres, build the star schema, verify it, refresh the dashboard",
    default_args=DEFAULT_ARGS,
    start_date=pendulum.datetime(2026, 8, 1, tz="UTC"),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    tags=["product-placement", "ST6001CEM", "warehouse"],
)
def product_placement_pipeline():

    @task(task_id="load_raw_to_oltp")
    def load_raw_to_oltp() -> str:
        """Load the cleaned POS CSV into the normalised OLTP schema.

        Expects 767,180 line items across 218,037 transactions and 5,680
        products. Asserts those counts itself and fails if they do not match.
        """
        return _run("scripts.load_to_postgres", "OLTP load")

    @task(task_id="oltp_to_warehouse")
    def oltp_to_warehouse() -> str:
        """Build the star schema from the OLTP tables.

        Populates dim_date, dim_category (carrying the notebook 07 placement
        zones), dim_product, dim_basket and fact_sales, entirely with
        set-based INSERT ... SELECT inside Postgres.
        """
        return _run("etl.load_warehouse", "Warehouse load")

    @task(task_id="run_quality_checks")
    def run_quality_checks() -> str:
        """Gate the pipeline on 32 completeness, integrity, consistency and
        accuracy checks.

        The accuracy group re-verifies the headline thesis figures, so an ETL
        change that silently moved the average basket value would fail here
        rather than reach the dashboard unnoticed.
        """
        return _run("etl.quality_checks", "Quality checks")

    @task(task_id="update_artifacts")
    def update_artifacts() -> str:
        """Refresh the dashboard artifacts the warehouse can derive.

        Only warehouse-derived files are rewritten. The association rule,
        clustering and cross-sell artifacts are left alone because they come
        from Apriori and K-Means in the notebooks, not from the warehouse.
        """
        return _run("etl.refresh_artifacts", "Artifact refresh")

    @task(task_id="done")
    def done() -> str:
        """Final marker so a successful run ends on an unambiguous green task."""
        print("Pipeline complete: OLTP loaded, warehouse built, quality verified, "
              "dashboard artifacts refreshed.", flush=True)
        return "pipeline complete"

    load_raw_to_oltp() >> oltp_to_warehouse() >> run_quality_checks() >> update_artifacts() >> done()


product_placement_pipeline()
