"""Enhanced API routes with provider registry integration."""

import time

import structlog
from fastapi import APIRouter, Header, Request

from ..application.chat_completion import ChatCompletionUseCase
from ..application.provider_registry import ProviderRegistry
from ..domain.entities import ChatRequest, Message, Tool
from .dtos import (
    ChatCompletionRequestDTO,
    ChatCompletionResponseDTO,
    ChoiceDTO,
    MessageDTO,
    ModelDTO,
    ModelListDTO,
    UsageDTO,
)

logger = structlog.get_logger()


class APIRoutes:
    """Enhanced API routes with provider registry."""

    def __init__(
        self,
        chat_completion_use_case: ChatCompletionUseCase,
        provider_registry: ProviderRegistry,
    ):
        """Initialize routes with dependencies.

        Args:
            chat_completion_use_case: Chat completion use case
            provider_registry: Provider registry for model routing
        """
        self._chat_use_case = chat_completion_use_case
        self._registry = provider_registry
        self.router = APIRouter()

        # Register routes
        self.router.add_api_route(
            "/v1/chat/completions",
            self.chat_completions,
            methods=["POST"],
            summary="Chat completions with provider registry",
            description="Execute chat completion using registered providers based on model",
        )
        self.router.add_api_route(
            "/v1/models",
            self.list_models,
            methods=["GET"],
            summary="List available models",
            description="List all models available from registered providers",
        )

    async def chat_completions(
        self,
        request_dto: ChatCompletionRequestDTO,
        request: Request,
        authorization: str | None = Header(None),
    ) -> ChatCompletionResponseDTO:
        """Chat completions endpoint with provider registry.

        Args:
            request_dto: Chat completion request
            request: FastAPI request object
            authorization: Authorization header

        Returns:
            Chat completion response

        Raises:
            HTTPException: For various error conditions (handled by middleware)
        """
        logger.info(
            "chat_completion_request",
            model=request_dto.model,
            message_count=len(request_dto.messages),
            has_tools=request_dto.tools is not None,
            temperature=request_dto.temperature,
            max_tokens=request_dto.max_tokens,
        )

        # Extract token
        token = None
        if authorization:
            token = authorization.replace("Bearer ", "").strip()

        # Convert DTO to domain entity
        messages = [
            Message(
                role=msg.role,
                content=msg.content,
                name=msg.name,
                tool_calls=[
                    # Convert tool calls if present
                    # This would need proper ToolCall entity conversion
                ] if msg.tool_calls else None,
                tool_call_id=msg.tool_call_id,
            )
            for msg in request_dto.messages
        ]

        tools = None
        if request_dto.tools:
            tools = [
                Tool(
                    name=tool.function["name"],
                    description=tool.function.get("description", ""),
                    parameters=tool.function.get("parameters", {}),
                )
                for tool in request_dto.tools
            ]

        chat_request = ChatRequest(
            messages=messages,
            model=request_dto.model,
            tools=tools,
            temperature=request_dto.temperature,
            max_tokens=request_dto.max_tokens,
        )

        # Execute via registry (no hardcoded provider)
        response = await self._chat_use_case.execute(
            chat_request, auth_token=token
        )

        logger.info(
            "chat_completion_response",
            response_id=response.id,
            model=response.model,
            finish_reason=response.finish_reason,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

        # Convert to DTO and return
        return self._build_response_dto(response)

    async def list_models(self) -> ModelListDTO:
        """List all available models from registry.

        Returns:
            List of available models from all registered providers
        """
        logger.info("models_list_request")

        providers = self._registry.list_providers()
        models = []

        for provider_name, model_list in providers.items():
            for model in model_list:
                models.append(
                    ModelDTO(
                        id=model,
                        object="model",
                        owned_by=provider_name,
                    )
                )

        logger.info(
            "models_list_response",
            total_models=len(models),
            providers=list(providers.keys()),
        )

        return ModelListDTO(object="list", data=models)

    def _build_response_dto(self, response) -> ChatCompletionResponseDTO:
        """Build response DTO from domain response.

        Args:
            response: Domain ChatResponse entity

        Returns:
            ChatCompletionResponseDTO
        """
        # Convert tool calls if present
        tool_calls = None
        if response.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": tc.arguments,
                    },
                }
                for tc in response.tool_calls
            ]

        message_dto = MessageDTO(
            role="assistant",
            content=response.content,
            tool_calls=tool_calls,
        )

        return ChatCompletionResponseDTO(
            id=response.id,
            created=int(time.time()),
            model=response.model,
            choices=[
                ChoiceDTO(
                    index=0,
                    message=message_dto,
                    finish_reason=response.finish_reason,
                )
            ],
            usage=UsageDTO(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            ),
        )
