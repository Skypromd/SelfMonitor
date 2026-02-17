import datetime
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import main


client = TestClient(main.app)


def _event_payload(event_name: str, *, variant: str | None = None) -> dict[str, object]:
    metadata: dict[str, object] = {"installation_id": "install-demo-1"}
    if variant:
        metadata["onboarding_variant"] = variant
    return {
        "event": event_name,
        "source": "mobile-app",
        "platform": "ios",
        "occurred_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "metadata": metadata,
    }


def setup_function():
    main.mobile_analytics_events.clear()
    main.mobile_weekly_snapshots.clear()
    main.MOBILE_ANALYTICS_INGEST_API_KEY = ""


def test_mobile_config_returns_splash_and_onboarding_variants():
    response = client.get("/mobile/config")
    assert response.status_code == 200
    payload = response.json()
    assert "generated_at" in payload
    assert payload["splash"]["title"]
    assert len(payload["splash"]["gradient"]) == 3
    assert payload["onboardingExperiment"]["experimentId"]
    assert len(payload["onboardingExperiment"]["variants"]) >= 1


def test_mobile_analytics_ingest_and_funnel_snapshot():
    events = [
        _event_payload("mobile.splash.impression"),
        _event_payload("mobile.splash.dismissed"),
        _event_payload("mobile.onboarding.impression", variant="velocity"),
        _event_payload("mobile.onboarding.cta_tapped", variant="velocity"),
        _event_payload("mobile.onboarding.completed", variant="velocity"),
        _event_payload("mobile.onboarding.impression", variant="security"),
        _event_payload("mobile.biometric.gate_shown"),
        _event_payload("mobile.biometric.challenge_succeeded"),
        _event_payload("mobile.push.permission_prompted"),
        _event_payload("mobile.push.permission_granted"),
        _event_payload("mobile.push.deep_link_opened"),
    ]
    for event in events:
        response = client.post("/mobile/analytics/events", json=event)
        assert response.status_code == 202
        assert response.json()["accepted"] is True

    funnel_response = client.get("/mobile/analytics/funnel?days=30")
    assert funnel_response.status_code == 200
    funnel = funnel_response.json()

    assert funnel["window_days"] == 30
    assert funnel["splash_impressions"] == 1
    assert funnel["splash_dismissed"] == 1
    assert funnel["onboarding_impressions"] == 2
    assert funnel["onboarding_cta_taps"] == 1
    assert funnel["onboarding_completions"] == 1
    assert funnel["biometric_gate_shown"] == 1
    assert funnel["biometric_successes"] == 1
    assert funnel["push_permission_prompted"] == 1
    assert funnel["push_permission_granted"] == 1
    assert funnel["push_deep_link_opened"] == 1
    assert funnel["onboarding_completion_rate_percent"] == 50.0

    variants = {item["variant_id"]: item for item in funnel["variants"]}
    assert variants["velocity"]["impressions"] == 1
    assert variants["velocity"]["cta_taps"] == 1
    assert variants["velocity"]["completions"] == 1
    assert variants["velocity"]["completion_rate_percent"] == 100.0


def test_mobile_analytics_api_key_guard():
    main.MOBILE_ANALYTICS_INGEST_API_KEY = "secret-key"
    unauthorized_response = client.post("/mobile/analytics/events", json=_event_payload("mobile.splash.impression"))
    assert unauthorized_response.status_code == 401

    authorized_response = client.post(
        "/mobile/analytics/events",
        json=_event_payload("mobile.splash.impression"),
        headers={"X-Api-Key": "secret-key"},
    )
    assert authorized_response.status_code == 202

    unauthorized_funnel = client.get("/mobile/analytics/funnel")
    assert unauthorized_funnel.status_code == 401

    authorized_funnel = client.get("/mobile/analytics/funnel", headers={"X-Api-Key": "secret-key"})
    assert authorized_funnel.status_code == 200


def test_mobile_analytics_export_supports_csv_and_json():
    client.post("/mobile/analytics/events", json=_event_payload("mobile.splash.impression"))
    client.post("/mobile/analytics/events", json=_event_payload("mobile.onboarding.impression", variant="velocity"))
    client.post("/mobile/analytics/events", json=_event_payload("mobile.onboarding.completed", variant="velocity"))

    json_export = client.get("/mobile/analytics/funnel/export?days=14&format=json")
    assert json_export.status_code == 200
    assert json_export.json()["total_events"] == 3

    csv_export = client.get("/mobile/analytics/funnel/export?days=14&format=csv")
    assert csv_export.status_code == 200
    assert csv_export.headers["content-type"].startswith("text/csv")
    text = csv_export.text
    assert "metric,value" in text
    assert "onboarding_completions,1" in text
    assert "variant_id,impressions,cta_taps,completions,completion_rate_percent" in text


def test_mobile_weekly_snapshot_and_cadence_endpoints():
    client.post("/mobile/analytics/events", json=_event_payload("mobile.splash.impression"))
    client.post("/mobile/analytics/events", json=_event_payload("mobile.onboarding.impression", variant="velocity"))
    client.post("/mobile/analytics/events", json=_event_payload("mobile.onboarding.cta_tapped", variant="velocity"))
    client.post("/mobile/analytics/events", json=_event_payload("mobile.onboarding.completed", variant="velocity"))
    client.post("/mobile/analytics/events", json=_event_payload("mobile.biometric.gate_shown"))
    client.post("/mobile/analytics/events", json=_event_payload("mobile.biometric.challenge_succeeded"))
    client.post("/mobile/analytics/events", json=_event_payload("mobile.push.permission_prompted"))
    client.post("/mobile/analytics/events", json=_event_payload("mobile.push.permission_granted"))

    snapshot_response = client.post("/mobile/analytics/weekly-snapshot?days=7")
    assert snapshot_response.status_code == 200
    snapshot_payload = snapshot_response.json()
    assert snapshot_payload["window_days"] == 7
    assert snapshot_payload["funnel"]["total_events"] == 8
    assert len(snapshot_payload["recommended_actions"]) >= 1
    assert len(snapshot_payload["checklist"]) == 3

    list_response = client.get("/mobile/analytics/weekly-snapshots?limit=5")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total_snapshots"] == 1
    assert len(list_payload["items"]) == 1

    cadence_response = client.get("/mobile/analytics/weekly-cadence?days=7")
    assert cadence_response.status_code == 200
    cadence_payload = cadence_response.json()
    assert cadence_payload["window_days"] == 7
    assert cadence_payload["funnel"]["total_events"] == 8
