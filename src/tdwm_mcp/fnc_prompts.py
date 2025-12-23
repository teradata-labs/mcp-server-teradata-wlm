"""
MCP Prompt Functions for TDWM Operations

This module contains all the prompt functions that are exposed through the MCP server.
"""

import logging
from typing import Dict, Any
import mcp.types as types
from .prompt import PROMPTS

logger = logging.getLogger(__name__)


async def handle_list_prompts() -> list[types.Prompt]:
    """List available prompts."""
    logger.debug("Handling list_prompts request")
    
    prompt_list = []
    for prompt_name, prompt_info in PROMPTS.items():
        prompt_list.append(
            types.Prompt(
                name=prompt_name,
                description=prompt_info.get("description", f"Prompt: {prompt_name}"),
                arguments=prompt_info.get("arguments", [])
            )
        )
    
    return prompt_list


async def handle_get_prompt(name: str, arguments: Dict[str, str] | None) -> types.GetPromptResult:
    """Generate a prompt based on the requested type"""
    logger.debug(f"Handling get_prompt request for: {name}")
    
    if arguments is None:
        arguments = {}
    
    if name not in PROMPTS:
        raise ValueError(f"Unknown prompt: {name}")
    
    prompt_info = PROMPTS[name]
    
    # Get the prompt template
    template = prompt_info.get("template", "")
    
    # Replace placeholders with arguments
    try:
        formatted_template = template.format(**arguments)
    except KeyError as e:
        raise ValueError(f"Missing required argument for prompt '{name}': {e}")
    
    return types.GetPromptResult(
        description=prompt_info.get("description", f"Generated prompt: {name}"),
        messages=[
            types.PromptMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=formatted_template
                )
            )
        ]
    )