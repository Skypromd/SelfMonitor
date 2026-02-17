import datetime
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import main


client = TestClient(main.app)


def _event_payload(
    event_name: str,
    *,
    installation_id: str = "install-demo-1",
    variant: str | None = None,
) -> dict[str, object]:
    metadata: dict[str, object] = {"installation_id": installation_id}
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
    main.MOBILE_ONBOARDING_EXPERIMENT_ENABLED = True
    main.MOBILE_ONBOARDING_ROLLBACK_TO_CONTROL = False
    main.MOBILE_ONBOARDING_ROLLOUT_PERCENT = 100
    main.MOBILE_GO_LIVE_REQUIRED_CRASH_FREE_RATE_PERCENT = 99.5
    main.MOBILE_GO_LIVE_REQUIRED_ONBOARDING_COMPLETION_RATE_PERCENT = 65.0
    main.MOBILE_GO_LIVE_REQUIRED_BIOMETRIC_SUCCESS_RATE_PERCENT = 80.0
    main.MOBILE_GO_LIVE_REQUIRED_PUSH_OPT_IN_RATE_PERCENT = 45.0
    main.MOBILE_GO_LIVE_MIN_ONBOARDING_IMPRESSIONS = 20
    main.MOBILE_GO_LIVE_CRASH_EVENT_NAMES = {
        "mobile.app.crash",
        "mobile.runtime.fatal",
        "mobile.runtime.crash",
    }


def test_mobile_config_returns_splash_and_onboarding_variants():
    response = client.get("/mobile/config")
    assert response.status_code == 200
    payload = response.json()
    assert "generated_at" in payload
    assert payload["splash"]["title"]
    assert len(payload["splash"]["gradient"]) == 3
    assert payload["onboardingExperiment"]["experimentId"]
    assert payload["onboardingExperiment"]["enabled"] is True
    assert payload["onboardingExperiment"]["rollbackToControl"] is False
    assert payload["onboardingExperiment"]["rolloutPercent"] == 100
    assert payload["onboardingExperiment"]["controlVariantId"]
    assert len(payload["onboardingExperiment"]["variants"]) >= 1


def test_mobile_config_supports_onboarding_rollback_toggle():
    main.MOBILE_ONBOARDING_EXPERIMENT_ENABLED = False
    main.MOBILE_ONBOARDING_ROLLBACK_TO_CONTROL = True
    main.MOBILE_ONBOARDING_ROLLOUT_PERCENT = 0
    response = client.get("/mobile/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["onboardingExperiment"]["enabled"] is False
    assert payload["onboardingExperiment"]["rollbackToControl"] is True
    assert payload["onboardingExperiment"]["rolloutPercent"] == 0
    assert payload["onboardingExperiment"]["controlVariantId"]


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


def test_mobile_go_live_gate_endpoint_reports_blockers():
    main.MOBILE_GO_LIVE_REQUIRED_CRASH_FREE_RATE_PERCENT = 99.0
    main.MOBILE_GO_LIVE_REQUIRED_ONBOARDING_COMPLETION_RATE_PERCENT = 65.0
    main.MOBILE_GO_LIVE_REQUIRED_BIOMETRIC_SUCCESS_RATE_PERCENT = 80.0
    main.MOBILE_GO_LIVE_REQUIRED_PUSH_OPT_IN_RATE_PERCENT = 45.0
    main.MOBILE_GO_LIVE_MIN_ONBOARDING_IMPRESSIONS = 2
    main.MOBILE_GO_LIVE_CRASH_EVENT_NAMES = {"mobile.app.crash"}

    events = [
        _event_payload("mobile.splash.impression", installation_id="install-a"),
        _event_payload("mobile.onboarding.impression", installation_id="install-a", variant="velocity"),
        _event_payload("mobile.onboarding.cta_tapped", installation_id="install-a", variant="velocity"),
        _event_payload("mobile.onboarding.completed", installation_id="install-a", variant="velocity"),
        _event_payload("mobile.biometric.gate_shown", installation_id="install-a"),
        _event_payload("mobile.biometric.challenge_succeeded", installation_id="install-a"),
        _event_payload("mobile.push.permission_prompted", installation_id="install-a"),
        _event_payload("mobile.push.permission_granted", installation_id="install-a"),
        _event_payload("mobile.splash.impression", installation_id="install-b"),
        _event_payload("mobile.onboarding.impression", installation_id="install-b", variant="security"),
        _event_payload("mobile.biometric.gate_shown", installation_id="install-b"),
        _event_payload("mobile.push.permission_prompted", installation_id="install-b"),
        _event_payload("mobile.app.crash", installation_id="install-a"),
    ]
    for event in events:
        assert client.post("/mobile/analytics/events", json=event).status_code == 202

    gate_response = client.get("/mobile/analytics/go-live-gate?days=7")
    assert gate_response.status_code == 200
    payload = gate_response.json()
    assert payload["window_days"] == 7
    assert payload["unique_active_installations"] == 2
    assert payload["crashing_installations"] == 1
    assert payload["crash_events"] == 1
    assert payload["sample_size_passed"] is True
    assert payload["push_opt_in_passed"] is True
    assert payload["crash_free_passed"] is False
    assert payload["onboarding_passed"] is False
    assert payload["biometric_passed"] is False
    assert payload["gate_passed"] is False
    assert len(payload["blockers"]) >= 3
