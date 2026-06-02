import pytest
from src.edgehunter.core.observed_result_ingestion import ingest_observed_results_payload


def test_ingestion_blocks_operational_language():
    dangerous_payload = """result_id,classification_id,signal_id,opportunity_id,source,match_id,result_status,observed_at,notes
R-123,C-123,S-123,O-123,LOCAL_CSV,TEST-OP,POSITIVE_OBSERVED,2026-06-02T10:00:00Z,great aposta
"""
    with pytest.raises((ValueError, RuntimeError)) as exc:
        ingest_observed_results_payload(
            payload=dangerous_payload,
            payload_format="csv",
            classifications=[]
        )
    err_msg = str(exc.value).lower()
    assert "aposta" in err_msg or "operational language" in err_msg or "dangerous" in err_msg


def test_ingestion_blocks_financial_fields():
    dangerous_payload = """result_id,classification_id,signal_id,opportunity_id,source,match_id,result_status,observed_at,stake
R-123,C-123,S-123,O-123,LOCAL_CSV,TEST-OP,POSITIVE_OBSERVED,2026-06-02T10:00:00Z,100
"""
    with pytest.raises((ValueError, RuntimeError)) as exc:
        ingest_observed_results_payload(
            payload=dangerous_payload,
            payload_format="csv",
            classifications=[]
        )
    err_msg = str(exc.value).lower()
    assert "stake" in err_msg or "forbidden" in err_msg or "financial" in err_msg


def test_ingestion_blocks_operational_flags():
    dangerous_payload = """result_id,classification_id,signal_id,opportunity_id,source,match_id,result_status,observed_at,bet_placed
R-123,C-123,S-123,O-123,LOCAL_CSV,TEST-OP,POSITIVE_OBSERVED,2026-06-02T10:00:00Z,true
"""
    with pytest.raises((ValueError, RuntimeError)) as exc:
        ingest_observed_results_payload(
            payload=dangerous_payload,
            payload_format="csv",
            classifications=[]
        )
    err_msg = str(exc.value).lower()
    assert "bet_placed" in err_msg or "forbidden" in err_msg or "operational" in err_msg
