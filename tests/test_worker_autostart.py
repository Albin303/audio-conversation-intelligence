from unittest.mock import Mock, patch

from src.api.server import launch_worker_processes


def test_launch_worker_processes_starts_audio_and_ml_workers() -> None:
    with patch("src.api.server.subprocess.Popen") as mock_popen:
        mock_popen.return_value = Mock(pid=101)

        processes = launch_worker_processes()

    assert len(processes) == 2
    assert [call.kwargs["env"]["WORKER_TYPE"] for call in mock_popen.call_args_list] == ["audio", "ml"]
