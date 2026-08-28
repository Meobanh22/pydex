CREATE TABLE functions (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    official_docstring TEXT,
    my_notes TEXT
);

CREATE TABLE arguments (
    id SERIAL PRIMARY KEY,
    function_id INT NOT NULL REFERENCES functions(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT,
    order_index INT NOT NULL
);