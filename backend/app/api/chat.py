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
from sqlmodel import Session
import json
import openai
from openai import OpenAI

from app.core.config import settings
from app.core.database import get_session
from app.models.user import User
from app.services.rag import RAGService
from app.services.embeddings import default_embedding_service
from app.services.openai_prompts import (
    FUNCTION_SCHEMAS,
    build_system_prompt_with_context,
    validate_function_call,
)
from app.services.tools import execute_tool, ToolExecutionError
from app.utils.security import get_current_user


router = APIRouter(prefix="/api/chat", tags=["chat"])


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
        default=5,
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
    user: User = Depends(get_current_user),
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
        # Initialize RAG service
        rag_service = RAGService(
            db=db,
            embedding_service=default_embedding_service,
        )
        
        # Step 1: Retrieve relevant context using RAG
        retrieved_context = rag_service.search(
            query=request.message,
            user_id=user.id or 0,  # type: ignore
            source_type=request.source_type,
            top_k=request.max_context_chunks,
        )
        
        # Step 2: Build system prompt with retrieved context
        system_prompt = build_system_prompt_with_context(
            retrieved_context=retrieved_context,
            max_context_tokens=4000,
        )
        
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
        
        # Step 4: Call OpenAI Chat Completion
        if request.stream:
            # Return streaming response
            return StreamingResponse(
                _stream_chat_response(
                    messages=messages,
                    retrieved_context=retrieved_context,
                ),
                media_type="text/event-stream",
            )
        else:
            # Non-streaming response
            response = openai_client.chat.completions.create(
                model=settings.openai_chat_model,
                messages=messages,  # type: ignore
                functions=FUNCTION_SCHEMAS,  # type: ignore
                function_call="auto",  # type: ignore
                temperature=0.7,
                max_tokens=1000,
            )
            
            choice = response.choices[0]
            finish_reason = choice.finish_reason
            
            # Check if model wants to call a function
            if choice.message.function_call:
                function_name = choice.message.function_call.name
                function_args_str = choice.message.function_call.arguments
                
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
                
                return ChatResponse(
                    message=choice.message.content or "",
                    sources=retrieved_context,
                    function_call={
                        "name": function_name,
                        "arguments": function_args,
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
    messages: list[dict[str, str]],
    retrieved_context: list[dict[str, Any]],
) -> AsyncIterator[str]:
    """
    Stream chat response using Server-Sent Events (SSE).
    
    Args:
        messages: Messages to send to OpenAI
        retrieved_context: Retrieved sources for citation
        
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
        
        # Stream the OpenAI response
        stream = openai_client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=messages,  # type: ignore
            functions=FUNCTION_SCHEMAS,  # type: ignore
            function_call="auto",  # type: ignore
            temperature=0.7,
            max_tokens=1000,
            stream=True,
        )
        
        function_call_name = None
        function_call_args = ""
        
        for chunk in stream:
            choice = chunk.choices[0]
            
            # Check for function call
            if choice.delta.function_call:
                if choice.delta.function_call.name:
                    function_call_name = choice.delta.function_call.name
                if choice.delta.function_call.arguments:
                    function_call_args += choice.delta.function_call.arguments
            
            # Regular content
            elif choice.delta.content:
                content_event = {
                    "type": "content",
                    "data": choice.delta.content,
                }
                yield f"data: {json.dumps(content_event)}\n\n"
            
            # Check finish reason
            if choice.finish_reason:
                if choice.finish_reason == "function_call" and function_call_name:
                    # Parse and validate function call
                    try:
                        function_args = json.loads(function_call_args)
                        is_valid, error_msg = validate_function_call(
                            function_call_name,
                            function_args,
                        )
                        
                        if is_valid:
                            function_event = {
                                "type": "function_call",
                                "data": {
                                    "name": function_call_name,
                                    "arguments": function_args,
                                },
                            }
                            yield f"data: {json.dumps(function_event)}\n\n"
                        else:
                            error_event = {
                                "type": "error",
                                "data": f"Invalid function call: {error_msg}",
                            }
                            yield f"data: {json.dumps(error_event)}\n\n"
                    except json.JSONDecodeError:
                        error_event = {
                            "type": "error",
                            "data": "Invalid function arguments from model",
                        }
                        yield f"data: {json.dumps(error_event)}\n\n"
                
                # Send finish event
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
    user: User = Depends(get_current_user),
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
