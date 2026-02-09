import asyncio
import json
import websockets
import os
import logging
from agent.agent import AgentOrchestrator


logger = logging.getLogger(__name__)


class GatewayServer:
    def __init__(self, agent: AgentOrchestrator, host="localhost", port=8765, auth_token=None):
        self.agent = agent
        self.host = host
        self.port = port
        self.auth_token = auth_token or os.environ.get(
            "PIXELPILOT_GATEWAY_TOKEN", "pixelpilot-secret"
        )

    async def handler(self, websocket):
        async for message in websocket:
            try:
                data = json.loads(message)
                if self.auth_token and data.get("auth") != self.auth_token:
                    await websocket.send(json.dumps({"error": "Unauthorized"}))
                    continue
                command = data.get("command")
                params = data.get("params", {})
                if not command:
                    await websocket.send(json.dumps({"error": "No command provided"}))
                    continue

                full_command = command
                if params:
                    full_command += " " + " ".join(f"{k}: {v}" for k, v in params.items())

                result = self.agent.run_task(full_command)

                last_reasoning = "Task completed."
                if self.agent.task_history:
                    last_action = self.agent.task_history[-1]
                    if last_action.get("action_type") == "reply":
                        last_reasoning = last_action.get("params", {}).get("text", "")
                    else:
                        last_reasoning = last_action.get("reasoning", str(last_action))

                response = {"result": result, "output": last_reasoning, "params": params}
                await websocket.send(json.dumps(response))
            except Exception as e:
                logger.exception("Gateway handler error: %s", e)
                await websocket.send(json.dumps({"error": str(e)}))

    def start(self):
        async def run_server():
            logger.info("Gateway server running on ws://%s:%s", self.host, self.port)
            async with websockets.serve(self.handler, self.host, self.port):
                await asyncio.Future()  # Run forever

        try:
            asyncio.run(run_server())
        except Exception as e:
            logger.exception("Gateway server failed to start: %s", e)
