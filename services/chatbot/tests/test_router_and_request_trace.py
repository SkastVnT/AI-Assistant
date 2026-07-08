import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.chatbot.core.central_router import route_request


def test_router_pipeline_selection():
    assert route_request("please search web latest ai news").pipeline == "xai_native"
    assert route_request("hãy tạo ảnh anime waifu").pipeline == "anime_pipeline"
    assert route_request("hãy đọc file và chạy git status").pipeline == "mcp_tool_flow"
