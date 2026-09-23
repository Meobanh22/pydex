import argparse

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from db import get_connection
from scan_file import scan_file, lookup_and_mark

console = Console()

def safe_str(value, default="N/A"):
    return str(value) if value is not None else default

def cmd_scan(file_path, conn):
    result = scan_file(file_path)
    if result is None:
        return
    if not result:
        console.print("[bold yellow]⚠ No functions found in file[/bold yellow]")
        return
    lookup_and_mark(result, conn)
    console.print("[bold green]✨ Scan completed![/bold green]")

def cmd_search(args, conn):
    with conn.cursor() as cur:
        if args.by_arg:
            query = """SELECT f.id, f.name, f.description, s.raw_signature, a.name, a.default_value, a.required, a.order_index, m.name
                    FROM functions f LEFT JOIN modules m ON f.module_id=m.id LEFT JOIN signatures s ON f.id=s.function_id LEFT JOIN arguments a ON s.id=a.signature_id
                    WHERE a.name ILIKE %s AND f.discovered=True
                    ORDER BY m.id, f.id, s.raw_signature, a.order_index"""
            params = [args.function_name]
        else:
            name_condition = "f.name ILIKE %s" if args.partial else "f.name = %s"
            search_value = f"%{args.function_name}%" if args.partial else args.function_name
            query = f"""SELECT f.id, f.name, f.description, s.raw_signature, a.name, a.default_value, a.required, a.order_index, m.name
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
                func_id, func_name, desc, sig, arg_name, default_val, required, order_idx, module = row
                
                if func_id != current_function_id:
                    if current_table:
                        console.print(current_table)
                        current_table = None

                    current_function_id = func_id
                    current_sig = ""
                    console.print(Panel(
                        f"[white]{desc}[/white]",
                        title=f"[bold green]⚡ {func_name}[/bold green] [dim](module: [yellow]{module}[/yellow], id: {func_id})[/dim]",
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
                        current_table.add_column("Index", justify="right", style="yellow")
                        current_table.add_column("Argument", style="cyan", no_wrap=True)
                        current_table.add_column("Default Value", style="white")
                        current_table.add_column("Required", justify="center")
                    else:
                        console.print("   [dim italic](No arguments)[/dim italic]\n")

                if arg_name is not None and current_table:
                    req_color = "[bold green]True[/]" if required else "[dim red]False[/]"
                    current_table.add_row(safe_str(order_idx), safe_str(arg_name), safe_str(default_val), req_color)

            if current_table:
                console.print(current_table)
                console.print()
        else:
            console.print(f"[bold red]✘[/bold red] Function '[cyan]{args.function_name}[/cyan]' not found or not discovered.\n")

def cmd_open_pydex(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT f.id, f.name, m.name FROM functions f
                    LEFT JOIN modules m ON m.id=f.module_id
                    WHERE discovered=True
                    ORDER BY module_id, id""")
        rows = cur.fetchall()
        if rows:
            console.print("\n[bold magenta]📖 Discovered functions:[/bold magenta]")
            cur_module = ""
            for row in rows:
                if cur_module != row[2]:
                    cur_module = row[2]
                    cur.execute("SELECT COUNT(*) FROM modules m LEFT JOIN functions f ON f.module_id=m.id WHERE m.name=%s", (row[2],))
                    total = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM modules m LEFT JOIN functions f ON f.module_id=m.id WHERE f.discovered=True AND m.name=%s", (row[2],))
                    dis = cur.fetchone()[0]
                    console.print(f"\n📦 [bold cyan]{cur_module}[/bold cyan] ([bold yellow]{dis}/{total}[/bold yellow]):")
                console.print(f"   [dim]#{row[0]:>3}[/dim] [bold green]✦ {row[1]}[/bold green]")
            console.print()
        else:
            console.print("[dim yellow]No discovered function found[/dim yellow]\n")

def cmd_delete_function(args, conn):
    with conn.cursor() as cur:
        if args.all:
            console.print("[bold yellow]Are you sure you want to delete all functions from the database (y/n)?[/bold yellow]")
            response = input().lower()
            if response == "y":
                cur.execute("Update functions SET discovered=False, my_notes=NULL")
                console.print("[bold green]✔ All functions deleted from the database.[/bold green]")
        elif args.function_name:
            cur.execute("Update functions SET discovered=False, my_notes=NULL WHERE name=%s", (args.function_name,))
            if cur.rowcount > 0:
                console.print(f"[bold green]✔ Function '{args.function_name}' deleted from the database.[/bold green]")
            else:
                console.print(f"[bold red]✘ Function '{args.function_name}' not found in the database.[/bold red]")
        else:
            console.print("[bold yellow]Please add a function name[/bold yellow]")
        conn.commit()

def main():
    parser = argparse.ArgumentParser(prog="pydex", description="Scan a Python file for built-in and standard library function calls.")
    subparsers = parser.add_subparsers(dest="command")
    
    # open command
    pydex_parser = subparsers.add_parser("open", help="Open pydex")
    
    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan a Python file to find functions.")
    scan_parser.add_argument("file_path", help="Path to the Python file to scan.")
    
    # search command
    search_parser = subparsers.add_parser("search", help="Search for a function in the database.")
    search_parser.add_argument("function_name", help="Name of the function to search for.")
    search_parser.add_argument("-p", "--partial", action="store_true", help="Enable partial search for function names.")
    search_parser.add_argument("-r", "--required", action="store_true", help="Filter results to show only required arguments.")
    search_parser.add_argument("--by-arg", action="store_true", help="Search by argument name instead of function name.")
    
    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete/reset a function from the database.")
    delete_parser.add_argument("function_name", nargs="?", help="Name of the function to delete.")
    delete_parser.add_argument("-a", "--all", action="store_true", help="Delete all functions in the database.")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        conn = get_connection()
    except Exception as e:
        console.print(f"[bold red]✘ Can't connect to database:[/] {e}")
        return

    try:
        if args.command == "scan":
            cmd_scan(args.file_path, conn)
        elif args.command == "search":
            cmd_search(args, conn)
        elif args.command == "open":
            cmd_open_pydex(conn)
        elif args.command == "delete":
            cmd_delete_function(args, conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()