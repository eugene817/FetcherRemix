from rich.console import Console

console = Console()


def _s(s: str):
    console.print(f"[bold blue][*][/bold blue] {s}")


def _e(s: str):
    console.print(f"[bold red][!][/bold red] {s}")


def _v(s: str):
    console.print(f"[dim][-][/dim] {s}")


def _p(s: str):
    console.print(f"[bold green][+][/bold green] {s}")
