import pandas as pd
from db_manager.augur_manager import AugurManager
from sqlalchemy.exc import SQLAlchemyError
import logging

QUERY_NAME = "BUS_FACTOR"

def bus_factor_query(self, repos):
    """
    Executes a SQL query against the Augur database to fetch contribution data
    and calculates the Bus Factor for the given repositories.

    Args:
        repos ([str]): List of repository IDs to calculate the Bus Factor for.

    Returns:
        dict: Dictionary with repository IDs as keys and their Bus Factors as values.
    """
    logging.warning(f"{QUERY_NAME}_QUERY - START")

    if not repos:
        logging.error(f"{QUERY_NAME}_QUERY - NO REPOSITORIES PROVIDED")
        return {}

    # Convert list of repos to a string format for the SQL query
    formatted_repos = ', '.join(f"'{repo}'" for repo in repos)
    query_string = f"""
        WITH ContributorContributions AS (
            SELECT
                repo_id,
                cntrb_id,
                COUNT(*) AS contributions
            FROM
                augur_data.explorer_contributor_actions
            WHERE
                repo_id IN ({formatted_repos})
            GROUP BY
                repo_id, cntrb_id
        ),
        TotalContributions AS (
            SELECT
                repo_id,
                SUM(contributions) AS total_contributions
            FROM
                ContributorContributions
            GROUP BY
                repo_id
        ),
        RankedContributors AS (
            SELECT
                cc.repo_id,
                cc.cntrb_id,
                cc.contributions,
                tc.total_contributions,
                RANK() OVER (PARTITION BY cc.repo_id ORDER BY cc.contributions DESC) AS rank,
                SUM(cc.contributions) OVER (PARTITION BY cc.repo_id ORDER BY cc.contributions DESC) AS cumulative_contributions
            FROM
                ContributorContributions cc
            JOIN
                TotalContributions tc ON cc.repo_id = tc.repo_id
        )
        SELECT
            rc.repo_id,
            rc.cntrb_id,
            rc.contributions,
            rc.total_contributions,
            rc.rank,
            (CAST(rc.cumulative_contributions AS FLOAT) / CAST(rc.total_contributions AS FLOAT)) * 100 AS cumulative_percentage
        FROM
            RankedContributors rc
        WHERE
            rc.repo_id IN ({formatted_repos})
        ORDER BY
            rc.repo_id, rc.cumulative_contributions DESC
    """

    try:
        dbm = AugurManager()
        results = dbm.run_query(query_string)
    except KeyError:
        logging.error(f"{QUERY_NAME}_QUERY - INCOMPLETE ENVIRONMENT")
        return {}
    except SQLAlchemyError as e:
        logging.error(f"{QUERY_NAME}_QUERY - COULDN'T CONNECT TO DB: {e}")
        raise

    # Process the results to calculate the Bus Factor
    df = pd.DataFrame(results)
    bus_factors = self.calculate_bus_factor(df)

    logging.warning(f"{QUERY_NAME}_QUERY - END")
    return bus_factors

def calculate_bus_factor(self, df):
    bus_factors = {}
    for repo_id, group in df.groupby('repo_id'):
        cumulative_percentage = 0
        contributors_count = 0
        for i, row in group.iterrows():
            cumulative_percentage += row['cumulative_percentage']
            contributors_count += 1
            if cumulative_percentage > 50:
                bus_factors[repo_id] = contributors_count
                break
    return bus_factors












# import logging
# import pandas as pd
# from db_manager.augur_manager import AugurManager
# from app import celery_app
# from cache_manager.cache_manager import CacheManager as cm
# import io
# import datetime as dt
# from sqlalchemy.exc import SQLAlchemyError

# QUERY_NAME = "BUS FACTOR"


# @celery_app.task(
#     bind=True,
#     autoretry_for=(Exception,),
#     exponential_backoff=2,
#     retry_kwargs={"max_retries": 5},
#     retry_jitter=True,
# )
# def bus_factor_query(self, repos):
#     """
#     (Worker Query)
#     Executes SQL query against Augur database for contributor data.

#     Explorer_contributor_actions is a materialized view on the database for quicker run time and
#     may not be in your augur database. The SQL query content can be found
#     in docs/materialized_views/explorer_contributor_actions.sql

#     Args:
#     -----
#         repo_ids ([str]): repos that SQL query is executed on.

#     Returns:
#     --------
#         dict: Results from SQL query, interpreted from pd.to_dict('records')

#     """
#     logging.warning(f"{QUERY_NAME}_DATA_QUERY - START")

#     if len(repos) == 0:
#         return None

#     query_string = f"""
#                     SELECT
#                         repo_id as id,
#                         repo_name as repo_name,
#                         cntrb_id,
#                         created_at,
#                         login,
#                         action,
#                         rank
#                     FROM
#                         augur_data.explorer_contributor_actions
#                     WHERE
#                         repo_id in ({str(repos)[1:-1]})
#                 """

#     try:
#         dbm = AugurManager()
#         engine = dbm.get_engine()
#     except KeyError:
#         # noack, data wasn't successfully set.
#         logging.error(f"{QUERY_NAME}_DATA_QUERY - INCOMPLETE ENVIRONMENT")
#         return False
#     except SQLAlchemyError:
#         logging.error(f"{QUERY_NAME}_DATA_QUERY - COULDN'T CONNECT TO DB")
#         # allow retry via Celery rules.
#         raise SQLAlchemyError("DBConnect failed")

#     df = dbm.run_query(query_string)

    # # update column values
    # df.loc[df["action"] == "pull_request_open", "action"] = "PR Opened"
    # df.loc[df["action"] == "pull_request_comment", "action"] = "PR Comment"
    # df.loc[df["action"] == "pull_request_closed", "action"] = "PR Closed"
    # df.loc[df["action"] == "pull_request_merged", "action"] = "PR Merged"
    # df.loc[df["action"] == "pull_request_review_COMMENTED", "action"] = "PR Review"
    # df.loc[df["action"] == "pull_request_review_APPROVED", "action"] = "PR Review"
    # df.loc[df["action"] == "pull_request_review_CHANGES_REQUESTED", "action"] = "PR Review"
    # df.loc[df["action"] == "pull_request_review_DISMISSED", "action"] = "PR Review"
    # df.loc[df["action"] == "issue_opened", "action"] = "Issue Opened"
    # df.loc[df["action"] == "issue_closed", "action"] = "Issue Closed"
    # df.loc[df["action"] == "issue_comment", "action"] = "Issue Comment"
    # df.loc[df["action"] == "commit", "action"] = "Commit"
    # df["cntrb_id"] = df["cntrb_id"].astype(str)  # contributor ids to strings
    # df.rename(columns={"action": "Action"}, inplace=True)

#     # change to compatible type and remove all data that has been incorrectly formated
#     df["created_at"] = pd.to_datetime(df["created_at"], utc=True).dt.date
#     df = df[df.created_at < dt.date.today()]

#     df = df.reset_index(drop=True)

#     pic = []

#     for i, r in enumerate(repos):
#         # convert series to a dataframe
#         c_df = pd.DataFrame(df.loc[df["id"] == r]).reset_index(drop=True)

#         # bytes buffer to be written to
#         b = io.BytesIO()

#         # write dataframe in feather format to BytesIO buffer
#         bs = c_df.to_feather(b)

#         # move head of buffer to the beginning
#         b.seek(0)

#         # write the bytes of the buffer into the array
#         bs = b.read()
#         pic.append(bs)

#     del df

#     # store results in Redis
#     cm_o = cm()

#     # 'ack' is a boolean of whether data was set correctly or not.
#     ack = cm_o.setm(
#         func=contributors_query,
#         repos=repos,
#         datas=pic,
#     )
#     logging.warning(f"{QUERY_NAME}_DATA_QUERY - END")

#     return ack
