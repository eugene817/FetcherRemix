import pyarrow as pa

JOB_SCHEMA = pa.schema(
    [
        ("job_id", pa.string()),
        ("title", pa.string()),
        ("company", pa.string()),
        ("url", pa.string()),
        ("skills", pa.list_(pa.string())),
        ("salary_min", pa.float64()),
        ("salary_max", pa.float64()),
        ("contract", pa.string()),
        ("is_remote", pa.bool_()),
    ]
)
