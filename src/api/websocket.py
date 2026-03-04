"""WebSocket endpoints for streaming queries and indexing progress."""

import json
import logging
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


def register_websockets(app: FastAPI):
    """Register WebSocket endpoints on the FastAPI app."""

    @app.websocket("/ws/query")
    async def ws_query(websocket: WebSocket):
        """Streaming RAG query via WebSocket."""
        await websocket.accept()

        try:
            while True:
                data = await websocket.receive_text()
                request = json.loads(data)

                question = request.get("question", "")
                mode = request.get("mode", "explain")
                filters = request.get("filters")
                conversation_id = request.get("conversation_id")

                engine = app.state.rag_engine
                if not engine:
                    await websocket.send_json({
                        "type": "error",
                        "message": "RAG engine not initialized",
                    })
                    continue

                # Send status update
                await websocket.send_json({
                    "type": "status",
                    "message": "Retrieving relevant context...",
                })

                # Execute query (synchronous for now)
                try:
                    result = engine.query(
                        question=question,
                        mode=mode,
                        filters=filters,
                        conversation_id=conversation_id,
                    )

                    # Send sources first
                    await websocket.send_json({
                        "type": "sources",
                        "sources": [s.model_dump() for s in result.sources],
                        "confidence": result.confidence,
                    })

                    # Send answer
                    await websocket.send_json({
                        "type": "answer",
                        "answer": result.answer,
                        "diagram": result.diagram,
                        "related_topics": result.related_topics,
                        "conversation_id": result.conversation_id,
                    })

                    # Send completion
                    await websocket.send_json({"type": "done"})

                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e),
                    })

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from /ws/query")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")

    @app.websocket("/ws/index")
    async def ws_index(websocket: WebSocket):
        """Real-time indexing progress via WebSocket."""
        await websocket.accept()

        try:
            while True:
                data = await websocket.receive_text()
                request = json.loads(data)

                action = request.get("action", "")
                path = request.get("path", "")

                pipeline = app.state.pipeline
                if not pipeline:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Pipeline not initialized",
                    })
                    continue

                if action == "ingest_directory":
                    await websocket.send_json({
                        "type": "status",
                        "message": f"Starting ingestion of {path}...",
                    })

                    def progress_cb(current, total, filename):
                        # Note: can't await in sync callback, use fire-and-forget
                        pass

                    try:
                        result = pipeline.ingest_markdown_directory(path)
                        await websocket.send_json({
                            "type": "result",
                            **result,
                        })
                        await websocket.send_json({"type": "done"})
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e),
                        })

                elif action == "stats":
                    stats = app.state.store.get_stats()
                    await websocket.send_json({
                        "type": "stats",
                        **stats,
                    })

        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected from /ws/index")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
