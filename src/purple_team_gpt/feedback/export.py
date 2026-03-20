"""JSONL export utilities for fine-tuning data preparation.

This module provides functions to export high-rated feedback entries
to JSONL format suitable for LLM fine-tuning.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from purple_team_gpt.feedback.models import AgentType, FeedbackEntry
from purple_team_gpt.feedback.store import FeedbackStore

logger = logging.getLogger(__name__)


def format_for_fine_tuning(
    entry: FeedbackEntry,
    include_context: bool = False,
    system_prompt: Optional[str] = None,
) -> dict:
    """Format a feedback entry for fine-tuning.
    
    Creates a conversation format suitable for OpenAI-style fine-tuning.
    
    Args:
        entry: The feedback entry to format.
        include_context: Whether to include context in the prompt.
        system_prompt: Optional system prompt to prepend.
        
    Returns:
        Dictionary in fine-tuning format with messages array.
    """
    messages = []
    
    # Add system prompt if provided
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # Add system message based on agent type
    agent_system_prompts = {
        AgentType.RED: "You are a Red Team cybersecurity agent specialized in offensive security operations.",
        AgentType.BLUE: "You are a Blue Team cybersecurity agent specialized in defensive security operations.",
        AgentType.ORCHESTRATOR: "You are a Purple Team orchestrator coordinating Red and Blue team activities.",
    }
    
    if not system_prompt:
        messages.append({
            "role": "system",
            "content": agent_system_prompts.get(
                entry.agent_type, 
                "You are a cybersecurity assistant."
            )
        })
    
    # Build user prompt
    user_content = entry.prompt
    if include_context and entry.context:
        try:
            context_data = json.loads(entry.context)
            context_str = json.dumps(context_data, indent=2)
            user_content = f"Context:\n{context_str}\n\n{entry.prompt}"
        except json.JSONDecodeError:
            pass
    
    messages.append({"role": "user", "content": user_content})
    messages.append({"role": "assistant", "content": entry.response})
    
    return {"messages": messages}


def export_fine_tuning_data(
    store: FeedbackStore,
    output_path: str,
    min_rating: int = 4,
    agent_type: Optional[AgentType] = None,
    include_context: bool = True,
    system_prompt: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict:
    """Export high-rated feedback to JSONL format for fine-tuning.
    
    Args:
        store: The FeedbackStore instance.
        output_path: Path to write the JSONL file.
        min_rating: Minimum rating threshold (default 4).
        agent_type: Filter by agent type (optional).
        include_context: Whether to include context in prompts.
        system_prompt: Optional custom system prompt.
        session_id: Filter by session ID (optional).
        
    Returns:
        Dictionary with export statistics.
    """
    # Get high-rated entries
    entries = store.list_feedback(
        session_id=session_id,
        agent_type=agent_type,
        min_rating=min_rating,
        limit=10000,  # Large limit to get all
    )
    
    if not entries:
        logger.warning("No high-rated feedback entries found for export")
        return {
            "success": False,
            "message": "No high-rated feedback entries found",
            "count": 0,
            "output_path": output_path,
        }
    
    # Ensure output directory exists
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write JSONL file
    count = 0
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in entries:
            formatted = format_for_fine_tuning(
                entry,
                include_context=include_context,
                system_prompt=system_prompt,
            )
            f.write(json.dumps(formatted, ensure_ascii=False) + "\n")
            count += 1
    
    logger.info(f"Exported {count} feedback entries to {output_path}")
    
    return {
        "success": True,
        "message": f"Successfully exported {count} entries",
        "count": count,
        "output_path": str(output_file.absolute()),
        "min_rating": min_rating,
        "agent_type": agent_type.value if agent_type else None,
        "session_id": session_id,
    }


def export_training_validation_split(
    store: FeedbackStore,
    output_dir: str,
    min_rating: int = 4,
    agent_type: Optional[AgentType] = None,
    validation_ratio: float = 0.1,
    include_context: bool = True,
    system_prompt: Optional[str] = None,
) -> dict:
    """Export feedback with training/validation split.
    
    Creates two JSONL files: one for training and one for validation.
    
    Args:
        store: The FeedbackStore instance.
        output_dir: Directory to write the JSONL files.
        min_rating: Minimum rating threshold (default 4).
        agent_type: Filter by agent type (optional).
        validation_ratio: Ratio of data for validation (default 0.1).
        include_context: Whether to include context in prompts.
        system_prompt: Optional custom system prompt.
        
    Returns:
        Dictionary with export statistics.
    """
    import random
    
    # Get high-rated entries
    entries = store.list_feedback(
        agent_type=agent_type,
        min_rating=min_rating,
        limit=10000,
    )
    
    if not entries:
        logger.warning("No high-rated feedback entries found for export")
        return {
            "success": False,
            "message": "No high-rated feedback entries found",
            "training_count": 0,
            "validation_count": 0,
        }
    
    # Shuffle entries
    random.shuffle(entries)
    
    # Split data
    split_idx = int(len(entries) * (1 - validation_ratio))
    training_entries = entries[:split_idx]
    validation_entries = entries[split_idx:]
    
    # Ensure output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    results = {
        "success": True,
        "training_count": 0,
        "validation_count": 0,
        "output_dir": str(output_path.absolute()),
    }
    
    # Write training file
    if training_entries:
        training_file = output_path / f"training_{timestamp}.jsonl"
        with open(training_file, "w", encoding="utf-8") as f:
            for entry in training_entries:
                formatted = format_for_fine_tuning(
                    entry,
                    include_context=include_context,
                    system_prompt=system_prompt,
                )
                f.write(json.dumps(formatted, ensure_ascii=False) + "\n")
        results["training_count"] = len(training_entries)
        results["training_file"] = str(training_file)
    
    # Write validation file
    if validation_entries:
        validation_file = output_path / f"validation_{timestamp}.jsonl"
        with open(validation_file, "w", encoding="utf-8") as f:
            for entry in validation_entries:
                formatted = format_for_fine_tuning(
                    entry,
                    include_context=include_context,
                    system_prompt=system_prompt,
                )
                f.write(json.dumps(formatted, ensure_ascii=False) + "\n")
        results["validation_count"] = len(validation_entries)
        results["validation_file"] = str(validation_file)
    
    logger.info(
        f"Exported {results['training_count']} training and "
        f"{results['validation_count']} validation entries"
    )
    
    return results