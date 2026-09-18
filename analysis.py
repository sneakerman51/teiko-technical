import pandas as pd
from db import get_connection

# Part 2
def get_cell_frequencies():
    query = """
    SELECT "sample", "population", "count"
    FROM cell_counts
    """

    with get_connection() as conn:
        df = pd.read_sql_query(query, conn)
    df["total_count"] = df.groupby("sample")["count"].transform("sum")
    df["percentage"] = df["count"]/df["total_count"] * 100

    return df[["sample", "total_count", "population", "count", "percentage"]]