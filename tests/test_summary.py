from operations.views import build_summary_from_events, summarize_transport_means


def test_summarize_transport_means_counts_transport_types():
    events = [
        {"transport_type": "Bus", "delayed": 1},
        {"transport_type": "Bus", "delayed": 0},
        {"transport_type": "Taxi", "delayed": 1},
        {"transport_type": "Moto", "delayed": 0},
    ]

    summary = summarize_transport_means(events)

    assert summary == {
        "Bus": 2,
        "Taxi": 1,
        "Moto": 1,
    }


def test_build_summary_from_events_has_total_and_transport_breakdown():
    events = [
        {"route_id": "R1", "transport_type": "Bus", "delayed": 1, "delay_probability": 60},
        {"route_id": "R1", "transport_type": "Bus", "delayed": 0, "delay_probability": 25},
        {"route_id": "R2", "transport_type": "Taxi", "delayed": 1, "delay_probability": 70},
    ]

    summary = build_summary_from_events(events)

    assert summary["total_trips"] == 3
    assert summary["delayed_trips"] == 2
    assert summary["top_route"] == "R1"
    assert summary["transport_means"] == {"Bus": 2, "Taxi": 1}
