from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from scan_file import scan_target

console = Console()

def safe_str(value, default="N/A"):
    return str(value) if value is not None else default

def cmd_scan(target_path, conn):
    result = scan_target(target_path, conn)
    if result["status"] == "not_found":
        console.print(f"[bold red]✘ Path '[bold cyan]{result['target']}[/bold cyan]' does not exist.[/bold red]\n")
        return
    if result["status"] == "no_files":
        console.print(f"[bold yellow]⚠ No Python (.py) files found in '[bold cyan]{result['target']}[/bold cyan]'.[/bold yellow]\n")
        return
    newly = result["newly_discovered"]
    already = result["already_discovered"]
    new_count = len(newly)
    already_count = len(already)
    distinct_count = new_count + already_count

    if newly:
        console.print()
        for item in newly:
            mod_name = item["module"]
            func_name = item["name"]
            func_id = item["id"]
            if item["is_important"]:
                console.print(f"   [bold yellow]★ Unlocked Core:[/] [bold cyan]{mod_name}.{func_name}()[/bold cyan] [yellow]#{func_id}[/yellow]")
            else:
                console.print(f"   [bold green]✦ Unlocked:[/] [bold cyan]{mod_name}.{func_name}()[/bold cyan] [yellow]#{func_id}[/yellow]")
        console.print()

    summary_table = Table.grid(padding=(0,2))
    summary_table.add_column(style="bold white")
    summary_table.add_column(style="cyan")
    file_label = f"[bold yellow]{result["file_count"]}[/bold yellow] file{"s" if result["file_count"]>1 else ""}"
    summary_table.add_row("Target path:",f"[bold cyan]{result["target"]} [/bold cyan]({file_label})")
    summary_table.add_row("Total calls detected:", f"[white]{result["total_calls"]}[/white]")

    new_style = f"[bold green]{new_count} 🎉[/bold green]" if new_count > 0 else "[white]0[/white]"
    summary_table.add_row("Newly unlocked:", new_style)
    summary_table.add_row("Already in pydex:", f"[white]{already_count}[/white]")
    summary_table.add_row("Distinct functions:", f"[bold cyan]{distinct_count}[/bold cyan]")
    panel = Panel(
        summary_table,
        title="[bold yellow]✨ Scan Summary[/bold yellow]",
        box=box.ROUNDED,
        expand=False
    )
    console.print(panel)
    if new_count > 0:
        console.print(f"[bold green]🎉 Great job! You unlocked [bold yellow]{new_count}[/bold yellow] new function{'s' if new_count > 1 else ''} in your pydex![/bold green]\n")
    elif distinct_count > 0:
        console.print(f"[yellow]★ All {distinct_count} detected functions were already in your pydex.[/yellow]\n")
    else:
        console.print("[yellow]⚠ No functions detected in the scanned file(s).[/yellow]\n")

def cmd_search(args, conn):
    cur = conn.cursor()
    try:
        if args.by_arg:
            query = """SELECT f.id, f.name, f.description, f.my_notes, f.is_important, s.raw_signature, a.name, a.default_value, a.required, a.order_index, m.name
                    FROM functions f LEFT JOIN modules m ON f.module_id=m.id LEFT JOIN signatures s ON f.id=s.function_id LEFT JOIN arguments a ON s.id=a.signature_id
                    WHERE a.name LIKE ? AND f.discovered=1
                    ORDER BY m.id, f.id, s.raw_signature, a.order_index"""
            params = [args.function_name]
        else:
            name_condition = "f.name LIKE ?" if args.partial else "f.name = ?"
            search_value = f"%{args.function_name}%" if args.partial else args.function_name
            query = f"""SELECT f.id, f.name, f.description, f.my_notes, f.is_important, s.raw_signature, a.name, a.default_value, a.required, a.order_index, m.name
                        FROM functions f LEFT JOIN modules m ON f.module_id=m.id LEFT JOIN signatures s ON f.id=s.function_id LEFT JOIN arguments a ON s.id=a.signature_id 
                        WHERE {name_condition} AND f.discovered=1"""
            if args.required:
                query += " AND a.required=1"
            query += " ORDER BY m.id, f.id, s.raw_signature, a.order_index"
            params = [search_value]
        cur.execute(query, params)
        rows = cur.fetchall()
        if rows:
            current_function_id = 0
            current_sig = ""
            current_table = None

            for row in rows:
                func_id, func_name, desc, my_notes, is_important, sig, arg_name, default_val, required, order_idx, module = row
                
                if func_id != current_function_id:
                    if current_table:
                        console.print(current_table)
                        current_table = None

                    current_function_id = func_id
                    current_sig = ""
                    func_header = f"[bold yellow]★ {func_name}[/bold yellow]" if is_important else f"[bold green]✦ {func_name}[/bold green]"
                    content = f"[white]{desc}[/white]"
                    if my_notes:
                        content += f"\n\n[bold yellow]📝 My Notes:[/bold yellow]\n[italic white]{my_notes}[/italic white]"
                    console.print(Panel(
                        content,
                        title=f"{func_header} [white](module: [bold cyan]{module}[/bold cyan], id: [yellow]#{func_id}[/yellow])[/white]",
                        box=box.ROUNDED,
                        expand=False
                    ))

                if sig != current_sig:
                    if current_table:
                        console.print(current_table)
                        current_table = None

                    current_sig = sig
                    console.print(f"  [bold yellow]Signature:[/] [italic cyan]{sig}[/italic cyan]")
                    if arg_name is not None:
                        current_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
                        current_table.add_column("Index", justify="center", style="yellow")
                        current_table.add_column("Argument", justify="center", style="cyan", no_wrap=True)
                        current_table.add_column("Default Value", justify="center", style="white")
                        current_table.add_column("Required", justify="center")
                    else:
                        console.print("   [italic white](No arguments)[/italic white]\n")

                if arg_name is not None and current_table:
                    req_color = "[bold green]True[/]" if required else "[bold red]False[/]"
                    current_table.add_row(safe_str(order_idx), safe_str(arg_name), safe_str(default_val), req_color)

            if current_table:
                console.print(current_table)
                console.print()
        else:
            console.print(f"[bold red]✘ Function '[bold cyan]{args.function_name}[/bold cyan]' not found or not discovered yet.[/bold red]\n")
    finally:
        cur.close()

def cmd_open_pydex(args, conn):
    cur = conn.cursor()
    try:
        if not args.module_name:
            current_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
            current_table.add_column("Module", justify="center", style="bold cyan")
            current_table.add_column("Discovered", justify="center", style="green")
            current_table.add_column("Total", justify="center", style="blue")
            current_table.add_column("Progress", justify="center", style="bold yellow")

            cur.execute("""
                SELECT m.name, 
                       COUNT(CASE WHEN f.discovered = 1 THEN 1 END) AS discovered,
                       COUNT(f.id) AS total
                FROM modules m 
                LEFT JOIN functions f ON m.id = f.module_id 
                GROUP BY m.id, m.name
                ORDER BY m.id
            """)
            all_rows = cur.fetchall()

            total_disc = sum(r[1] for r in all_rows)
            total_all = sum(r[2] for r in all_rows)
            overall_pct = f"{round(total_disc / total_all * 100, 1)}%" if total_all > 0 else "0.0%"

            display_rows = all_rows if args.all else [r for r in all_rows if r[1] > 0]

            for module_name, discovered, total in display_rows:
                pct = f"{round(discovered / total * 100, 1)}%" if total > 0 else "0.0%"
                current_table.add_row(module_name, str(discovered), str(total), pct)

            current_table.add_section()
            current_table.add_row(
                "[bold white]Total[/bold white]",
                f"[bold green]{total_disc}[/bold green]",
                f"[bold blue]{total_all}[/bold blue]",
                f"[bold yellow]{overall_pct}[/bold yellow]"
            )

            console.print(current_table)
            if not args.all:
                console.print("[yellow]💡 Tip: Use '[bold cyan]pydex open -a[/bold cyan]' to view all modules including 0% progress.[/yellow]\n")

        else:
            filter_important = "" if args.all else "AND f.is_important = 1"
            cur.execute(f"""
                    SELECT f.id, f.name, f.my_notes, f.is_important
                    FROM functions f
                    LEFT JOIN modules m ON m.id=f.module_id
                    WHERE f.discovered=1 AND m.name=? {filter_important}
                    ORDER BY f.id
                    """, (args.module_name,))
            rows = cur.fetchall()
            if not rows:
                console.print(f"[bold yellow]⚠ No discovered functions found in module '[bold cyan]{args.module_name}[/bold cyan]'.[/bold yellow]\n")
                return
            for row in rows:
                func_id, func_name, note, important = row
                note_badge = " 📝" if note else ""
                if important:
                    console.print(f"   [yellow]#{func_id:>3}[/yellow] [bold yellow]★ {func_name}[/bold yellow]{note_badge}")
                else:
                    console.print(f"   [yellow]#{func_id:>3}[/yellow] [bold green]✦ {func_name}[/bold green]{note_badge}")
            if not args.all:
                console.print(f"[yellow]💡 Tip: Use '[bold cyan]pydex open {args.module_name} -a[/bold cyan]' to view all functions in module [bold cyan]{args.module_name}[/bold cyan].[/yellow]")
    finally:
        cur.close()

def cmd_delete_function(args, conn):
    cur = conn.cursor()
    try:
        if args.all:
            console.print("[bold yellow]Are you sure you want to delete all functions from pydex? (y/n):[/bold yellow]")
            response = input().lower()
            if response == "y":
                cur.execute("UPDATE functions SET discovered=0, my_notes=NULL")
                conn.commit()
                console.print("[bold green]✔ All functions deleted from pydex.[/bold green]")
        elif args.function_name:
            cur.execute("UPDATE functions SET discovered=0, my_notes=NULL WHERE name=?", (args.function_name,))
            conn.commit()
            if cur.rowcount > 0:
                console.print(f"[bold green]✔ Function '[bold cyan]{args.function_name}[/bold cyan]' deleted from pydex.[/bold green]")
            else:
                console.print(f"[bold red]✘ Function '[bold cyan]{args.function_name}[/bold cyan]' not found in pydex.[/bold red]")
        else:
            console.print("[bold yellow]Please provide a function name.[/bold yellow]")
    finally:
        cur.close()

def cmd_note(args, conn):
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, my_notes FROM functions WHERE name=? AND discovered=1", (args.function_name,))
        row = cur.fetchone()
        if not row:
            console.print(f"[bold yellow]⚠ Function '[bold cyan]{args.function_name}[/bold cyan]' is not discovered yet.[/bold yellow]")
            return
        func_id, func_name, current_note = row
        if args.note:
            cur.execute("UPDATE functions SET my_notes=? WHERE id=?", (args.note, func_id))
            conn.commit()
            console.print(f"[bold green]✔ Saved note for function '[bold cyan]{func_name}[/bold cyan]'![/bold green]")
        elif args.clear:
            cur.execute("UPDATE functions SET my_notes=NULL WHERE id=?", (func_id,))
            conn.commit()
            console.print(f"[bold green]✔ Cleared note for function '[bold cyan]{func_name}[/bold cyan]'![/bold green]")
        else:
            if current_note:
                console.print(f"📝 [bold yellow]Note for '[bold cyan]{func_name}[/bold cyan]':[/bold yellow] [white]{current_note}[/white]")
            else:
                console.print(f"[yellow]ℹ Function '[bold cyan]{func_name}[/bold cyan]' has no notes. Type '[bold cyan]pydex note {func_name} \"<note>\"[/bold cyan]' to add one![/yellow]")
    finally:
        cur.close()