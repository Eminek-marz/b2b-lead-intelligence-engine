"""
Campaign & Sequence Generator
Transforms raw enriched leads into ready-to-send, high-converting
3-step cold outreach campaigns formatted for Apollo, Instantly, or GoHighLevel.
"""

import os
import sys
import glob
import csv
import time
import argparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

console = Console(force_terminal=True)

# Proven, high-converting agency outreach templates
TEMPLATES = {
    "lead_gen": {
        "name": "B2B Lead Generation & Pipeline Support",
        "subject": "quick question re: {{Company}} pipeline",
        "step_1": (
            "Hi {{First Name}},\n\n"
            "Saw that you're leading {{Company}}—congratulations on the recent momentum.\n\n"
            "I noticed many teams in your space spend 10+ hours a week manually cleaning "
            "prospect databases or dealing with high bounce rates that burn their email domains.\n\n"
            "We recently helped an outbound team cut their bounce rate to under 1.5% while doubling "
            "their qualified meetings using custom lead enrichment.\n\n"
            "Would you be open to seeing a free sample list of 50 verified decision-makers for {{Company}} this week?\n\n"
            "Best,\n[Your Name]"
        ),
        "step_2_followup": (
            "Hi {{First Name}},\n\n"
            "Quick follow-up on my note below—I put together a quick 3-point audit on how "
            "{{Company}} can streamline its outbound pipeline.\n\n"
            "Would you like me to send that over?\n\n"
            "Best,\n[Your Name]"
        ),
        "step_3_breakup": (
            "Hi {{First Name}},\n\n"
            "I know you're busy running {{Company}}, so I won't follow up again.\n\n"
            "If you ever need verified, zero-bounce B2B leads or pipeline automation in the future, "
            "feel free to reach back out.\n\n"
            "Wishing you and {{Company}} all the best!\n\n"
            "Best,\n[Your Name]"
        ),
    },
    "automation": {
        "name": "Zapier / Make.com & CRM Workflow Optimization",
        "subject": "{{Company}} - backend workflows & automations",
        "step_1": (
            "Hi {{First Name}},\n\n"
            "Quick question—as {{Company}} grows, are your team members still spending time "
            "manually copy-pasting data between your forms, CRM, and communication tools?\n\n"
            "We build custom Make.com and GoHighLevel automations with built-in error handling "
            "so no lead or notification ever slips through the cracks.\n\n"
            "Are you open to a 5-minute video showing 2 workflows you could automate right now?\n\n"
            "Best,\n[Your Name]"
        ),
        "step_2_followup": (
            "Hi {{First Name}},\n\n"
            "Following up on this. We recently automated lead routing for a team in your space, "
            "saving them roughly 15 hours a week in manual admin.\n\n"
            "Happy to share the workflow blueprint if you're interested?\n\n"
            "Best,\n[Your Name]"
        ),
        "step_3_breakup": (
            "Hi {{First Name}},\n\n"
            "Assuming automating backend workflows isn't a priority for {{Company}} right now.\n\n"
            "I'll close your file for now. Feel free to reach out down the road if things change.\n\n"
            "Best,\n[Your Name]"
        ),
    }
}


def find_latest_enriched_csv() -> str:
    """Find the most recent enriched lead CSV in the exports directory."""
    files = glob.glob(os.path.join("exports", "enriched_leads_*.csv"))
    if not files:
        return ""
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def build_campaign(input_csv: str, campaign_type: str = "lead_gen", output_csv: str = None):
    """Generate a complete 3-step personalized outreach campaign."""
    if not os.path.exists(input_csv):
        console.print(f"[bold red]Input file not found: {input_csv}[/bold red]")
        return

    template = TEMPLATES.get(campaign_type, TEMPLATES["lead_gen"])
    campaign_name = template["name"]

    console.print(f"\n[bold cyan]🚀 Generating Outreach Campaign:[/bold cyan] [bold yellow]{campaign_name}[/bold yellow]")
    console.print(f"[dim]Reading from: {input_csv}[/dim]\n")

    leads = []
    with open(input_csv, "r", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        leads = list(reader)

    if not leads:
        console.print("[bold red]No leads found in CSV![/bold red]")
        return

    campaign_rows = []
    for lead in leads:
        first = lead.get("First Name", "").strip() or "there"
        last = lead.get("Last Name", "").strip()
        company = lead.get("Company", "").strip() or "your company"
        email = lead.get("Best Email", "").strip() or lead.get("Email", "").strip()

        if not email:
            continue

        # Personalize subject and steps
        subject = template["subject"].replace("{{Company}}", company).replace("{{First Name}}", first)
        step_1 = template["step_1"].replace("{{Company}}", company).replace("{{First Name}}", first)
        step_2 = template["step_2_followup"].replace("{{Company}}", company).replace("{{First Name}}", first)
        step_3 = template["step_3_breakup"].replace("{{Company}}", company).replace("{{First Name}}", first)

        campaign_rows.append({
            "First Name": first,
            "Last Name": last,
            "Company": company,
            "Email": email,
            "Subject Line": subject,
            "Email Step 1 (Day 1)": step_1,
            "Email Step 2 (Day 3)": step_2,
            "Email Step 3 (Day 7)": step_3,
            "Status": "Ready to Launch",
        })

    # Save to exports
    os.makedirs("exports", exist_ok=True)
    if not output_csv:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_csv = os.path.join("exports", f"apollo_ready_campaign_{timestamp}.csv")

    headers = [
        "First Name", "Last Name", "Company", "Email", "Subject Line",
        "Email Step 1 (Day 1)", "Email Step 2 (Day 3)", "Email Step 3 (Day 7)", "Status"
    ]

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(campaign_rows)

    # Render Preview Panel
    console.print(Panel(
        f"[bold green]✅ Campaign Successfully Built![/bold green]\n\n"
        f"[bold]Total Prospects Targeted:[/bold] {len(campaign_rows)}\n"
        f"[bold]Sequence Structure:[/bold] 3 Automated Steps (Day 1, Day 3, Day 7)\n"
        f"[bold]Export File (Apollo/Instantly Ready):[/bold] [cyan]{output_csv}[/cyan]",
        title="📬 Campaign Generation Dossier",
        border_style="green",
        box=box.ROUNDED
    ))

    # Show a live preview of the first lead's email
    if campaign_rows:
        sample = campaign_rows[0]
        preview_text = (
            f"[bold yellow]To:[/bold yellow] {sample['Email']} ({sample['First Name']} @ {sample['Company']})\n"
            f"[bold yellow]Subject:[/bold yellow] {sample['Subject Line']}\n\n"
            f"[dim]── Step 1 (Initial Pitch) ──[/dim]\n{sample['Email Step 1 (Day 1)']}\n\n"
            f"[dim]── Step 2 (Follow-up after 3 days) ──[/dim]\n{sample['Email Step 2 (Day 3)']}\n\n"
            f"[dim]── Step 3 (Break-up after 7 days) ──[/dim]\n{sample['Email Step 3 (Day 7)']}"
        )
        console.print(Panel(preview_text, title=f"🔍 Live Sequence Preview for {sample['First Name']} {sample['Last Name']}", border_style="cyan"))


def main():
    parser = argparse.ArgumentParser(description="Automated Cold Outreach Campaign Builder")
    parser.add_argument("--input", help="Path to input enriched CSV")
    parser.add_argument("--type", choices=["lead_gen", "automation"], default="lead_gen", help="Campaign angle")
    parser.add_argument("--output", help="Path to output CSV")

    args = parser.parse_args()

    input_file = args.input
    if not input_file:
        input_file = find_latest_enriched_csv()
        if not input_file:
            input_file = "sample_leads.csv"

    build_campaign(input_file, args.type, args.output)


if __name__ == "__main__":
    main()
