import argparse
from db import get_connection
from commands import cmd_delete_function, cmd_open_pydex, cmd_scan, cmd_search, cmd_note, console

def main():
    parser = argparse.ArgumentParser(prog="pydex", description="CLI tool for exploring Python standard libraries and functions with pydex.")
    subparsers = parser.add_subparsers(dest="command")
    
    # open command
    pydex_parser = subparsers.add_parser("open", help="Browse discovered modules and functions.")
    pydex_parser.add_argument("module_name", nargs="?", help="Module name to inspect.")
    pydex_parser.add_argument("-a", "--all", action="store_true", help="Show all functions in module (or all modules in overview).")
    
    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan a Python file to find functions.")
    scan_parser.add_argument("file_path", help="Path to the Python file to scan.")
    
    # search command
    search_parser = subparsers.add_parser("search", help="Search for a function in pydex.")
    search_parser.add_argument("function_name", help="Name of the function to search for.")
    search_parser.add_argument("-p", "--partial", action="store_true", help="Enable partial search for function names.")
    search_parser.add_argument("-r", "--required", action="store_true", help="Filter results to show only required arguments.")
    search_parser.add_argument("--by-arg", action="store_true", help="Search by argument name instead of function name.")

    # take note
    note_parser = subparsers.add_parser("note", help="View, add, or clear personal notes for a function.")
    note_parser.add_argument("function_name", help="Name of the function.")
    note_parser.add_argument("note", nargs="?", help="Note text to save.")
    note_parser.add_argument("-c", "--clear", action="store_true", help="Clear existing note for the function.")

    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a function from pydex.")
    delete_parser.add_argument("function_name", nargs="?", help="Name of the function to delete.")
    delete_parser.add_argument("-a", "--all", action="store_true", help="Delete all functions from pydex.")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        conn = get_connection()
    except Exception as e:
        console.print(f"[bold red]✘ Cannot connect to pydex:[/] {e}")
        return

    try:
        if args.command == "scan":
            cmd_scan(args.file_path, conn)
        elif args.command == "search":
            cmd_search(args, conn)
        elif args.command == "open":
            cmd_open_pydex(args, conn)
        elif args.command == "note":
            cmd_note(args, conn)
        elif args.command == "delete":
            cmd_delete_function(args, conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()