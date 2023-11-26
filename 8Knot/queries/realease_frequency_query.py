import logging
import pandas as pd
from db_manager.augur_manager import AugurManager
from app import celery_app
from cache_manager.cache_manager import CacheManager as cm
import io
import datetime as dt
from sqlalchemy.exc import SQLAlchemyError

QUERY_NAME = "RELEASES"

@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)

def release_frequency_query(self,repos):
    logging.warning(f"{QUERY_NAME}_DATA_QUERY - START")

    if len(repos) == 0:
        return None

    query_string = f"""
                    SELECT
                        repo_id as id,
                        release_id as r_id,
                        release_published_at as r_date
                    FROM 
                        augur_data.releases
                    WHERE
                        repo_id in ({str(repos)[1:-1]})
                """

    try:
        dbm = AugurManager()
        engine = dbm.get_engine()
    except KeyError:
        # noack, data wasn't successfully set.
        logging.error(f"{QUERY_NAME}_DATA_QUERY - INCOMPLETE ENVIRONMENT")
        return False
    except SQLAlchemyError:
        logging.error(f"{QUERY_NAME}_DATA_QUERY - COULDN'T CONNECT TO DB")
        # allow retry via Celery rules.
        raise SQLAlchemyError("DBConnect failed")

    df = dbm.run_query(query_string)

    df["r_date"] = pd.to_datetime(df["r_date"], utc=True).dt.date
    df = df[df.r_date < dt.date.today()]

    pic = []
    for r in repos:
        c_df = pd.DataFrame(df.loc[df["id"] == r].drop(columns=["id"])).reset_index(drop=True)

        b = io.BytesIO()

        bs = c_df.to_feather(b)

        b.seek(0)

        bs = b.read()
        pic.append(bs)

    del df

    cm_o = cm()

    ack = cm_o.setm(
        func=release_frequency_query,
        repos=repos,
        datas=pic,
    )

    logging.warning(f"{QUERY_NAME}_DATA_QUERY - END")
    return ack

