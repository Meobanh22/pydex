CREATE TABLE IF NOT EXISTS modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS functions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    description TEXT,
    my_notes TEXT,
    discovered BOOLEAN DEFAULT 0,
    is_important BOOLEAN DEFAULT 0,
    CONSTRAINT uq_func UNIQUE (module_id, name)
);

CREATE TABLE IF NOT EXISTS signatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    function_id INTEGER NOT NULL REFERENCES functions(id) ON DELETE CASCADE,
    raw_signature TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS arguments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signature_id INTEGER NOT NULL REFERENCES signatures(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    default_value TEXT,
    required BOOLEAN DEFAULT 1
);