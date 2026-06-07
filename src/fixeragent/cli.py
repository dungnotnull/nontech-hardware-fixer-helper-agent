"""CLI entry point for FixerAgent."""

from __future__ import annotations

import json
from pathlib import Path

import click
from loguru import logger

from fixeragent.agents import FixerAgent
from fixeragent.config import configure_logging
from fixeragent.models import LLMConfig, LLMProvider


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.option("--provider", type=click.Choice(["claude", "openai", "gemini", "local"]), default="claude")
@click.option("--model", default="")
@click.option("--api-key", default="")
def main(verbose: bool, provider: str, model: str, api_key: str) -> None:
    """FixerAgent — AI repair assistant for home appliances."""
    configure_logging()
    if verbose:
        logger.level("DEBUG")
    ctx = click.get_current_context()
    ctx.ensure_object(dict)
    ctx.obj["llm_config"] = LLMConfig(
        provider=LLMProvider(provider),
        model=model or ("claude-sonnet-4-6" if provider == "claude" else ""),
        api_key=api_key or None,
    )


@main.command()
@click.option("--image", "-i", type=click.Path(exists=True), help="Photo of the broken device.")
@click.option("--describe", "-d", default="", help="Text description of the problem.")
@click.option("--device-hint", default="", help="Hint about device type/brand.")
@click.option("--json-out", is_flag=True, help="Output raw JSON instead of markdown.")
@click.pass_context
def diagnose(ctx: click.Context, image: str | None, describe: str, device_hint: str, json_out: bool) -> None:
    """Diagnose a device and generate a repair guide."""
    agent = FixerAgent(llm_config=ctx.obj["llm_config"])
    result = agent.diagnose(
        image_path=image,
        description=describe,
        device_hint=device_hint,
        llm_config=ctx.obj["llm_config"],
    )

    if json_out:
        click.echo(result.model_dump_json(indent=2))
        return

    if result.status in ("escalated", "needs_input", "needs_clarification", "error"):
        click.echo(f"[{result.status.upper()}] {result.message or 'No message'}")
        if result.safety and result.safety.warnings:
            for w in result.safety.warnings:
                click.echo(f"  ⚠️  {w}")
        return

    if result.guide:
        click.echo(result.guide.to_markdown())
        click.echo(f"\n💡 Session ID: {result.session_id}")
        click.echo("Run: fixer feedback --session {id} --outcome fixed|partial|failed")


@main.command()
@click.option("--session", required=True, help="Diagnosis session ID.")
@click.option("--outcome", type=click.Choice(["fixed", "partial", "failed"]), required=True)
@click.option("--notes", default="", help="Additional notes.")
@click.option("--skill", type=click.Choice(["beginner", "intermediate", "advanced"]), default="beginner")
@click.option("--time-min", type=int, default=None, help="Actual time spent in minutes.")
@click.pass_context
def feedback(
    ctx: click.Context,
    session: str,
    outcome: str,
    notes: str,
    skill: str,
    time_min: int | None,
) -> None:
    """Submit feedback on a previous repair attempt."""
    agent = FixerAgent(llm_config=ctx.obj["llm_config"])
    resp = agent.feedback(session, outcome, notes)
    if resp["acknowledged"]:
        click.echo(f"✅ Feedback recorded for session {session}: {outcome}")
    else:
        click.echo(f"❌ Failed to record feedback: {resp.get('error', 'unknown error')}")


@main.command()
@click.argument("pdf_paths", nargs=-1, type=click.Path(exists=True))
@click.option("--directory", "-d", type=click.Path(file_okay=False), help="Ingest all PDFs in directory.")
def ingest(pdf_paths: tuple[str, ...], directory: str | None) -> None:
    """Ingest PDF manuals into the knowledge base."""
    from fixeragent.tools.rag_engine import RAGEngine
    rag = RAGEngine()
    if directory:
        rag.ingest_directory(directory)
    for pdf in pdf_paths:
        rag.add_pdf(pdf)
    rag.persist()
    click.echo("📚 PDF ingestion complete.")


@main.command()
def brain_reload() -> None:
    """Reload SECOND-KNOWLEDGE-BRAIN.md into the vector index."""
    from fixeragent.tools.rag_engine import RAGEngine
    rag = RAGEngine()
    rag.load_knowledge_brain()
    rag.persist()
    click.echo("🧠 Knowledge brain reloaded.")


@main.command()
def health() -> None:
    """Check system health and configuration."""
    from fixeragent.config import get_settings
    settings = get_settings()
    status = {
        "version": "0.1.0",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "chroma_persist_dir": settings.chroma_persist_dir,
        "knowledge_brain_path": settings.knowledge_brain_path,
        "feedback_log_path": settings.feedback_log_path,
    }
    click.echo(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()