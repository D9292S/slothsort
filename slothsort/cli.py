"""
Developer-grade CLI and terminal interface for SlothSort.
Designed for clean UNIX-style ergonomics, clear diffs, and safe defaults.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure UTF-8 output encoding across Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.tree import Tree

from slothsort import __version__
from slothsort.categorizer import categorize_files
from slothsort.config import SortConfig, UNDO_LOG_FILENAME, load_user_config
from slothsort.organizer import execute_organization, execute_undo, plan_organization
from slothsort.scanner import scan_directory

console = Console()

CATEGORY_ICONS: dict[str, str] = {
    "Documents": "📄",
    "Images": "🖼️ ",
    "Installers": "⚙️ ",
    "Code": "💻",
    "Data": "📊",
    "Audio": "🎵",
    "Videos": "🎬",
    "Archives": "📦",
    "Design": "🎨",
    "Duplicates": "📑",
    "Misc": "📁",
}


def render_header(source_path: Path, dest_path: Path, execute: bool, model: str) -> None:
    """Print the modern SlothSort header card."""
    mode_badge = (
        "[bold white on red] EXECUTE [/bold white on red]"
        if execute
        else "[bold white on blue] DRY-RUN [/bold white on blue]"
    )
    dest_str = f" → [bold white]{dest_path}[/bold white]" if dest_path != source_path else ""

    body = (
        f"📂 [bold]{source_path}[/bold]{dest_str}\n"
        f"⚙️  {mode_badge} [dim]Model: [bold white]{model}[/bold white] • Offline Inference[/dim]"
    )
    console.print(
        Panel(
            body,
            title="[bold green]🦥 slothsort[/bold green] [dim]v" + __version__ + "[/dim]",
            border_style="dim",
            box=box.ROUNDED,
            expand=False,
            padding=(0, 2),
        )
    )
    console.print()


def render_summary_table(plan: list, source_dir: Path, dest_dir: Path) -> None:
    """Render a clean summary table grouped by category with icons and totals."""
    table = Table(
        title="[bold]Taxonomy Breakdown[/bold]",
        title_justify="left",
        header_style="bold bright_white",
        border_style="dim",
        box=box.ROUNDED,
        padding=(0, 1),
    )

    table.add_column("Category", style="bright_cyan", width=18)
    table.add_column("Files", justify="right", style="white", width=8)
    table.add_column("Size", justify="right", style="dim", width=10)
    table.add_column("Renamed", justify="right", style="yellow", width=10)
    table.add_column("Inference", justify="right", style="dim", width=14)

    categories: dict[str, list] = {}
    for action in plan:
        categories.setdefault(action.category, []).append(action)

    total_files = len(plan)
    total_bytes = 0
    total_renamed = 0

    for cat_name, actions in sorted(categories.items()):
        icon = CATEGORY_ICONS.get(cat_name, "📁")
        cat_bytes = sum(a.source_path.stat().st_size for a in actions if a.source_path.exists())
        total_bytes += cat_bytes
        size_mb = cat_bytes / (1024 * 1024)
        size_str = f"{size_mb / 1024:.2f} GB" if size_mb >= 1024 else f"{size_mb:.1f} MB"

        renamed_count = sum(1 for a in actions if a.is_renamed)
        total_renamed += renamed_count

        ai_count = sum(1 for a in actions if a.source_type == "ai")
        dedupe_count = sum(1 for a in actions if a.source_type == "dedupe")

        if dedupe_count > 0:
            mode_badge = "[cyan]dedupe[/cyan]"
        elif ai_count > 0:
            mode_badge = f"[green]{ai_count}/{len(actions)} local[/green]"
        else:
            mode_badge = "[dim]rules[/dim]"

        table.add_row(
            f"{icon} {cat_name}",
            str(len(actions)),
            size_str,
            str(renamed_count) if renamed_count > 0 else "[dim]0[/dim]",
            mode_badge,
        )

    # Summary Totals Row
    tot_mb = total_bytes / (1024 * 1024)
    tot_size_str = f"{tot_mb / 1024:.2f} GB" if tot_mb >= 1024 else f"{tot_mb:.1f} MB"
    table.add_section()
    table.add_row(
        "[bold]Total[/bold]",
        f"[bold]{total_files}[/bold]",
        f"[dim]{tot_size_str}[/dim]",
        f"[bold yellow]{total_renamed}[/bold yellow]",
        "[dim]—[/dim]",
    )

    console.print(table)
    console.print()


def render_tree_preview(plan: list, dest_dir: Path, max_per_cat: int = 6) -> None:
    """Render a clean diff tree of planned folder hierarchy with category glyphs."""
    tree = Tree(f"📁 [bold]{dest_dir.name}/[/bold] [dim]({dest_dir.resolve()})[/dim]")

    categories: dict[str, list] = {}
    for action in plan:
        categories.setdefault(action.category, []).append(action)

    for cat_name, actions in sorted(categories.items()):
        icon = CATEGORY_ICONS.get(cat_name, "📁")
        branch = tree.add(f"[bold cyan]{icon} {cat_name}/[/bold cyan] [dim]({len(actions)} files)[/dim]")

        for action in actions[:max_per_cat]:
            reason_hint = f" [dim]• {action.reason}[/dim]" if action.reason else ""
            if action.source_type == "dedupe":
                branch.add(
                    f"[bright_black]{action.original_name}[/bright_black] [bold cyan]→[/bold cyan] [bold yellow]Duplicates/{action.target_name}[/bold yellow]{reason_hint}"
                )
            elif action.is_renamed:
                branch.add(
                    f"[bright_black]{action.original_name}[/bright_black] [bold cyan]→[/bold cyan] [bold green]{action.target_name}[/bold green]{reason_hint}"
                )
            else:
                branch.add(f"[white]{action.original_name}[/white]")

        if len(actions) > max_per_cat:
            remaining = len(actions) - max_per_cat
            branch.add(f"[dim italic]... and {remaining} more files[/dim italic]")

    console.print(
        Panel(
            tree,
            title="[bold]Proposed Directory Hierarchy[/bold]",
            title_align="left",
            border_style="dim",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )
    console.print()


class DefaultCommandGroup(click.Group):
    """
    Routes commands ergonomically:
      slothsort ~/Downloads
      slothsort ~/Downloads --execute
      slothsort --execute ~/Downloads
      slothsort undo ~/Downloads
    """

    def __init__(self, *args, **kwargs):
        self.default_command = kwargs.pop("default_command", "sort")
        super().__init__(*args, **kwargs)

    def resolve_command(self, ctx: click.Context, args: list[str]):
        if not args:
            return super().resolve_command(ctx, args)

        cmd_name = args[0]
        if cmd_name in self.commands or cmd_name in ("--help", "-h", "--version"):
            return super().resolve_command(ctx, args)

        # Prepend the default command ('sort')
        args.insert(0, self.default_command)
        return super().resolve_command(ctx, args)


@click.group(cls=DefaultCommandGroup, default_command="sort")
@click.version_option(__version__, "--version", message="slothsort %(version)s")
def cli() -> None:
    """
    slothsort — local, privacy-first file organization tool.
    """
    pass


@cli.command("sort")
@click.argument("source_dir", required=False, type=click.Path())
@click.option(
    "--dest",
    "-d",
    type=click.Path(),
    help="Target destination directory (default: in-place)",
)
@click.option(
    "--execute",
    is_flag=True,
    default=False,
    help="Apply file moves (default: dry-run inspection)",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    default=False,
    help="Prompt for confirmation before applying changes",
)
@click.option(
    "--model",
    "-m",
    default="llama3.2",
    help="Local model for contextual categorization (default: llama3.2)",
)
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    default=False,
    help="Traverse subdirectories recursively",
)
@click.option(
    "--no-rename",
    is_flag=True,
    default=False,
    help="Only categorize into folders without renaming files",
)
@click.option(
    "--peek/--no-peek",
    default=True,
    help="Inspect text file headers for contextual classification",
)
@click.option(
    "--dedupe",
    is_flag=True,
    default=False,
    help="Identify duplicate files and isolate into Duplicates/",
)
@click.option(
    "--watch",
    "-w",
    is_flag=True,
    default=False,
    help="Run continuously in background to organize incoming files",
)
@click.option(
    "--interval",
    "-t",
    default=60,
    type=int,
    help="Interval in seconds between watch cycles (default: 60)",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to custom .slothsort.toml config file",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Print detailed diagnostic output",
)
def sort_cmd(
    source_dir: str | None,
    dest: str | None,
    execute: bool,
    interactive: bool,
    model: str,
    recursive: bool,
    no_rename: bool,
    peek: bool,
    dedupe: bool,
    watch: bool,
    interval: int,
    config: str | None,
    verbose: bool,
) -> None:
    """
    Scan and organize files in SOURCE_DIR.
    """
    if not source_dir:
        render_banner()
        console.print("[yellow]Error:[/yellow] Missing target directory argument.")
        console.print("Usage: slothsort <SOURCE_DIR> [--execute]\n")
        sys.exit(1)

    # Load optional user TOML configuration
    user_conf = load_user_config(Path(config) if config else None)

    source_path = Path(source_dir).expanduser().resolve()
    dest_path = Path(dest).expanduser().resolve() if dest else source_path

    # Merge user config overrides if present
    active_model = user_conf.get("model", model)
    active_batch = user_conf.get("batch_size", 15)
    active_ignores = user_conf.get("ignore", ["*.tmp", "*.crdownload", "*.part", "node_modules/*"])

    cfg = SortConfig(
        source_dir=source_path,
        dest_dir=dest_path,
        model=active_model,
        dry_run=not execute and not watch,
        recursive=recursive,
        no_rename=no_rename,
        interactive=interactive,
        peek_content=peek,
        dedupe=dedupe,
        watch=watch,
        watch_interval=interval,
        verbose=verbose,
        batch_size=active_batch,
        ignore_patterns=active_ignores,
    )

    render_header(source_path, dest_path, execute, active_model)

    if watch:
        import time
        from datetime import datetime

        console.print(f"[bold cyan]Sloth Watch Mode active[/bold cyan] 🦥")
        console.print(f"Watching:    [bold]{source_path}[/bold]")
        console.print(f"Interval:    [dim]Checking every {interval}s (Ctrl+C to exit)[/dim]\n")

        try:
            while True:
                files = scan_directory(
                    source_path,
                    recursive=recursive,
                    peek_content=peek,
                    dedupe=dedupe,
                    ignore_patterns=cfg.ignore_patterns,
                    verbose=verbose,
                )
                if files:
                    now_str = datetime.now().strftime("%H:%M:%S")
                    console.print(f"[{now_str}] Found [bold green]{len(files)}[/bold green] new file(s) to organize...")
                    results = categorize_files(files=files, config=cfg)
                    plan = plan_organization(results, dest_path)
                    moved_count, _ = execute_organization(plan, dest_path)
                    console.print(f"[{now_str}] [green]✓ Organized {moved_count} file(s).[/green]\n")
                time.sleep(interval)
        except KeyboardInterrupt:
            console.print("\n[yellow]Watch mode stopped.[/yellow]\n")
            return

    # Step 1: Scan
    with console.status("[dim]Scanning files...[/dim]", spinner="dots"):
        try:
            files = scan_directory(
                source_path,
                recursive=recursive,
                peek_content=peek,
                dedupe=dedupe,
                ignore_patterns=cfg.ignore_patterns,
                verbose=verbose,
            )
        except Exception as e:
            console.print(f"[red]Scan failed:[/red] {e}")
            sys.exit(1)

    if not files:
        console.print(
            Panel(
                "[dim]No unorganized files found. Directory is already clean.[/dim] ✨",
                box=box.ROUNDED,
                border_style="dim",
                expand=False,
            )
        )
        console.print()
        return

    # Step 2: Categorize
    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("[dim]{task.completed}/{task.total} files[/dim]"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[dim]Analyzing taxonomy...[/dim]", total=len(files))

        def update_progress(current: int, total: int) -> None:
            progress.update(task, completed=current)

        def log_msg(msg: str) -> None:
            console.log(msg)

        results = categorize_files(
            files=files,
            config=cfg,
            progress_callback=update_progress,
            log_func=log_msg,
        )

    console.print()

    # Step 3: Plan
    plan = plan_organization(results, dest_path)

    # Render Visuals
    render_summary_table(plan, source_path, dest_path)
    render_tree_preview(plan, dest_path)

    # Step 4: Execution / Guidance
    if not execute:
        import shutil

        is_global = shutil.which("slothsort") is not None
        prefix = "slothsort" if is_global else "uv run slothsort"

        cmd_hint = f"{prefix} \"{source_path}\" --execute"
        if dest:
            cmd_hint += f" --dest \"{dest_path}\""
        if active_model != "llama3.2":
            cmd_hint += f" --model {active_model}"
        if dedupe:
            cmd_hint += " --dedupe"

        guidance_text = (
            f"[bold yellow]Dry-run preview complete. No files were modified on disk.[/bold yellow]\n\n"
            f"To apply these changes, run:\n"
            f"  [bold green]{cmd_hint}[/bold green]"
        )
        if not is_global:
            guidance_text += "\n\n[dim]Tip: Run 'uv tool install .' to use 'slothsort' directly without 'uv run'.[/dim]"

        console.print(
            Panel(
                guidance_text,
                title="[bold]Next Step[/bold]",
                title_align="left",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )
        console.print()
    else:
        if interactive:
            confirm = click.confirm(f"Move and rename {len(plan)} files?", default=True)
            if not confirm:
                console.print("[yellow]Operation aborted by user.[/yellow]\n")
                return

        with console.status("[dim]Applying filesystem moves...[/dim]", spinner="dots"):
            moved_count, undo_file = execute_organization(plan, dest_path)

        import shutil
        is_global = shutil.which("slothsort") is not None
        prefix = "slothsort" if is_global else "uv run slothsort"

        console.print(
            Panel(
                f"[bold green]✓ Successfully organized {moved_count} file(s) into category subfolders.[/bold green]\n\n"
                f"Rollback manifest: [dim]{undo_file}[/dim]\n"
                f"To revert this operation anytime, run:\n"
                f"  [bold cyan]{prefix} undo \"{dest_path}\"[/bold cyan]",
                title="[bold green]Complete[/bold green]",
                title_align="left",
                border_style="green",
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )
        console.print()


@cli.command("undo")
@click.argument("target_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
def undo(target_dir: str) -> None:
    """
    Restore files to original locations using the undo log.
    """
    path = Path(target_dir).expanduser().resolve()
    console.print()

    try:
        count, warnings = execute_undo(path)
        body = f"[bold green]✓ Successfully restored {count} file(s) to original locations.[/bold green]"
        if warnings:
            body += "\n\n[yellow]Warnings:[/yellow]"
            for w in warnings:
                body += f"\n  • {w}"

        console.print(
            Panel(
                body,
                title="[bold green]Rollback Complete[/bold green]",
                title_align="left",
                border_style="green",
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )
        console.print()
    except FileNotFoundError:
        console.print(
            Panel(
                f"[yellow]No {UNDO_LOG_FILENAME} manifest found in:[/yellow]\n{path}",
                title="[bold red]Undo Failed[/bold red]",
                title_align="left",
                border_style="red",
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )
        console.print()
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Undo failed:[/red] {e}\n")
        sys.exit(1)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
