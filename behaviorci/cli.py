"""BehaviorCI CLI - Command-line interface for LLM behavior testing."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from behaviorci import __version__
from behaviorci.bundle.loader import load_bundle
from behaviorci.exceptions import BehaviorCIError
from behaviorci.providers import get_provider
from behaviorci.reporters import get_reporter
from behaviorci.runner import Runner

console = Console()
error_console = Console(stderr=True)


@click.group()
@click.version_option(version=__version__, prog_name="behaviorci")
def main() -> None:
    """BehaviorCI - CI/CD for LLM behavior.

    Prompts don't ship until behavior passes tests.
    """
    pass


@main.command()
@click.argument("path", type=click.Path(), default="bundles/example")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files")
def init(path: str, force: bool) -> None:
    """Initialize a new Behavior Bundle.

    Creates example bundle files at the specified PATH.
    """
    bundle_dir = Path(path)

    if bundle_dir.exists() and not force:
        if any(bundle_dir.iterdir()):
            error_console.print(
                f"[red]Directory '{path}' is not empty. Use --force to overwrite.[/red]"
            )
            sys.exit(1)

    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Create bundle.yaml
    bundle_yaml = bundle_dir / "bundle.yaml"
    bundle_yaml.write_text(EXAMPLE_BUNDLE_YAML)

    # Create prompt.md
    prompt_md = bundle_dir / "prompt.md"
    prompt_md.write_text(EXAMPLE_PROMPT)

    # Create dataset.jsonl
    dataset_jsonl = bundle_dir / "dataset.jsonl"
    dataset_jsonl.write_text(EXAMPLE_DATASET)

    # Create schema.json
    schema_json = bundle_dir / "schema.json"
    schema_json.write_text(EXAMPLE_SCHEMA)

    console.print(f"[green]✓[/green] Created bundle at [bold]{path}/[/bold]")
    console.print()
    console.print("Files created:")
    console.print(f"  • {bundle_yaml}")
    console.print(f"  • {prompt_md}")
    console.print(f"  • {dataset_jsonl}")
    console.print(f"  • {schema_json}")
    console.print()
    console.print("Next steps:")
    console.print(f"  1. Review and customize the bundle")
    console.print(f"  2. Validate: [bold]behaviorci validate {path}/bundle.yaml[/bold]")
    console.print(f"  3. Run: [bold]behaviorci run {path}/bundle.yaml[/bold]")


@main.command()
@click.argument("bundle_path", type=click.Path(exists=True))
def validate(bundle_path: str) -> None:
    """Validate a Behavior Bundle configuration.

    Checks that the bundle.yaml is valid and all referenced files exist.
    """
    try:
        bundle = load_bundle(bundle_path)
        config = bundle.config

        console.print(f"[green]✓[/green] Bundle is valid: [bold]{config.name}[/bold]")
        console.print()

        # Show summary
        table = Table(show_header=False, box=None)
        table.add_column("Key", style="dim")
        table.add_column("Value")

        table.add_row("Name", config.name)
        table.add_row("Version", config.version)
        table.add_row("Provider", config.provider.name)
        table.add_row("Model", config.provider.model or "(default)")
        table.add_row("Dataset", config.dataset_path)
        table.add_row("Cases", str(len(bundle.dataset)))
        table.add_row("Thresholds", str(len(config.thresholds)))

        console.print(table)

    except BehaviorCIError as e:
        error_console.print(f"[red]✗ Validation failed:[/red] {e}")
        sys.exit(1)


@main.command()
@click.argument("bundle_path", type=click.Path(exists=True))
@click.option(
    "--provider", "-p", help="Override provider (openai, anthropic, mock)"
)
@click.option("--model", "-m", help="Override model")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["console", "json", "markdown"]),
    default="console",
    help="Output format",
)
@click.option("--output", "-o", type=click.Path(), help="Write report to file")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
@click.option("--quiet", "-q", is_flag=True, help="Minimal output")
def run(
    bundle_path: str,
    provider: str | None,
    model: str | None,
    output_format: str,
    output: str | None,
    verbose: bool,
    quiet: bool,
) -> None:
    """Run a Behavior Bundle and evaluate results.

    Executes all test cases, validates outputs against contracts,
    and checks thresholds. Exit code is non-zero if thresholds fail.
    """
    try:
        bundle = load_bundle(bundle_path)
        config = bundle.config

        if not quiet:
            console.print(
                f"Running bundle: [bold]{config.name}[/bold] ({len(bundle.dataset)} cases)"
            )

        # Create provider override if specified
        provider_instance = None
        if provider:
            provider_instance = get_provider(
                provider,
                model=model or config.provider.model,
                temperature=config.provider.temperature,
                max_tokens=config.provider.max_tokens,
            )

        # Run the bundle
        runner = Runner(bundle, provider=provider_instance)
        result = asyncio.run(runner.run())

        # Generate report
        reporter = get_reporter(output_format)
        report = reporter.emit(result, verbose=verbose)

        # Output report
        if output:
            Path(output).write_text(report)
            if not quiet:
                console.print(f"Report written to: {output}")
        else:
            if output_format == "console":
                # Console reporter already prints
                console.print(report)
            else:
                # JSON/Markdown go to stdout
                print(report)

        # Exit with appropriate code
        if result.passed:
            if not quiet:
                console.print()
                console.print("[green]✓ All thresholds passed[/green]")
            sys.exit(0)
        else:
            if not quiet:
                console.print()
                console.print("[red]✗ Thresholds failed[/red]")
            sys.exit(1)

    except BehaviorCIError as e:
        error_console.print(f"[red]Error:[/red] {e}")
        sys.exit(2)


# Example bundle templates
EXAMPLE_BUNDLE_YAML = """\
name: example-bundle
version: "1.0"
description: An example Behavior Bundle for testing

prompt_path: prompt.md
dataset_path: dataset.jsonl

output_contract:
  schema_path: schema.json
  invariants:
    - "len(raw_output) < 1000"
    - "'error' not in raw_output.lower()"

thresholds:
  - metric: pass_rate
    operator: ">="
    value: 0.8

provider:
  name: mock  # Change to 'openai' or 'anthropic' for real testing
  model: null
  temperature: 0.0
"""

EXAMPLE_PROMPT = """\
You are a helpful assistant that answers questions concisely.

Question: {{ question }}

Respond with a JSON object containing:
- "answer": Your concise answer
- "confidence": A number from 0 to 1 indicating confidence

Respond only with valid JSON, no additional text.
"""

EXAMPLE_DATASET = """\
{"input": {"question": "What is 2 + 2?"}, "expected_output": {"answer": "4"}}
{"input": {"question": "What color is the sky?"}, "expected_output": {"answer": "blue"}}
{"input": {"question": "What is the capital of France?"}, "expected_output": {"answer": "Paris"}}
"""

EXAMPLE_SCHEMA = """\
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["answer", "confidence"],
  "properties": {
    "answer": {
      "type": "string",
      "minLength": 1
    },
    "confidence": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    }
  },
  "additionalProperties": false
}
"""


if __name__ == "__main__":
    main()
