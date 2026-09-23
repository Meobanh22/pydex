from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from scan_file import lookup_and_mark, scan_file

console = Console()

def safe_str(value, default="N/A"):
    return str(value) if value is not None else default

def cmd_scan(file_path, conn):
    result = scan_file(file_path)
    if result is None:
        return
    if not result:
        console.print("[bold yellow]⚠ No functions found in the file.[/bold yellow]")
        return
    lookup_and_mark(result, conn)
    console.print("[bold green]✨ Scan completed![/bold green]")

def cmd_search(args, conn):
    with conn.cursor() as cur:
        if args.by_arg:
            query = """SELECT f.id, f.name, f.description, f.my_notes, f.is_important, s.raw_signature, a.name, a.default_value, a.required, a.order_index, m.name
                    FROM functions f LEFT JOIN modules m ON f.module_id=m.id LEFT JOIN signatures s ON f.id=s.function_id LEFT JOIN arguments a ON s.id=a.signature_id
                    WHERE a.name ILIKE %s AND f.discovered=True
                    ORDER BY m.id, f.id, s.raw_signature, a.order_index"""
            params = [args.function_name]
        else:
            name_condition = "f.name ILIKE %s" if args.partial else "f.name = %s"
            search_value = f"%{args.function_name}%" if args.partial else args.function_name
            query = f"""SELECT f.id, f.name, f.description, f.my_notes, f.is_important, s.raw_signature, a.name, a.default_value, a.required, a.order_index, m.name
                        FROM functions f LEFT JOIN modules m ON f.module_id=m.id LEFT JOIN signatures s ON f.id=s.function_id LEFT JOIN arguments a ON s.id=a.signature_id 
                        WHERE {name_condition} AND f.discovered=True"""
            if args.required:
                query += " AND a.required=True"
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

def cmd_open_pydex(args, conn):
    with conn.cursor() as cur:
        if not args.module_name:
            current_table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
            current_table.add_column("Module", justify="center", style="bold cyan")
            current_table.add_column("Discovered", justify="center", style="green")
            current_table.add_column("Total", justify="center", style="blue")
            current_table.add_column("Progress", justify="center", style="bold yellow")

            having_clause = "" if args.all else "HAVING COUNT(CASE WHEN f.discovered THEN 1 END) > 0"
            cur.execute(f"""SELECT m.name, 
                        COUNT(CASE WHEN f.discovered THEN 1 END) AS discovered,
                        COUNT(f.id) AS total
                        FROM modules m 
                        LEFT JOIN functions f ON m.id = f.module_id 
                        GROUP BY m.id, m.name {having_clause}
                        ORDER BY m.id""")
            rows = cur.fetchall()
            for module_name, discovered, total in rows:
                pct = f"{round(discovered / total * 100, 1)}%" if total > 0 else "0.0%"
                current_table.add_row(module_name, str(discovered), str(total), pct)

            console.print(current_table)
            if not args.all:
                console.print("[yellow]💡 Tip: Use '[bold cyan]pydex open -a[/bold cyan]' to view all modules including 0% progress.[/yellow]\n")
        else:
            filter_important = "" if args.all else "AND f.is_important = True"
            cur.execute(f"""
                    SELECT f.id, f.name, f.my_notes, f.is_important
                    FROM functions f
                    LEFT JOIN modules m ON m.id=f.module_id
                    WHERE f.discovered=True AND m.name=%s {filter_important}
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

def cmd_delete_function(args, conn):
    with conn.cursor() as cur:
        if args.all:
            console.print("[bold yellow]Are you sure you want to delete all functions from pydex? (y/n):[/bold yellow]")
            response = input().lower()
            if response == "y":
                cur.execute("Update functions SET discovered=False, my_notes=NULL")
                console.print("[bold green]✔ All functions deleted from pydex.[/bold green]")
        elif args.function_name:
            cur.execute("Update functions SET discovered=False, my_notes=NULL WHERE name=%s", (args.function_name,))
            if cur.rowcount > 0:
                console.print(f"[bold green]✔ Function '[bold cyan]{args.function_name}[/bold cyan]' deleted from pydex.[/bold green]")
            else:
                console.print(f"[bold red]✘ Function '[bold cyan]{args.function_name}[/bold cyan]' not found in pydex.[/bold red]")
        else:
            console.print("[bold yellow]Please provide a function name.[/bold yellow]")
        conn.commit()

def cmd_note(args, conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, my_notes FROM functions WHERE name=%s AND discovered=True", (args.function_name,))
        row = cur.fetchone()
        if not row:
            console.print(f"[bold yellow]⚠ Function '[bold cyan]{args.function_name}[/bold cyan]' is not discovered yet.[/bold yellow]")
            return
        func_id, func_name, current_note = row
        if args.note:
            cur.execute("UPDATE functions SET my_notes=%s WHERE id=%s", (args.note, func_id))
            conn.commit()
            console.print(f"[bold green]✔ Saved note for function '[bold cyan]{func_name}[/bold cyan]'![/bold green]")
        elif args.clear:
            cur.execute("UPDATE functions SET my_notes=NULL WHERE id=%s", (func_id,))
            console.print(f"[bold green]✔ Cleared note for function '[bold cyan]{func_name}[/bold cyan]'![/bold green]")
        else:
            if current_note:
                console.print(f"📝 [bold yellow]Note for '[bold cyan]{func_name}[/bold cyan]':[/bold yellow] [white]{current_note}[/white]")
            else:
                console.print(f"[yellow]ℹ Function '[bold cyan]{func_name}[/bold cyan]' has no notes. Type '[bold cyan]pydex note {func_name} \"<note>\"[/bold cyan]' to add one![/yellow]")
    conn.commit()