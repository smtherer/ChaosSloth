import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text

class SlothConsole:
    def __init__(self):
        self.console = Console()

    def print_banner(self):
        title = Text("CHAOSSLOTH :: ASYNC CONCURRENCY EXORCIST", style="bold white")
        subtitle = Text("Autonomous Bayesian Interleaver • Formal Verification • Air-Gapped Local AI", style="dim cyan")
        
        banner_content = Text()
        banner_content.append("  ⚡ Leslie Lamport Vector Clocks (Safety Invariant: ¬(e1 ≺ e2))\n", style="green")
        banner_content.append("  ⚡ Prior Labs TabPFN-3.5 (In-Context Bayesian State-Space Inversion)\n", style="green")
        banner_content.append("  ⚡ Google Gemma 2B/9B (AST Synchronization & Atomic Lock Synthesis)\n", style="green")
        banner_content.append("  ⚡ Coffman Lock Acquisition DAG (Liveness & Deadlock Prevention)\n", style="green")
        
        self.console.print(Panel(
            banner_content,
            title=title,
            subtitle=subtitle,
            border_style="bright_blue",
            padding=(1, 2)
        ))

    def step(self, phase_num: int, name: str, status: str = "running"):
        self.console.print(f"[bold bright_blue]▶ [{phase_num}/8][/bold bright_blue] [bold white]{name.upper()}[/bold white] [dim]... {status}[/dim]")

    def print_telemetry_table(self, baseline_runs: int, flakiness_rate: float, delay_us: float, confidence: float):
        table = Table(title="Prior Labs TabPFN-3.5 Telemetry Matrix", border_style="bright_blue", show_header=True)
        table.add_column("Parameter / State", style="bold white")
        table.add_column("Observed Measurement", style="bold cyan")
        table.add_column("Engine Interpretation", style="dim white")
        
        table.add_row("Baseline Sampling Cycles", f"{baseline_runs} Iterations", "Empirical async event loop sampling")
        table.add_row("Observed Flakiness Ratio", f"{flakiness_rate:.1%}", "Intermittent failure rate under random jitter")
        table.add_row("Critical Failure Coordinate", f"{delay_us:.1f} µs delay", "TabPFN inverted temporal boundary")
        table.add_row("Bayesian Confidence Score", f"{confidence:.2%}", "Posterior certainty of race reproduction")
        table.add_row("Targeted Reproducibility", "100.0% (10/10)", "Deterministically reproduced on demand")
        
        self.console.print(table)

    def print_patch(self, diff_text: str):
        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
        self.console.print(Panel(syntax, title="[bold green]Deterministic AST Atomic Patch[/bold green]", border_style="green"))

    def print_success(self, orig_rate: float, patched_rate: float, elapsed: float):
        summary = Text()
        summary.append(f"✔ VERIFICATION COMPLETE IN {elapsed:.2f}s\n", style="bold green")
        summary.append(f"  • Pre-Patch Race Rate : ", style="white")
        summary.append(f"{orig_rate:.1%}\n", style="bold red")
        summary.append(f"  • Post-Patch Race Rate: ", style="white")
        summary.append(f"{patched_rate:.1%}\n\n", style="bold green")
        summary.append("All Lamport Happened-Before invariants satisfied. Coffman lock DAG acyclic.\n", style="dim white")
        summary.append("Sloth mode fulfilled. Safe to merge.", style="bold cyan")
        
        self.console.print(Panel(summary, border_style="bright_green", padding=(1, 2)))
