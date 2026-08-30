import os
import sys
import argparse

# Ensure standard streams use UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from core.pipeline import run_patch_pipeline
from core.models import PipelineResult

console = Console(highlight=False)

def print_banner():
    banner_text = (
        "[bold cyan]+----------------------------------------------------------+[/bold cyan]\n"
        "[bold cyan]|[/bold cyan]       [bold yellow]GlobalConvertApps - Automated APK Patcher[/bold yellow]          [bold cyan]|[/bold cyan]\n"
        "[bold cyan]|[/bold cyan]  [white]Strict In-Method IS_INTERNATIONAL_BUILD -> 0x1 Patcher[/white]  [bold cyan]|[/bold cyan]\n"
        "[bold cyan]+----------------------------------------------------------+[/bold cyan]"
    )
    console.print(banner_text)

def display_results(res: PipelineResult):
    if not res.success:
        console.print(Panel(f"[bold red][FAIL] Patching Failed:[/bold red]\n{res.error_message}", title="[red]Error[/red]", border_style="red"))
        return

    console.print()
    console.print(Panel(
        f"[bold green][OK] Patching and repackaging completed successfully![/bold green]\n\n"
        f"[bold white]Output APK:[/bold white] [cyan]{res.output_apk_path}[/cyan]\n"
        f"[bold white]File Size:[/bold white] [yellow]{res.file_size_bytes / (1024 * 1024):.2f} MB[/yellow]\n"
        f"[bold white]Classes DEX Count:[/bold white] {res.total_dex_count}\n"
        f"[bold white]Total Executable Patches:[/bold white] [bold green]{res.total_patches}[/bold green]\n"
        f"[bold white]Non-Executable References Skipped:[/bold white] [blue]{len(res.skipped)}[/blue]",
        title="[bold green]Success[/bold green]",
        border_style="green"
    ))

    if res.patches:
        table = Table(title="[bold]Patched IS_INTERNATIONAL_BUILD Usages[/bold]", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Class", style="cyan")
        table.add_column("Method", style="green")
        table.add_column("Line", style="yellow", justify="right")
        table.add_column("Register", style="bold red")
        table.add_column("Injected Code", style="bold white")

        for idx, p in enumerate(res.patches, start=1):
            table.add_row(
                str(idx),
                p.class_name,
                p.method_name,
                str(p.line_number),
                p.register,
                f"const/4 {p.register}, 0x1"
            )
        console.print(table)

    if res.skipped:
        skipped_table = Table(title="[dim]Audited & Preserved Non-Executable Usages (Untouched)[/dim]", show_header=True, header_style="dim cyan")
        skipped_table.add_column("#", style="dim", width=4)
        skipped_table.add_column("File", style="dim")
        skipped_table.add_column("Line", style="dim", justify="right")
        skipped_table.add_column("Reason Untouched", style="yellow")
        skipped_table.add_column("Content", style="dim white")

        for idx, s in enumerate(res.skipped[:15], start=1):
            skipped_table.add_row(
                str(idx),
                os.path.basename(s.file_path),
                str(s.line_number),
                s.reason,
                s.line_content[:60] + ("..." if len(s.line_content) > 60 else "")
            )
        if len(res.skipped) > 15:
            skipped_table.add_row("...", "...", "...", "...", f"+ {len(res.skipped) - 15} more non-executable items preserved untouched")
        console.print(skipped_table)

def main():
    print_banner()
    parser = argparse.ArgumentParser(description="Automated general-purpose APK IS_INTERNATIONAL_BUILD patcher.")
    parser.add_argument("url", nargs="?", help="Direct APK download URL or local path")
    parser.add_argument("-u", "--url-arg", dest="url_flag", help="APK URL")
    parser.add_argument("-o", "--output", default="output", help="Directory to save patched APK (default: output/)")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary decompiled directories for debugging")

    args = parser.parse_args()
    apk_source = args.url or args.url_flag

    if not apk_source:
        try:
            apk_source = console.input("[bold yellow]Enter APK URL (or local file path): [/bold yellow]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[red]Operation cancelled by user.[/red]")
            sys.exit(1)

    if not apk_source:
        console.print("[bold red]Error: No APK URL or file provided.[/bold red]")
        sys.exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Processing APK...", total=100)

        def on_progress(pct: int, msg: str, stage: str, data=None):
            progress.update(task, completed=max(pct, 0), description=f"[cyan][{stage}][/cyan] {msg}")

        result = run_patch_pipeline(
            apk_source=apk_source,
            output_dir=args.output,
            progress_callback=on_progress,
            keep_temp=args.keep_temp
        )

    display_results(result)
    sys.exit(0 if result.success else 1)

if __name__ == "__main__":
    main()
