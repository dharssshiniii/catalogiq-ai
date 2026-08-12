import io

VALID_CSV = b"Mfg_Part_Num,Part_Desc,E1_Brand,Unilog_Brand,DIB_Brand,Part_Manuf\nDW-14,A 14 place settings dishwasher,Aster,-- No Unilog Brand --,-,Aster Works\nDW-14,A 14 place settings dishwasher,Aster,-- No Unilog Brand --,-,Aster Works\n"


def test_health_and_status(client):
    assert client.get("/health").json()["status"] == "ok"
    status = client.get("/api/v1/status").json()
    assert status["mode"] == "DEMO"
    assert status["database"]["available"] is True
    assert status["providers"]["demo"] is True


def test_output_schema_parsing(client):
    response = client.get("/api/v1/schema/output")
    assert response.status_code == 200
    assert response.json()["column_count"] == 252
    assert "MANUFACTURER_NAME" in response.json()["columns"]


def test_profile_endpoint(client):
    response = client.post("/api/v1/datasets/profile", files={"file": ("sample.csv", io.BytesIO(VALID_CSV), "text/csv")})
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 2
    assert body["duplicate_count"] == 1
    assert body["duplicate_counts"] == {"manufacturer_part_number": 1, "description": 1, "full_row": 1}
    assert body["missing_placeholder_counts"]["Unilog_Brand"] == 2


def test_profile_rejects_wrong_extension(client):
    response = client.post("/api/v1/datasets/profile", files={"file": ("sample.txt", VALID_CSV, "text/plain")})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_EXTENSION"


def test_demo_enrichment_is_deterministic(client):
    payload = {"Mfg_Part_Num": "DW-14X", "Part_Desc": "14 place settings stainless steel dishwasher", "E1_Brand": "Aster", "Unilog_Brand": "-", "DIB_Brand": "-", "Part_Manuf": "Aster Works"}
    first = client.post("/api/v1/enrich/demo", json=payload)
    second = client.post("/api/v1/enrich/demo", json=payload)
    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["commerce_record"]["ATTRIBUTE_VALUE 1"] == "14"


def test_demo_missing_evidence_is_flagged(client):
    payload = {"Mfg_Part_Num": "MX-1", "Part_Desc": "Industrial cleaning appliance", "E1_Brand": "-", "Unilog_Brand": "-", "DIB_Brand": "-", "Part_Manuf": "-"}
    response = client.post("/api/v1/enrich/demo", json=payload).json()
    assert response["review_status"] == "NEEDS_REVIEW"
    assert any(issue["code"] == "MISSING_EVIDENCE" for issue in response["validation_issues"])
