import csv
import io


PRODUCT = {"Mfg_Part_Num":"AST-24","Part_Desc":"Built-in dishwasher 14 place settings stainless steel","E1_Brand":"Aster","Unilog_Brand":"-","DIB_Brand":"-","Part_Manuf":"Aster Works"}


def test_complete_demo_review_export_flow(client):
    product = client.post("/api/v1/enrich/demo/persist", json=PRODUCT)
    assert product.status_code == 200
    body = product.json(); product_id = body["id"]
    field = next(item for item in body["fields"] if item["field_name"] == "MANUFACTURER_NAME")
    corrected = client.post(f"/api/v1/fields/{field['id']}/review", json={"action":"CORRECT","value":"Aster Manufacturing","note":"Verified against synthetic manufacturer evidence"})
    assert corrected.status_code == 200
    changed = next(item for item in corrected.json()["fields"] if item["id"] == field["id"])
    assert changed["generated_value"] == "Aster Manufacturing" and changed["review_status"] == "APPROVED"
    mobile = next(item for item in corrected.json()["fields"] if item["field_name"] == "MOBILE_DESC")
    assert "Aster Manufacturing" in mobile["generated_value"]
    audit = client.get(f"/api/v1/products/{product_id}/audit.json").json()
    assert audit["review_history"][0]["decision"] == "CORRECT"
    exported = client.get(f"/api/v1/products/{product_id}/export.csv")
    rows = list(csv.reader(io.StringIO(exported.text)))
    schema = client.get("/api/v1/schema/output").json()["columns"]
    assert rows[0] == schema and len(rows[0]) == 252
    assert rows[1][schema.index("MANUFACTURER_NAME")] == "Aster Manufacturing"
    assert "Aster Manufacturing" in rows[1][schema.index("MOBILE_DESC")]
    assert rows[1][schema.index("EAN")] == ""


def test_manufacturer_correction_rebuilds_every_derived_description(client):
    original_manufacturer = "Synthetic Original Manufacturing"
    corrected_manufacturer = "Synthetic Corrected Manufacturing"
    payload = {**PRODUCT, "Part_Manuf": original_manufacturer, "E1_Brand": "-"}
    body = client.post("/api/v1/enrich/demo/persist", json=payload).json()
    manufacturer = next(item for item in body["fields"] if item["field_name"] == "MANUFACTURER_NAME")

    response = client.post(
        f"/api/v1/fields/{manufacturer['id']}/review",
        json={"action": "CORRECT", "value": corrected_manufacturer, "note": "Verified synthetic correction"},
    )
    assert response.status_code == 200

    derived_names = {
        "MOBILE_DESC", "INVOICE_DESC", "SHORT_DESC", "RETAIL_DESC",
        "MARKETING_DESCRIPTION",
    }
    derived = [
        field for field in response.json()["fields"]
        if field["field_name"] in derived_names or field["field_name"].startswith("LONG_DESC")
    ]
    assert derived
    assert any(field["field_name"].startswith("LONG_DESC") for field in derived)
    for field in derived:
        value = field["generated_value"] or ""
        assert corrected_manufacturer.casefold() in value.casefold(), field["field_name"]
        assert original_manufacturer.casefold() not in value.casefold(), field["field_name"]


def test_rejected_field_is_excluded_and_product_audit_is_preserved(client):
    body = client.post("/api/v1/enrich/demo/persist", json=PRODUCT).json()
    field = next(item for item in body["fields"] if item["field_name"] == "MANUFACTURER_NAME")
    rejected = client.post(f"/api/v1/fields/{field['id']}/review", json={"action":"REJECT","reason":"Synthetic evidence insufficient"})
    assert rejected.status_code == 200
    approved_product = client.post(f"/api/v1/products/{body['id']}/review", json={"action":"APPROVE","note":"Judge accepted remaining fields"})
    assert approved_product.json()["review_status"] == "APPROVED"
    schema = client.get("/api/v1/schema/output").json()["columns"]
    rows = list(csv.reader(io.StringIO(client.get(f"/api/v1/products/{body['id']}/export.csv").text)))
    assert rows[1][schema.index("MANUFACTURER_NAME")] == ""
    audit = client.get(f"/api/v1/products/{body['id']}/audit.json").json()
    assert any(item["scope"] == "product" and item["decision"] == "APPROVE" for item in audit["review_history"])
    assert any(field["review_status"] == "REJECTED" for field in audit["fields"])


def test_batch_progress_limit_and_cancellation(client):
    job = client.post("/api/v1/jobs", json={"rows":[PRODUCT, {**PRODUCT,"Mfg_Part_Num":"AST-25"}], "limit":2})
    assert job.status_code == 200 and job.json()["processed_count"] == 2 and job.json()["status"] == "COMPLETED"
    job_id = job.json()["id"]
    assert client.get(f"/api/v1/jobs/{job_id}").json()["row_count"] == 2
    assert client.post(f"/api/v1/jobs/{job_id}/cancel").json()["status"] == "CANCELLED"


def test_csv_formula_injection_in_export(client):
    body = client.post("/api/v1/enrich/demo/persist", json={**PRODUCT,"Mfg_Part_Num":"=2+2"}).json()
    csv_text = client.get(f"/api/v1/products/{body['id']}/export.csv").text
    assert "'=2+2" in csv_text


def test_quality_metrics_come_from_state(client):
    metrics = client.get("/api/v1/quality").json()
    assert metrics["field_count"] >= 0
    assert "evidence_coverage" in metrics and "conflict_count" in metrics
