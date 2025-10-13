"""
Chat API endpoint with RAG, function calling, and streaming support.

This module provides the main chat interface for the Financial Advisor AI agent.
It integrates:
- RAG (Retrieval Augmented Generation) for context retrieval
- OpenAI Chat Completion API with function calling
- Server-Sent Events (SSE) for streaming responses
- Prompt injection protection
"""

from typing import Any, AsyncIterator, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import json
import logging
import openai
from openai import OpenAI

from app.core.config import settings
from app.core.database import get_session
from app.models.user import User
from app.services.rag import RAGService
from app.services.embeddings import EmbeddingService
from app.services.openai_prompts import (
    FUNCTION_SCHEMAS,
    build_system_prompt_with_context,
    validate_function_call,
)
from app.services.tools import execute_tool, ToolExecutionError, HubSpotTokenExpiredError
from app.utils.security import get_current_user_from_cookie


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/chat", tags=["chat"])


# Request/Response models
class ChatMessage(BaseModel):
    """A single message in the conversation."""
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request to chat with the AI agent."""
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    conversation_history: list[ChatMessage] = Field(
        default_factory=list,
        description="Previous messages in the conversation (for context)",
    )
    source_type: Optional[str] = Field(
        None,
        description="Filter context by source type: 'emails', 'contacts', or None for all",
    )
    stream: bool = Field(
        default=True,
        description="Whether to stream the response via SSE",
    )
    max_context_chunks: int = Field(
        default=2,
        ge=1,
        le=20,
        description="Maximum number of context chunks to retrieve",
    )


class ChatResponse(BaseModel):
    """Response from the AI agent."""
    message: str = Field(..., description="AI response message")
    sources: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Retrieved sources used for context",
    )
    function_call: Optional[dict[str, Any]] = Field(
        None,
        description="Function call made by the model (if any)",
    )
    finish_reason: str = Field(
        default="stop",
        description="Why the model stopped: 'stop', 'length', 'function_call', or 'content_filter'",
    )


# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.openai_api_key)


@router.post("/", response_model=ChatResponse)
@router.post("", response_model=ChatResponse)  # Also register without trailing slash
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_session),
) -> ChatResponse | StreamingResponse:
    """
    Chat with the AI agent using RAG and function calling.
    
    This endpoint:
    1. Retrieves relevant context from the user's data using semantic search
    2. Constructs a prompt with the retrieved context
    3. Calls OpenAI Chat Completion API with function calling
    4. Returns the response (streaming or non-streaming)
    
    Args:
        request: Chat request with message and options
        user: Current authenticated user
        db: Database session
        
    Returns:
        ChatResponse with AI message and sources, or StreamingResponse for SSE
    """
    try:
        # Initialize RAG service (this might fail if embeddings service fails)
        rag_service = None
        try:
            embedding_service = EmbeddingService()
            rag_service = RAGService(
                db=db,
                embedding_service=embedding_service,
            )
        except Exception as e:
            logger.warning(f"RAG service initialization failed: {e}")
            rag_service = None
        
        # Step 1: Retrieve relevant context using RAG
        retrieved_context = []
        rag_error = None
        
        if rag_service:
            try:
                retrieved_context = rag_service.search(
                    query=request.message,
                    user_id=user.id or 0,  # type: ignore
                    source_type=request.source_type,
                    top_k=request.max_context_chunks,
                )
            except Exception as e:
                # If RAG fails (e.g., OpenAI rate limit), fallback to no context
                logger.warning(f"RAG search failed, falling back to chat without context: {e}")
                rag_error = str(e)
                retrieved_context = []
        else:
            logger.info("RAG service not available, proceeding without context")
            rag_error = "RAG service initialization failed"
        
        # Step 2: Build system prompt with retrieved context (or fallback)
        if retrieved_context:
            system_prompt = build_system_prompt_with_context(
                retrieved_context=retrieved_context,
                max_context_tokens=4000,
            )
        else:
            # Fallback system prompt without context
            system_prompt = """You are a helpful financial advisor AI assistant.
            
You can help users with:
- Financial planning and advice
- Investment strategies
- Budget management
- Financial goal setting
- General financial questions

Please provide helpful, accurate, and professional financial advice. If you need specific information about the user's financial situation, ask for clarification."""
        
        # Step 3: Construct messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (for multi-turn conversations)
        for msg in request.conversation_history:
            messages.append({
                "role": msg.role,
                "content": msg.content,
            })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": request.message,
        })
        
        # Step 4: Call OpenAI Chat Completion (skip if RAG failed due to rate limit)
        if not retrieved_context and rag_error and "rate limit" in rag_error.lower():
            # If we have no context and hit rate limit, return a helpful fallback response
            logger.info("Rate limit detected in RAG, returning fallback response without API call")
            return ChatResponse(
                message="Olá! Sou seu assistente financeiro. No momento, estou com algumas limitações técnicas devido a limites de API, mas posso te ajudar com conselhos gerais sobre finanças pessoais, planejamento financeiro e investimentos. Como posso te ajudar hoje?",
                sources=[],
                function_call=None,
                finish_reason="fallback",
            )
        
        if request.stream:
            # Return streaming response
            return StreamingResponse(
                _stream_chat_response(
                    messages=messages,
                    retrieved_context=retrieved_context,
                    user=user,
                    db=db,
                ),
                media_type="text/event-stream",
            )
        else:
            # Non-streaming response
            # Convert function schemas to tools format
            tools = [
                {
                    "type": "function",
                    "function": schema,
                }
                for schema in FUNCTION_SCHEMAS
            ]
            
        # Call OpenAI without streaming for non-streaming responses
        response = openai_client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=messages,  # type: ignore
            tools=tools,  # type: ignore
            tool_choice="auto",  # type: ignore
            max_completion_tokens=4000,
        )
        
        choice = response.choices[0]
        finish_reason = choice.finish_reason
        
        # Check if model wants to call a function (new tool_calls format)
        if choice.message.tool_calls:
            # Get the first tool call
            tool_call = choice.message.tool_calls[0]
            function_obj = getattr(tool_call, "function", None)
            if function_obj:
                function_name = function_obj.name
                function_args_str = function_obj.arguments
                
                try:
                    function_args = json.loads(function_args_str)
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid function arguments from model",
                    )
                
                # Validate function call
                is_valid, error_msg = validate_function_call(function_name, function_args)
                if not is_valid:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid function call: {error_msg}",
                    )
                
                # Execute the tool
                try:
                    tool_result = await execute_tool(
                        tool_name=function_name,
                        arguments=function_args,
                        user=user,
                        db=db,
                    )
                    
                    # Format result message
                    result_message = f"✅ Tool executed: {function_name}\n\n{json.dumps(tool_result, indent=2)}"
                    
                    return ChatResponse(
                        message=result_message,
                        sources=retrieved_context,
                        function_call={
                            "name": function_name,
                            "arguments": function_args,
                            "result": tool_result,
                        },
                        finish_reason=finish_reason,
                    )
                except ToolExecutionError as e:
                    # Return error as message
                    error_message = f"❌ Tool execution failed: {str(e)}"
                    return ChatResponse(
                        message=error_message,
                        sources=retrieved_context,
                        function_call={
                            "name": function_name,
                            "arguments": function_args,
                            "error": str(e),
                        },
                        finish_reason=finish_reason,
                    )
        
        # Regular response
        return ChatResponse(
            message=choice.message.content or "",
            sources=retrieved_context,
            function_call=None,
            finish_reason=finish_reason,
        )
            
    except openai.RateLimitError as e:
        raise HTTPException(
            status_code=429,
            detail="OpenAI API rate limit exceeded. Please try again later.",
        )
    except openai.APIError as e:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI API error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}",
        )


async def _stream_chat_response(
    messages: list[dict[str, Any]],
    retrieved_context: list[dict[str, Any]],
    user: User,
    db: Session,
) -> AsyncIterator[str]:
    """
    Stream chat response using Server-Sent Events (SSE).
    
    Args:
        messages: Messages to send to OpenAI
        retrieved_context: Retrieved sources for citation
        user: Current authenticated user
        db: Database session
        
    Yields:
        SSE-formatted strings with response chunks
    """
    try:
        # First, send sources as metadata
        sources_event = {
            "type": "sources",
            "data": retrieved_context,
        }
        yield f"data: {json.dumps(sources_event)}\n\n"
        
        # Convert function schemas to tools format
        tools = [
            {
                "type": "function",
                "function": schema,
            }
            for schema in FUNCTION_SCHEMAS
        ]
        
        # Stream the OpenAI response
        stream = openai_client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=messages,  # type: ignore
            tools=tools,  # type: ignore
            tool_choice="auto",  # type: ignore
            max_completion_tokens=4000,
            stream=True,
        )
        
        # Track all tool calls (OpenAI can return multiple)
        tool_calls: dict[int, dict[str, Any]] = {}
        
        for chunk in stream:
            choice = chunk.choices[0]
            
            # Check for tool calls (new format)
            if choice.delta.tool_calls:
                for tool_call_chunk in choice.delta.tool_calls:
                    idx = tool_call_chunk.index
                    
                    # Initialize tool call entry if needed
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": "",
                            "name": "",
                            "arguments": "",
                        }
                    
                    # Accumulate tool call data
                    if hasattr(tool_call_chunk, "id") and tool_call_chunk.id:
                        tool_calls[idx]["id"] = tool_call_chunk.id
                    
                    function_obj = getattr(tool_call_chunk, "function", None)
                    if function_obj:
                        if hasattr(function_obj, "name") and function_obj.name:
                            tool_calls[idx]["name"] = function_obj.name
                        if hasattr(function_obj, "arguments") and function_obj.arguments:
                            tool_calls[idx]["arguments"] += function_obj.arguments
            
            # Regular content
            elif choice.delta.content:
                content_event = {
                    "type": "content",
                    "data": choice.delta.content,
                }
                yield f"data: {json.dumps(content_event)}\n\n"
            
            # Check finish reason
            if choice.finish_reason:
                # Process tool calls if we have any, regardless of finish_reason
                # (gpt-5-nano sometimes returns "length" even when there are tool calls)
                if tool_calls:
                    # Process all tool calls
                    assistant_tool_calls = []
                    tool_responses = []
                    
                    for idx in sorted(tool_calls.keys()):
                        tool_call = tool_calls[idx]
                        tool_call_name = tool_call["name"]
                        tool_call_id = tool_call["id"]
                        tool_call_args_str = tool_call["arguments"]
                        
                        # Parse and validate tool call
                        try:
                            function_args = json.loads(tool_call_args_str)
                            is_valid, error_msg = validate_function_call(
                                tool_call_name,
                                function_args,
                            )
                            
                            if not is_valid:
                                error_event = {
                                    "type": "error",
                                    "data": f"Invalid function call {tool_call_name}: {error_msg}",
                                }
                                yield f"data: {json.dumps(error_event)}\n\n"
                                continue
                            
                            # Notify frontend about tool execution
                            function_event = {
                                "type": "function_call",
                                "data": {
                                    "name": tool_call_name,
                                    "arguments": function_args,
                                },
                            }
                            yield f"data: {json.dumps(function_event)}\n\n"
                            
                            # Execute the tool
                            tool_result = await execute_tool(
                                tool_name=tool_call_name,
                                arguments=function_args,
                                user=user,
                                db=db,
                            )
                            
                            # Store for message history
                            assistant_tool_calls.append({
                                "id": tool_call_id or f"call_{idx}",
                                "type": "function",
                                "function": {
                                    "name": tool_call_name,
                                    "arguments": json.dumps(function_args),
                                }
                            })
                            
                            tool_responses.append({
                                "role": "tool",
                                "tool_call_id": tool_call_id or f"call_{idx}",
                                "name": tool_call_name,
                                "content": json.dumps(tool_result),
                            })
                            
                        except json.JSONDecodeError:
                            error_event = {
                                "type": "error",
                                "data": f"Invalid function arguments for {tool_call_name}",
                            }
                            yield f"data: {json.dumps(error_event)}\n\n"
                        except HubSpotTokenExpiredError as e:
                            # Special handling for expired HubSpot token
                            reconnect_event = {
                                "type": "hubspot_reconnect_required",
                                "data": str(e),
                            }
                            yield f"data: {json.dumps(reconnect_event)}\n\n"
                        except Exception as e:
                            error_event = {
                                "type": "error",
                                "data": f"Error executing {tool_call_name}: {str(e)}",
                            }
                            yield f"data: {json.dumps(error_event)}\n\n"
                    
                    if assistant_tool_calls:
                        # Add assistant message with all tool calls
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": assistant_tool_calls
                        })
                        
                        # Add all tool responses
                        for tool_response in tool_responses:
                            messages.append(tool_response)
                        
                        max_iterations = 10
                        iteration = 0
                        
                        logger.info(f"Starting iterative tool execution loop (max {max_iterations} iterations)")
                        
                        while iteration < max_iterations:
                            iteration += 1
                            logger.info(f"Iteration {iteration}/{max_iterations}: Calling LLM again...")
                            
                            try:
                                # Call LLM again with updated conversation
                                followup_stream = openai_client.chat.completions.create(
                                    model=settings.openai_chat_model,
                                    messages=messages,  # type: ignore
                                    tools=tools,  # type: ignore
                                    tool_choice="auto",  # type: ignore
                                    max_completion_tokens=4000,
                                    stream=True,
                                )
                                
                                # Track tool calls in this iteration
                                followup_tool_calls: dict[int, dict[str, Any]] = {}
                                has_content = False
                                
                                # Process the followup stream
                                for followup_chunk in followup_stream:
                                    followup_choice = followup_chunk.choices[0]
                                    
                                    # Check for more tool calls
                                    if followup_choice.delta.tool_calls:
                                        for tool_call_chunk in followup_choice.delta.tool_calls:
                                            idx = tool_call_chunk.index
                                            
                                            if idx not in followup_tool_calls:
                                                followup_tool_calls[idx] = {
                                                    "id": "",
                                                    "name": "",
                                                    "arguments": "",
                                                }
                                            
                                            if hasattr(tool_call_chunk, "id") and tool_call_chunk.id:
                                                followup_tool_calls[idx]["id"] = tool_call_chunk.id
                                            
                                            function_obj = getattr(tool_call_chunk, "function", None)
                                            if function_obj:
                                                if hasattr(function_obj, "name") and function_obj.name:
                                                    followup_tool_calls[idx]["name"] = function_obj.name
                                                if hasattr(function_obj, "arguments") and function_obj.arguments:
                                                    followup_tool_calls[idx]["arguments"] += function_obj.arguments
                                    
                                    # Regular content
                                    elif followup_choice.delta.content:
                                        has_content = True
                                        content_event = {
                                            "type": "content",
                                            "data": followup_choice.delta.content,
                                        }
                                        yield f"data: {json.dumps(content_event)}\n\n"
                                    
                                    # Check finish reason
                                    if followup_choice.finish_reason:
                                        logger.info(f"Iteration {iteration} finish_reason: {followup_choice.finish_reason}")
                                        # Process tool calls if we have any, regardless of finish_reason
                                        if followup_tool_calls:
                                            logger.info(f"Iteration {iteration}: Found {len(followup_tool_calls)} more tool calls to execute")
                                            # More tools to execute! Process them
                                            followup_assistant_calls = []
                                            followup_tool_responses = []
                                            
                                            for idx in sorted(followup_tool_calls.keys()):
                                                tool_call = followup_tool_calls[idx]
                                                tool_call_name = tool_call["name"]
                                                tool_call_id = tool_call["id"]
                                                tool_call_args_str = tool_call["arguments"]
                                                
                                                try:
                                                    function_args = json.loads(tool_call_args_str)
                                                    is_valid, error_msg = validate_function_call(
                                                        tool_call_name,
                                                        function_args,
                                                    )
                                                    
                                                    if not is_valid:
                                                        error_event = {
                                                            "type": "error",
                                                            "data": f"Invalid function call {tool_call_name}: {error_msg}",
                                                        }
                                                        yield f"data: {json.dumps(error_event)}\n\n"
                                                        continue
                                                    
                                                    # Notify frontend
                                                    function_event = {
                                                        "type": "function_call",
                                                        "data": {
                                                            "name": tool_call_name,
                                                            "arguments": function_args,
                                                        },
                                                    }
                                                    yield f"data: {json.dumps(function_event)}\n\n"
                                                    
                                                    # Execute
                                                    tool_result = await execute_tool(
                                                        tool_name=tool_call_name,
                                                        arguments=function_args,
                                                        user=user,
                                                        db=db,
                                                    )
                                                    
                                                    # Store
                                                    followup_assistant_calls.append({
                                                        "id": tool_call_id or f"call_{idx}",
                                                        "type": "function",
                                                        "function": {
                                                            "name": tool_call_name,
                                                            "arguments": json.dumps(function_args),
                                                        }
                                                    })
                                                    
                                                    followup_tool_responses.append({
                                                        "role": "tool",
                                                        "tool_call_id": tool_call_id or f"call_{idx}",
                                                        "name": tool_call_name,
                                                        "content": json.dumps(tool_result),
                                                    })
                                                    
                                                except HubSpotTokenExpiredError as e:
                                                    # Special handling for expired HubSpot token
                                                    reconnect_event = {
                                                        "type": "hubspot_reconnect_required",
                                                        "data": str(e),
                                                    }
                                                    yield f"data: {json.dumps(reconnect_event)}\n\n"
                                                except Exception as e:
                                                    error_event = {
                                                        "type": "error",
                                                        "data": f"Error executing {tool_call_name}: {str(e)}",
                                                    }
                                                    yield f"data: {json.dumps(error_event)}\n\n"
                                            
                                            # Add to conversation and continue loop
                                            if followup_assistant_calls:
                                                messages.append({
                                                    "role": "assistant",
                                                    "content": None,
                                                    "tool_calls": followup_assistant_calls
                                                })
                                                for tool_response in followup_tool_responses:
                                                    messages.append(tool_response)
                                                break
                                        else:
                                            finish_event = {
                                                "type": "finish",
                                                "data": followup_choice.finish_reason,
                                            }
                                            yield f"data: {json.dumps(finish_event)}\n\n"
                                            return
                                
                            except Exception as e:
                                error_event = {
                                    "type": "error",
                                    "data": f"Error in tool loop: {str(e)}",
                                }
                                yield f"data: {json.dumps(error_event)}\n\n"
                                break
                else:
                    # No tool calls, just regular response - send finish event
                    finish_event = {
                        "type": "finish",
                        "data": choice.finish_reason,
                    }
                    yield f"data: {json.dumps(finish_event)}\n\n"
                break
        
    except openai.RateLimitError:
        error_event = {
            "type": "error",
            "data": "OpenAI API rate limit exceeded. Please try again later.",
        }
        yield f"data: {json.dumps(error_event)}\n\n"
    except openai.APIError as e:
        error_event = {
            "type": "error",
            "data": f"OpenAI API error: {str(e)}",
        }
        yield f"data: {json.dumps(error_event)}\n\n"
    except Exception as e:
        error_event = {
            "type": "error",
            "data": f"Internal error: {str(e)}",
        }
        yield f"data: {json.dumps(error_event)}\n\n"


@router.get("/health")
async def chat_health() -> dict[str, str]:
    """Health check for chat service."""
    return {"status": "healthy", "service": "chat"}


class ExecuteToolRequest(BaseModel):
    """Request to execute a tool."""
    tool_name: str = Field(..., description="Name of the tool to execute")
    arguments: dict[str, Any] = Field(..., description="Tool arguments")


class ExecuteToolResponse(BaseModel):
    """Response from tool execution."""
    status: str = Field(..., description="Execution status: 'success' or 'error'")
    result: Optional[dict[str, Any]] = Field(default=None, description="Tool execution result")
    error: Optional[str] = Field(default=None, description="Error message if failed")


@router.post("/execute-tool", response_model=ExecuteToolResponse)
async def execute_tool_endpoint(
    request: ExecuteToolRequest,
    user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_session),
) -> ExecuteToolResponse:
    """
    Execute a tool (action) after the model suggests it.
    
    This endpoint should be called after the chat endpoint returns a function_call.
    It validates and executes the actual action (send email, schedule event, etc.).
    
    Args:
        request: Tool name and arguments
        user: Current authenticated user
        db: Database session
        
    Returns:
        ExecuteToolResponse with result or error
    """
    try:
        # Validate function call
        is_valid, error_msg = validate_function_call(request.tool_name, request.arguments)
        if not is_valid:
            return ExecuteToolResponse(
                status="error",
                error=f"Invalid arguments: {error_msg}",
            )
        
        # Execute the tool
        result = await execute_tool(
            tool_name=request.tool_name,
            arguments=request.arguments,
            user=user,
            db=db,
        )
        
        return ExecuteToolResponse(
            status="success",
            result=result,
        )
        
    except ToolExecutionError as e:
        return ExecuteToolResponse(
            status="error",
            error=str(e),
        )
    except Exception as e:
        return ExecuteToolResponse(
            status="error",
            error=f"Internal error: {str(e)}",
        )
