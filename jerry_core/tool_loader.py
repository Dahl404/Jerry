#!/usr/bin/env python3
"""Jerry — Tool Package Loader

Loads tool definitions from .tool files in jerry_workspace/tools/<package_name>/.
Builds llama-server compatible tool definitions based on assigned tool packs.
"""

import os
import json
from typing import Dict, List, Optional
from .config import JERRY_BASE

TOOLS_DIR = os.path.join(JERRY_BASE, "tools")


def load_tool_package(package_name: str) -> List[Dict]:
    """Load all .tool files from a package directory.
    
    Args:
        package_name: Name of the tool package (subdirectory in tools/)
    
    Returns:
        List of llama-server compatible tool definitions
    """
    package_dir = os.path.join(TOOLS_DIR, package_name)
    if not os.path.isdir(package_dir):
        return []
    
    tools = []
    for filename in sorted(os.listdir(package_dir)):
        if not filename.endswith('.tool'):
            continue
        filepath = os.path.join(package_dir, filename)
        try:
            with open(filepath, 'r') as f:
                tool_def = json.load(f)
            # Convert to llama-server format
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_def["name"],
                    "description": tool_def["description"],
                    "parameters": {
                        "type": "object",
                        "properties": tool_def.get("parameters", {}),
                        "required": tool_def.get("required", [])
                    }
                }
            })
        except Exception as e:
            print(f"Error loading tool {filepath}: {e}")
    
    return tools


def load_tools_for_packs(pack_names: List[str]) -> List[Dict]:
    """Load tools from multiple packages.

    Args:
        pack_names: List of package names to load

    Returns:
        Combined list of tool definitions
    """
    all_tools = []
    for pack in pack_names:
        all_tools.extend(load_tool_package(pack))
    return all_tools


def load_prompts_for_packs(pack_names: List[str]) -> str:
    """Load bundled prompt instructions from multiple packages.

    Each package can have a prompt_<name>.py file with AGENT_PROMPT variable.
    These are concatenated and returned as a single string.

    Args:
        pack_names: List of package names

    Returns:
        Combined prompt string (empty if no prompts found)
    """
    prompts = []
    for pack in pack_names:
        try:
            module = __import__(f"jerry_core.prompt_{pack}", fromlist=["AGENT_PROMPT"])
            prompt = getattr(module, "AGENT_PROMPT", "")
            if prompt:
                prompts.append(prompt)
        except (ImportError, AttributeError):
            pass
    return "\n".join(prompts)

def get_tool_catalog_for_packs(pack_names: List[str]) -> Dict:
    """Build tool catalog (for help tool) from loaded packages.
    
    Args:
        pack_names: List of package names
    
    Returns:
        Dict mapping tool name → catalog entry
    """
    catalog = {}
    for pack in pack_names:
        package_dir = os.path.join(TOOLS_DIR, pack)
        if not os.path.isdir(package_dir):
            continue
        for filename in os.listdir(package_dir):
            if not filename.endswith('.tool'):
                continue
            filepath = os.path.join(package_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    tool_def = json.load(f)
                params_desc = {}
                for pname, pdef in tool_def.get("parameters", {}).items():
                    ptype = pdef.get("type", "str")
                    pdesc = pdef.get("description", "")
                    params_desc[pname] = f"{ptype} - {pdesc}" if pdesc else ptype
                
                catalog[tool_def["name"]] = {
                    "description": tool_def["description"],
                    "params": params_desc,
                    "example": f"{tool_def['name']}({', '.join(tool_def.get('required', []))})"
                }
            except Exception:
                pass
    return catalog


def list_available_packages() -> List[str]:
    """List all available tool packages."""
    if not os.path.isdir(TOOLS_DIR):
        return []
    return [d for d in os.listdir(TOOLS_DIR) 
            if os.path.isdir(os.path.join(TOOLS_DIR, d))]


def get_package_tool_names(package_name: str) -> List[str]:
    """Get list of tool names in a package."""
    package_dir = os.path.join(TOOLS_DIR, package_name)
    if not os.path.isdir(package_dir):
        return []
    return [f.replace('.tool', '') for f in os.listdir(package_dir) 
            if f.endswith('.tool')]
