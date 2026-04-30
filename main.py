import typer
from rich.console import Console
from james.core.agent import PentestAgent

app = typer.Typer(help="James Linux - Parrot OS Pentesting Agent")
console = Console()

@app.command()
def start(
    target: str = typer.Argument(..., help="The target scope (e.g., specific SSID or BSSID)"),
    interface: str = typer.Option("wlan0", "--interface", "-i", help="Wireless interface to use")
):
    """
    Start the autonomous AI agent against a specified target scope.
    """
    console.print(f"[bold green]Starting James AI Agent on Parrot OS[/bold green]")
    console.print(f"Target Scope: [bold yellow]{target}[/bold yellow]")
    console.print(f"Interface: [bold blue]{interface}[/bold blue]")

    agent = PentestAgent(target_scope=target)
    agent.run_cycle(interface)

@app.command()
def info():
    """
    Display information about the tool.
    """
    console.print("[bold cyan]James Linux[/bold cyan] - A native pentesting agent for Parrot OS.")
    console.print("Powered by local execution without shell=True for enhanced security.")

if __name__ == "__main__":
    app()
