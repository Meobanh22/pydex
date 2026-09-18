CREATE TABLE modules (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE functions (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    module_id INT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    description TEXT,
    my_notes TEXT,
    discovered BOOLEAN DEFAULT FALSE,
    CONSTRAINT uq_func UNIQUE (module_id, name)
);

CREATE TABLE signatures (
    id SERIAL PRIMARY KEY,
    function_id INT NOT NULL REFERENCES functions(id) ON DELETE CASCADE,
    raw_signature TEXT NOT NULL
);

CREATE TABLE arguments (
    id SERIAL PRIMARY KEY,
    signature_id INT NOT NULL REFERENCES signatures(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    order_index INT NOT NULL,
    default_value TEXT,
    required BOOLEAN DEFAULT TRUE
);