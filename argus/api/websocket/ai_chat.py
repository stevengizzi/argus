"""WebSocket handler for AI chat streaming.

Provides real-time streaming of AI responses with tool_use support.
Authentication via JWT token in first message.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, date
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from argus.ai.tools import ARGUS_TOOLS, requires_approval
from argus.api.auth import get_jwt_secret
from argus.api.dependencies import AppState

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Router for AI chat WebSocket
ai_ws_router = APIRouter(tags=["ai-websocket"])

# Page tag mapping for conversation creation
PAGE_TAG_MAP: dict[str, str] = {
    "Dashboard": "session",
    "Trades": "session",
    "Performance": "research",
    "Orchestrator": "session",
    "PatternLibrary": "research",
    "Debrief": "debrief",
    "System": "session",
}

# Active connections for cleanup
_active_connections: set[WebSocket] = set()


def get_active_connections() -> set[WebSocket]:
    """Get the set of active AI chat WebSocket connections."""
    return _active_connections


@ai_ws_router.websocket("/ws/v1/ai/chat")
async def ai_chat_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming AI chat.

    Protocol:
    1. Client sends: {type: "auth", token: "<JWT>"}
    2. Server validates JWT, closes with 4001 if invalid
    3. Client sends: {type: "message", conversation_id: str|null, content: str, page: str, page_context: dict}
    4. Server streams: {type: "stream_start"}, {type: "token"}, {type: "tool_use"}, {type: "stream_end"}
    5. Client can send: {type: "cancel"} to abort streaming
    """
    await websocket.accept()
    _active_connections.add(websocket)

    authenticated = False
    app_state: AppState | None = None
    current_stream_task: asyncio.Task[None] | None = None

    try:
        # Get AppState from the app
        app_state = websocket.app.state.app_state

        # Wait for auth message
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)

        if auth_data.get("type") != "auth":
            await websocket.close(code=4001)
            return

        token = auth_data.get("token")
        if not token:
            await websocket.close(code=4001)
            return

        # Validate JWT
        try:
            jwt_secret = get_jwt_secret()
            jwt.decode(token, jwt_secret, algorithms=["HS256"])
            authenticated = True
        except (JWTError, Exception):
            await websocket.close(code=4001)
            return

        # Send auth success
        await websocket.send_json({
            "type": "auth_success",
            "timestamp": datetime.now(UTC).isoformat(),
        })

        # Main message loop
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            msg_type = data.get("type")

            if msg_type == "cancel":
                # Cancel current streaming if active
                if current_stream_task is not None and not current_stream_task.done():
                    current_stream_task.cancel()
                    try:
                        await current_stream_task
                    except asyncio.CancelledError:
                        pass
                    current_stream_task = None
                continue

            if msg_type == "message":
                # Cancel any existing stream before starting new one
                if current_stream_task is not None and not current_stream_task.done():
                    current_stream_task.cancel()
                    try:
                        await current_stream_task
                    except asyncio.CancelledError:
                        pass

                # Start new streaming response
                current_stream_task = asyncio.create_task(
                    _handle_chat_message(websocket, app_state, data)
                )

    except asyncio.TimeoutError:
        await websocket.close(code=4001)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception(f"Error in AI chat WebSocket: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })
        except Exception:
            pass
    finally:
        _active_connections.discard(websocket)
        # Cancel any running stream
        if current_stream_task is not None and not current_stream_task.done():
            current_stream_task.cancel()
            try:
                await current_stream_task
            except asyncio.CancelledError:
                pass


async def _handle_chat_message(
    websocket: WebSocket,
    app_state: AppState,
    data: dict[str, Any],
) -> None:
    """Handle a chat message and stream the response.

    Args:
        websocket: The WebSocket connection.
        app_state: Application state with AI services.
        data: The message data from the client.
    """
    # Check AI services
    if app_state.ai_client is None or not app_state.ai_client.enabled:
        await websocket.send_json({
            "type": "error",
            "message": "AI service not available",
        })
        return

    if app_state.conversation_manager is None:
        await websocket.send_json({
            "type": "error",
            "message": "Conversation service not available",
        })
        return

    if app_state.prompt_manager is None or app_state.context_builder is None:
        await websocket.send_json({
            "type": "error",
            "message": "AI prompt services not available",
        })
        return

    conversation_id = data.get("conversation_id")
    content = data.get("content", "")
    page = data.get("page", "Dashboard")
    page_context = data.get("page_context", {})

    # Get or create conversation
    if conversation_id is None:
        tag = PAGE_TAG_MAP.get(page, "general")
        today_str = date.today().isoformat()
        conversation = await app_state.conversation_manager.create_conversation(today_str, tag)
        conversation_id = conversation["id"]
    else:
        conversation = await app_state.conversation_manager.get_conversation(conversation_id)
        if conversation is None:
            await websocket.send_json({
                "type": "error",
                "message": f"Conversation {conversation_id} not found",
            })
            return

    # Build context
    context = await app_state.context_builder.build_context(page, page_context, app_state)

    # Get conversation history
    history_messages = await app_state.conversation_manager.get_messages(conversation_id, limit=50)
    history = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history_messages
    ]

    # Build system prompt
    strategies_info = _build_strategies_info(app_state)
    system_config = _build_system_config_info(app_state)
    system_prompt = app_state.prompt_manager.build_system_prompt(strategies_info, system_config)
    formatted_page_context = app_state.prompt_manager.build_page_context(
        page, context.get("page_context", {})
    )

    # Assemble messages
    full_system, messages = app_state.prompt_manager.build_conversation_messages(
        history,
        content,
        system_prompt,
        formatted_page_context,
    )

    # Persist user message
    await app_state.conversation_manager.add_message(
        conversation_id,
        "user",
        content,
        page_context=page_context,
    )

    # Generate message ID for the stream
    from argus.core.ids import generate_id
    message_id = generate_id()

    # Send stream_start
    await websocket.send_json({
        "type": "stream_start",
        "conversation_id": conversation_id,
        "message_id": message_id,
    })

    # Stream response with timeout
    full_content_parts: list[str] = []
    tool_use_blocks: list[dict[str, Any]] = []
    total_input_tokens = 0
    total_output_tokens = 0
    model = ""

    try:
        # Get streaming response
        stream_gen = await asyncio.wait_for(
            app_state.ai_client.send_message(
                messages,
                full_system,
                tools=ARGUS_TOOLS,
                stream=True,
            ),
            timeout=60.0,
        )

        # Process stream events
        # Track tool_use blocks during streaming
        current_tool_use: dict[str, Any] | None = None
        current_tool_input_json: list[str] = []

        async for event in stream_gen:
            event_type = event.get("type", "")

            # DEBUG: Log all events to diagnose tool_use processing
            logger.debug("Stream event: type=%s, keys=%s", event_type, list(event.keys()))
            if event_type == "content_block_start":
                logger.debug(
                    "content_block_start details: content_block=%s",
                    event.get("content_block", "MISSING"),
                )
            if event_type == "content_block_delta":
                logger.debug(
                    "content_block_delta details: delta=%s, delta_type=%s",
                    event.get("delta", "MISSING"),
                    event.get("delta_type", "MISSING"),
                )

            if event_type == "error":
                await websocket.send_json({
                    "type": "error",
                    "message": event.get("message", "Stream error"),
                })
                return

            if event_type == "message_start":
                msg_info = event.get("message", {})
                model = msg_info.get("model", "")

            elif event_type == "content_block_start":
                # Check if it's a tool_use block
                content_block = event.get("content_block", {})
                if content_block.get("type") == "tool_use":
                    current_tool_use = {
                        "id": content_block.get("id", ""),
                        "name": content_block.get("name", ""),
                    }
                    current_tool_input_json = []

            elif event_type == "content_block_delta":
                delta = event.get("delta", {})
                delta_type = delta.get("type", "") or event.get("delta_type", "")

                if delta_type == "text_delta":
                    text = delta.get("text", "") or event.get("text", "")
                    if text:
                        full_content_parts.append(text)
                        await websocket.send_json({
                            "type": "token",
                            "content": text,
                        })
                elif delta_type == "input_json_delta" and current_tool_use is not None:
                    # Accumulate tool_use input JSON
                    partial_json = delta.get("partial_json", "")
                    if partial_json:
                        current_tool_input_json.append(partial_json)

            elif event_type == "content_block_stop":
                # Block finished - finalize tool_use if we have one
                logger.debug(
                    "content_block_stop: current_tool_use=%s, input_json_len=%d",
                    current_tool_use,
                    len(current_tool_input_json),
                )
                if current_tool_use is not None:
                    # Parse accumulated JSON
                    import json as json_module
                    try:
                        input_json_str = "".join(current_tool_input_json)
                        tool_input = json_module.loads(input_json_str) if input_json_str else {}
                    except json_module.JSONDecodeError:
                        tool_input = {}

                    current_tool_use["input"] = tool_input

                    # Handle the tool_use
                    tool_name = current_tool_use.get("name", "")
                    tool_use_id = current_tool_use.get("id", "")

                    proposal_id = None
                    if tool_name == "generate_report":
                        # generate_report doesn't require approval
                        pass
                    elif requires_approval(tool_name) and app_state.action_manager is not None:
                        # Create proposal
                        proposal = await app_state.action_manager.create_proposal(
                            conversation_id=conversation_id,
                            message_id=None,
                            tool_name=tool_name,
                            tool_use_id=tool_use_id,
                            tool_input=tool_input,
                        )
                        proposal_id = proposal.id

                    # Send tool_use event to client
                    await websocket.send_json({
                        "type": "tool_use",
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "tool_use_id": tool_use_id,
                        "proposal_id": proposal_id,
                    })

                    # Add to tool_use_blocks for persistence
                    tool_use_blocks.append({
                        "id": tool_use_id,
                        "name": tool_name,
                        "input": tool_input,
                        "proposal_id": proposal_id,
                    })

                    # Reset
                    current_tool_use = None
                    current_tool_input_json = []

            elif event_type == "message_delta":
                # Check stop_reason for logging
                stop_reason = event.get("delta", {}).get("stop_reason")
                if stop_reason:
                    logger.debug("Stream stop_reason: %s", stop_reason)

            elif event_type == "message_stop":
                # Stream complete
                pass

    except asyncio.TimeoutError:
        await websocket.send_json({
            "type": "error",
            "message": "Response timeout (60s)",
        })
        return
    except asyncio.CancelledError:
        # Stream was cancelled by client
        logger.info(f"Stream cancelled for conversation {conversation_id}")
        raise

    # If tool_use blocks were detected, send tool_results and continue conversation
    if tool_use_blocks:
        logger.info(
            "Tool use detected, sending tool_results continuation. "
            "tool_use_blocks=%s",
            tool_use_blocks,
        )

        # Build tool_results
        import json as json_module
        tool_results: list[dict[str, Any]] = []
        for tu in tool_use_blocks:
            tool_name = tu.get("name", "")
            tool_use_id = tu.get("id", "")
            proposal_id = tu.get("proposal_id")

            if tool_name == "generate_report":
                result_content = "Report generation queued."
            elif proposal_id:
                result_content = f"Proposal #{proposal_id} created. Awaiting operator approval."
            else:
                result_content = "Action acknowledged."

            tool_results.append({
                "tool_use_id": tool_use_id,
                "content": result_content,
            })

        # Build the assistant message with tool_use content blocks
        assistant_content: list[dict[str, Any]] = []
        # Add any text content first
        if full_content_parts:
            assistant_content.append({
                "type": "text",
                "text": "".join(full_content_parts),
            })
        # Add tool_use blocks
        for tu in tool_use_blocks:
            assistant_content.append({
                "type": "tool_use",
                "id": tu.get("id", ""),
                "name": tu.get("name", ""),
                "input": tu.get("input", {}),
            })

        # Build continuation messages
        continuation_messages = list(messages)
        continuation_messages.append({
            "role": "assistant",
            "content": assistant_content,
        })

        # Log the exact messages being sent
        logger.info(
            "send_with_tool_results: messages=%s",
            json_module.dumps(continuation_messages, indent=2, default=str)[:2000],
        )
        logger.info(
            "send_with_tool_results: tool_results=%s",
            json_module.dumps(tool_results, indent=2),
        )

        try:
            continuation_response, continuation_usage = await app_state.ai_client.send_with_tool_results(
                continuation_messages,
                full_system,
                ARGUS_TOOLS,
                tool_results,
            )

            logger.info(
                "Continuation response received: type=%s, keys=%s",
                continuation_response.get("type"),
                list(continuation_response.keys()),
            )

            # Extract continuation text content
            if continuation_response.get("type") != "error":
                for block in continuation_response.get("content", []):
                    if block.get("type") == "text":
                        continuation_text = block.get("text", "")
                        if continuation_text:
                            full_content_parts.append(continuation_text)
                            # Stream the continuation text to the client
                            await websocket.send_json({
                                "type": "token",
                                "content": continuation_text,
                            })
            else:
                logger.error(
                    "Continuation response error: %s",
                    continuation_response.get("message", "Unknown error"),
                )

        except Exception as e:
            logger.exception(
                "Error in send_with_tool_results continuation: %s", e
            )
            # Don't fail the whole stream, just log and continue
            await websocket.send_json({
                "type": "error",
                "message": f"Tool result continuation failed: {e}",
            })

    # Send stream_end
    full_content = "".join(full_content_parts)
    await websocket.send_json({
        "type": "stream_end",
        "full_content": full_content,
    })

    # Persist assistant message
    await app_state.conversation_manager.add_message(
        conversation_id,
        "assistant",
        full_content,
        tool_use_data=tool_use_blocks if tool_use_blocks else None,
    )

    # Record usage (approximate for streaming)
    if app_state.usage_tracker is not None and model:
        # Estimate tokens from content length
        input_tokens = len(full_system) // 4 + sum(len(m.get("content", "")) // 4 for m in messages)
        output_tokens = len(full_content) // 4
        cost = (
            (input_tokens / 1_000_000) * 15.0 +
            (output_tokens / 1_000_000) * 75.0
        )
        await app_state.usage_tracker.record_usage(
            conversation_id,
            input_tokens,
            output_tokens,
            model,
            cost,
        )


def _build_strategies_info(state: AppState) -> list[dict[str, Any]] | None:
    """Build strategies info for system prompt.

    Args:
        state: Application state.

    Returns:
        List of strategy info dicts, or None if no strategies.
    """
    if not state.strategies:
        return None

    strategies_info: list[dict[str, Any]] = []
    for strategy_id, strategy in state.strategies.items():
        config = getattr(strategy, "_config", None)
        if config is None:
            continue

        info: dict[str, Any] = {
            "name": getattr(config, "name", strategy_id),
        }

        time_window = getattr(config, "time_window_display", None)
        if time_window:
            info["window"] = time_window

        desc = getattr(config, "description_short", None)
        if desc:
            info["mechanic"] = desc[:100]

        strategies_info.append(info)

    return strategies_info if strategies_info else None


def _build_system_config_info(state: AppState) -> dict[str, Any] | None:
    """Build system config info for system prompt.

    Args:
        state: Application state.

    Returns:
        Config info dict, or None if no config.
    """
    if state.config is None:
        return None

    config_info: dict[str, Any] = {}

    # Risk limits from risk manager config
    if state.risk_manager is not None:
        risk_config = getattr(state.risk_manager, "_config", None)
        if risk_config is not None:
            account_config = getattr(risk_config, "account", None)
            if account_config is not None:
                config_info["risk_limits"] = {
                    "daily_loss_limit_pct": getattr(account_config, "daily_loss_limit_pct", 0.03),
                    "max_concurrent_positions": getattr(account_config, "max_concurrent_positions", 5),
                }

    if state.orchestrator is not None:
        regime = getattr(state.orchestrator, "current_regime", None)
        if regime is not None:
            config_info["regime"] = str(regime)

    return config_info if config_info else None
