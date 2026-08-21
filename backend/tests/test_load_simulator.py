from scripts.simulate_cctv_load import SimulationConfig, run_stage


def test_simulator_keeps_workload_bounded_and_accounts_for_every_sample():
    result = run_stage(
        5,
        SimulationConfig(
            virtual_duration_seconds=20,
            time_scale=0,
            stream_failure_rate=0,
            queue_capacity=16,
            worker_concurrency=4,
            max_batch_wait_ms=1,
            base_batch_latency_ms=0,
            per_item_latency_ms=0,
        ),
    )

    assert result.scheduled_samples == (
        result.successful_jobs + result.stream_failures + result.overload_skips
    )
    assert result.max_queue_depth <= 16
    assert result.max_batch_size <= 8
    assert result.latest_state_writes == result.websocket_updates
