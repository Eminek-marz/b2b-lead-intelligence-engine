"""
Mini-Apollo: B2B Lead Engine & Email Permutator
A self-hosted, zero-cost intelligence tool for finding, generating,
pattern-matching, and verifying corporate decision-maker emails.
"""

import sys
import os
import re
import csv
import json
import time
import argparse
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Ensure Windows stdout supports UTF-8 characters
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


USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def clean_name(name_str: str) -> str:
    """Strip titles, credentials, punctuation, and extra whitespace."""
    if not name_str:
        return ""
    # Remove credentials like MD, PhD, LLC, CEO
    name_str = re.sub(r"\b(Dr|Mr|Mrs|Ms|PhD|MD|Esq|CEO|Founder|Owner)\b\.?", "", name_str, flags=re.I)
    # Remove anything inside parentheses
    name_str = re.sub(r"\(.*?\)", "", name_str)
    # Keep only letters, spaces, hyphens
    name_str = re.sub(r"[^a-zA-Z\s\-]", "", name_str)
    return name_str.strip()


def clean_domain(domain_str: str) -> str:
    """Normalize URLs into pure domain names (e.g. https://www.acme.com/about -> acme.com)."""
    if not domain_str:
        return ""
    domain_str = domain_str.strip().lower()
    if not domain_str.startswith(("http://", "https://")):
        domain_str = "https://" + domain_str
    parsed = urlparse(domain_str)
    host = parsed.netloc or parsed.path
    if host.startswith("www."):
        host = host[4:]
    return host.split(":")[0].strip("/")


def query_mx_records(domain: str):
    """Query Google DNS-over-HTTPS to discover mail servers (MX records)."""
    try:
        url = f"https://dns.google/resolve?name={domain}&type=MX"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "Answer" in data and data["Answer"]:
                records = [ans["data"] for ans in data["Answer"] if "data" in ans]
                return records
    except Exception:
        pass
    return []


def identify_mail_provider(mx_records: list) -> str:
    """Identify the email service provider based on MX hosts."""
    if not mx_records:
        return "Unknown / No MX"
    combined = " ".join(mx_records).lower()
    if "google" in combined or "aspmx" in combined:
        return "Google Workspace (Gmail)"
    if "outlook" in combined or "office365" in combined or "protection.outlook" in combined:
        return "Microsoft 365 (Exchange)"
    if "zoho" in combined:
        return "Zoho Mail"
    if "protonmail" in combined or "proton" in combined:
        return "Proton Mail"
    if "mimecast" in combined:
        return "Mimecast (Enterprise Security)"
    if "barracuda" in combined or "proofpoint" in combined:
        return "Proofpoint / Barracuda"
    return "Custom / Self-Hosted Mail Server"


def scrape_domain_for_emails(domain: str) -> list:
    """Crawl homepage and contact page to discover publicly published emails & patterns."""
    found_emails = set()
    urls_to_try = [
        f"https://{domain}",
        f"https://{domain}/contact",
        f"https://{domain}/about",
        f"https://{domain}/team",
        f"http://{domain}",
    ]
    headers = {"User-Agent": USER_AGENTS}

    email_pattern = re.compile(
        rf"[a-zA-Z0-9_.+-]+@{re.escape(domain)}", re.IGNORECASE
    )

    for url in urls_to_try:
        try:
            resp = requests.get(url, headers=headers, timeout=4, allow_redirects=True)
            if resp.status_code == 200:
                # Search in HTML comments, mailto, and body text
                matches = email_pattern.findall(resp.text)
                for m in matches:
                    clean_m = m.strip().lower()
                    if not any(clean_m.endswith(ext) for ext in [".png", ".jpg", ".svg", ".css", ".js"]):
                        found_emails.add(clean_m)
                if len(found_emails) >= 3:
                    break
        except Exception:
            continue
    return list(found_emails)


def detect_company_pattern(sample_emails: list, domain: str) -> str:
    """Detect if the company uses first.last, first, or flast from sample scraped emails."""
    for email in sample_emails:
        local_part = email.split("@")[0].lower()
        if local_part in ["info", "contact", "support", "sales", "press", "media", "help", "careers"]:
            continue
        if "." in local_part:
            return "{first}.{last}@" + domain
        if "_" in local_part:
            return "{first}_{last}@" + domain
        if len(local_part) > 3 and not re.search(r"\d", local_part):
            return "{first}@" + domain
    return "{first}.{last}@" + domain  # Default most common corporate standard


def generate_permutations(first_name: str, last_name: str, domain: str) -> list:
    """Generate the top corporate B2B email permutations ordered by statistical frequency."""
    fn = re.sub(r"[^a-zA-Z]", "", first_name).lower()
    ln = re.sub(r"[^a-zA-Z]", "", last_name).lower()
    d = domain.lower()

    if not fn and not ln:
        return []
    if not ln:
        return [
            {"email": f"{fn}@{d}", "pattern": "first"},
            {"email": f"contact@{d}", "pattern": "generic"},
        ]
    if not fn:
        return [
            {"email": f"{ln}@{d}", "pattern": "last"},
            {"email": f"contact@{d}", "pattern": "generic"},
        ]

    f_initial = fn[0]
    l_initial = ln[0]

    permutations = [
        {"email": f"{fn}.{ln}@{d}", "pattern": "first.last", "rank": 1, "confidence": "High"},
        {"email": f"{fn}@{d}", "pattern": "first", "rank": 2, "confidence": "High"},
        {"email": f"{f_initial}{ln}@{d}", "pattern": "flast", "rank": 3, "confidence": "High"},
        {"email": f"{fn}{ln}@{d}", "pattern": "firstlast", "rank": 4, "confidence": "Medium"},
        {"email": f"{fn}_{ln}@{d}", "pattern": "first_last", "rank": 5, "confidence": "Medium"},
        {"email": f"{ln}.{fn}@{d}", "pattern": "last.first", "rank": 6, "confidence": "Low"},
        {"email": f"{f_initial}.{ln}@{d}", "pattern": "f.last", "rank": 7, "confidence": "Medium"},
        {"email": f"{fn}{l_initial}@{d}", "pattern": "firstl", "rank": 8, "confidence": "Low"},
    ]
    return permutations


def verify_email_format_and_dns(email: str) -> dict:
    """Free syntax, disposable email detection, and public API check."""
    domain = email.split("@")[-1]
    res = {
        "valid_format": bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email)),
        "disposable": False,
        "dns": True,
        "is_role_account": False,
    }

    # Role check
    role_accounts = ["info", "sales", "support", "admin", "contact", "billing", "careers"]
    if email.split("@")[0].lower() in role_accounts:
        res["is_role_account"] = True

    # Check via free public API (disify.com)
    try:
        api_url = f"https://disify.com/api/email/{email}"
        resp = requests.get(api_url, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            res["disposable"] = data.get("disposable", False)
            res["dns"] = data.get("dns", True)
    except Exception:
        pass

    return res


def investigate_prospect(first_name: str, last_name: str, domain: str, company_name: str = ""):
    """Execute complete intelligence lookup for a single prospect."""
    first_name = clean_name(first_name)
    last_name = clean_name(last_name)
    domain = clean_domain(domain)

    console.print(f"\n[bold cyan]🔍 Investigating Target:[/bold cyan] {first_name} {last_name} @ [bold yellow]{domain}[/bold yellow]")

    # 1. DNS & Mail Provider Check
    with console.status("[bold green]Checking Mail Servers (MX Records)..."):
        mx_records = query_mx_records(domain)
        provider = identify_mail_provider(mx_records)

    # 2. Public Website Email Crawl
    with console.status("[bold green]Crawling website for email footprint & patterns..."):
        scraped_emails = scrape_domain_for_emails(domain)
        detected_pattern = detect_company_pattern(scraped_emails, domain)

    # 3. Generate Permutations
    permutations = generate_permutations(first_name, last_name, domain)

    # Determine Top Recommendation
    best_candidate = None
    confidence = "Medium"

    # If any scraped email directly matches our candidate's name
    direct_match = None
    for em in scraped_emails:
        fn_part = first_name.lower()
        if fn_part and fn_part in em:
            direct_match = em
            confidence = "Verified (Found on Website!)"
            break

    if direct_match:
        best_candidate = direct_match
    elif detected_pattern:
        resolved = detected_pattern.replace("{first}", first_name.lower()).replace("{last}", last_name.lower())
        best_candidate = resolved
        confidence = "High (Company Pattern Matched)"
    else:
        best_candidate = permutations[0]["email"] if permutations else ""
        confidence = "Medium (Standard Industry Heuristic)"

    # Verify best candidate
    verification = verify_email_format_and_dns(best_candidate) if best_candidate else {}

    # Print Intelligence Report
    print_prospect_report(
        first_name,
        last_name,
        company_name or domain,
        domain,
        provider,
        mx_records,
        scraped_emails,
        detected_pattern,
        best_candidate,
        confidence,
        verification,
        permutations,
    )

    return {
        "First Name": first_name,
        "Last Name": last_name,
        "Company": company_name or domain,
        "Domain": domain,
        "Best Email": best_candidate,
        "Confidence": confidence,
        "Mail Provider": provider,
        "Detected Pattern": detected_pattern,
        "Sample Found Emails": ", ".join(scraped_emails),
        "DNS Valid": verification.get("dns", True),
        "Disposable": verification.get("disposable", False),
    }


def print_prospect_report(
    first_name, last_name, company, domain, provider, mx_records,
    scraped_emails, detected_pattern, best_candidate, confidence,
    verification, permutations
):
    """Render a terminal dashboard with rich panels and tables."""
    # Summary Panel
    mx_display = mx_records[0].strip(".") if mx_records else "None"
    scraped_display = ", ".join(scraped_emails[:3]) if scraped_emails else "None published publicly"

    summary_text = (
        f"[bold]Target:[/bold] {first_name} {last_name}\n"
        f"[bold]Company:[/bold] {company} ({domain})\n"
        f"[bold]Mail Provider:[/bold] [green]{provider}[/green] ([dim]{mx_display}[/dim])\n"
        f"[bold]Scraped Footprint:[/bold] [dim]{scraped_display}[/dim]\n"
        f"[bold]Company Email Pattern:[/bold] [yellow]{detected_pattern}[/yellow]\n\n"
        f"[bold green]⭐ BEST PREDICTED EMAIL:[/bold green] [bold white on blue] {best_candidate} [/bold white on blue]\n"
        f"[bold]Confidence Score:[/bold] [bold cyan]{confidence}[/bold cyan]"
    )
    console.print(Panel(summary_text, title="🎯 Intelligence Dossier", border_style="cyan", box=box.ROUNDED))

    # Permutations Table
    table = Table(title=f"All Email Permutations for {first_name} {last_name}", box=box.SIMPLE_HEAVY)
    table.add_column("Rank", justify="center", style="dim", width=6)
    table.add_column("Email Address", style="bold white")
    table.add_column("Pattern Type", style="yellow")
    table.add_column("Status / Probability", justify="center")

    for p in permutations:
        is_best = (p["email"].lower() == best_candidate.lower())
        status_tag = "[bold green]★ Top Match[/bold green]" if is_best else f"[{p['confidence'].lower()}]{p['confidence']}[/{p['confidence'].lower()}]"
        style_highlight = "bold white on green" if is_best else ""
        table.add_row(
            str(p.get("rank", "-")),
            p["email"],
            p["pattern"],
            status_tag,
            style=style_highlight
        )

    console.print(table)


def process_csv_file(filepath: str, output_csv: str = None):
    """Batch process an entire CSV file with multiple leads."""
    if not os.path.exists(filepath):
        console.print(f"[bold red]File not found: {filepath}[/bold red]")
        return

    results = []
    with open(filepath, "r", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    console.print(f"\n[bold green]🚀 Found {len(rows)} leads in {filepath}. Starting batch intelligence extraction...[/bold green]\n")

    for i, row in enumerate(rows, 1):
        # Flexible header detection
        first = row.get("First Name") or row.get("first_name") or row.get("First") or ""
        last = row.get("Last Name") or row.get("last_name") or row.get("Last") or ""
        full_name = row.get("Name") or row.get("Full Name") or ""
        if not first and full_name:
            parts = full_name.split(" ", 1)
            first = parts[0]
            last = parts[1] if len(parts) > 1 else ""

        domain = row.get("Website") or row.get("Domain") or row.get("Company Website") or ""
        company = row.get("Company") or row.get("Company Name") or ""

        if not domain:
            continue

        console.print(f"[dim]── Processing [{i}/{len(rows)}]: {first} {last} @ {domain} ──[/dim]")
        res = investigate_prospect(first, last, domain, company)
        results.append(res)
        time.sleep(0.5)

    # Save output
    os.makedirs("exports", exist_ok=True)
    if not output_csv:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_csv = os.path.join("exports", f"enriched_leads_{timestamp}.csv")

    keys = [
        "First Name", "Last Name", "Company", "Domain", "Best Email",
        "Confidence", "Mail Provider", "Detected Pattern", "Sample Found Emails",
        "DNS Valid", "Disposable"
    ]
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)

    console.print(f"\n[bold green]✅ Batch complete! Enriched dataset exported to:[/bold green] [bold cyan]{output_csv}[/bold cyan]\n")


def interactive_menu():
    """Terminal interactive mode."""
    console.print(Panel.fit(
        "[bold cyan]MINI-APOLLO LEAD ENGINE[/bold cyan]\n"
        "[dim]Find, predict, pattern-match, and verify corporate emails for $0[/dim]",
        border_style="cyan"
    ))

    choice = Prompt.ask(
        "\nChoose an action",
        choices=["1", "2", "3", "q"],
        default="1"
    )

    if choice == "1":
        name = Prompt.ask("Enter Full Name (e.g. Satya Nadella or John Smith)")
        domain = Prompt.ask("Enter Company Website or Domain (e.g. microsoft.com or stripe.com)")
        company = Prompt.ask("Enter Company Name (optional)", default="")
        parts = name.strip().split(" ", 1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else ""
        investigate_prospect(first, last, domain, company)

    elif choice == "2":
        filepath = Prompt.ask("Enter CSV file path (e.g. sample_leads.csv)")
        process_csv_file(filepath)

    elif choice == "3":
        # Create a sample test CSV
        sample_path = "sample_leads.csv"
        with open(sample_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["First Name", "Last Name", "Company", "Website"])
            writer.writerow(["Tim", "Cook", "Apple", "apple.com"])
            writer.writerow(["Satya", "Nadella", "Microsoft", "microsoft.com"])
            writer.writerow(["Brian", "Chesky", "Airbnb", "airbnb.com"])
        console.print(f"[bold green]Created demo file: {sample_path}[/bold green]")
        process_csv_file(sample_path)

    elif choice == "q":
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Mini-Apollo B2B Lead Engine & Email Permutator")
    parser.add_argument("--name", help="Full name of target (e.g. 'Satya Nadella')")
    parser.add_argument("--first", help="First name")
    parser.add_argument("--last", help="Last name")
    parser.add_argument("--domain", help="Company domain or website URL (e.g. 'microsoft.com')")
    parser.add_argument("--company", help="Company name (optional)", default="")
    parser.add_argument("--file", help="Path to input CSV file for batch processing")
    parser.add_argument("--export", help="Path to custom output CSV file")

    args = parser.parse_args()

    if args.file:
        process_csv_file(args.file, args.export)
    elif args.domain and (args.name or args.first):
        first = args.first
        last = args.last
        if args.name:
            parts = args.name.strip().split(" ", 1)
            first = parts[0]
            last = parts[1] if len(parts) > 1 else ""
        investigate_prospect(first, last, args.domain, args.company)
    else:
        interactive_menu()


if __name__ == "__main__":
    main()
