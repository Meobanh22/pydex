import argparse

from db import get_connection
from scan_file import find_builtin_call, lookup_and_mark

def safe_str(value, default="N/A"):
    return str(value) if value is not None else default

def cmd_scan(file_path):
    result = find_builtin_call(file_path)
    conn = get_connection()
    lookup_and_mark(result, conn)
    conn.close()
    print("Scan completed!")

def cmd_search(args):
    conn = get_connection()
    with conn.cursor() as cur:
        if args.by_arg:
            query = """SELECT f.id, f.name, f.description, a.name, a.default_value, a.required, a.order_index
                    FROM functions f INNER JOIN arguments a ON f.id=a.function_id
                    WHERE a.name ILIKE %s AND f.discovered=True
                    ORDER BY f.id, a.order_index"""
            params = [args.function_name] 
        else:
            name_condition = "f.name ILIKE %s" if args.partial else "f.name = %s"
            search_value = f"%{args.function_name}%" if args.partial else args.function_name
            query = f"""SELECT f.id, f.name, f.description, a.name, a.default_value, a.required, a.order_index
                        FROM functions f INNER JOIN arguments a ON f.id=a.function_id
                        WHERE {name_condition} AND f.discovered=True"""
            if args.required:
                query += " AND a.required=True"
            query += " ORDER BY f.id, a.order_index"
            params = [search_value]
        cur.execute(query, params)
        rows = cur.fetchall()
        if rows:
            current_function_id = 0
            for row in rows:
                if row[0] != current_function_id:
                    current_function_id = row[0]
                    print(f"\nFunction(id: {row[0]}): {row[1]}")
                    print(f"Description: {row[2]}")
                    print("Arguments:")
                    print("   Name   | Default Value | Required | Order Index ")
                print(f"{safe_str(row[3]):^10}|{safe_str(row[4]):^15}|{safe_str(row[5]):^10}|{safe_str(row[6]):^13}")
        else:
            print(f"Function '{args.function_name}' not found or not discovered.")
    conn.close()

def cmd_open_pydex():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""SELECT id, name FROM functions
                    WHERE discovered=True
                    ORDER BY id""")
        rows = cur.fetchall()
        if rows:
            print("Discovered Built-in Functions:")
            for row in rows:
                print(f"{row[0]}.{row[1]}")
        else:
            print("No discovered built-in functions found.")
    conn.close()

def cmd_delete_function(args):
    conn = get_connection()
    with conn.cursor() as cur:
        if args.all:
            print("Are you sure you want to delete all functions from the database (y/n)?")
            response = input().lower()
            if response == "y":
                cur.execute("Update functions SET discovered=False, my_note=NULL")
                print("All functions deleted from the database.")
        else:
            cur.execute("Update functions SET discovered=False, my_note=NULL WHERE name=%s", (args.function_name,))
            if cur.rowcount > 0:
                print(f"Function '{args.function_name}' deleted from the database.")
            else:
                print(f"Function '{args.function_name}' not found in the database.")
        conn.commit()
    conn.close()

def main():
    parser = argparse.ArgumentParser(prog="pydex", description="Scan a Python file for built-in function calls.")
    subparsers = parser.add_subparsers(dest="command")
    # open command
    pydex_parser = subparsers.add_parser("open", help="Open pydex")
    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan a Python file to find built-in functions.")
    scan_parser.add_argument("file_path", help="Path to the Python file to scan.")
    # search command
    search_parser = subparsers.add_parser("search", help="Search for a built-in function in the database.")
    search_parser.add_argument("function_name", help="Name of the built-in function to search for.")
    search_parser.add_argument("-p", "--partial", action="store_true", help="Enable partial search for function names.")
    search_parser.add_argument("-r", "--required", action="store_true", help="Filter results to show only required arguments.")
    search_parser.add_argument("--by-arg", action="store_true", help="Search by argument name instead of function name.")
    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a built-in function from the database.")
    delete_parser.add_argument("function_name", action="store_true", help="Name of the built-in function to delete.")
    delete_parser.add_argument("-a", "--all", action="store_true", help="Delete all functions in the database.")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args.file_path)

    elif args.command == "search":
        cmd_search(args)

    elif args.command == "open":
        cmd_open_pydex()

    elif args.command == "delete":
        cmd_delete_function(args)

if __name__ == "__main__":
    main()