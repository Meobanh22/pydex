def test_seed_data_integrity(test_db):
    cur = test_db.cursor()

    cur.execute("SELECT COUNT(*) FROM modules")
    module_count = cur.fetchone()[0]
    assert module_count == 18

    cur.execute("SELECT COUNT(*) FROM functions")
    function_count = cur.fetchone()[0]
    assert function_count == 485

    cur.execute("SELECT COUNT(*) FROM functions WHERE is_important = 1")
    important_function_count = cur.fetchone()[0]
    assert important_function_count == 119

def test_add_and_update_notes(test_db):
    cur = test_db.cursor()

    # Add a note to a function
    cur.execute("SELECT id FROM functions WHERE name = 'sqrt' LIMIT 1")
    func_id = cur.fetchone()[0]
    note_text = "This is a test note."
    cur.execute("UPDATE functions SET my_notes = ? WHERE id = ?", (note_text, func_id))
    test_db.commit()

    # Verify the note was added
    cur.execute("SELECT my_notes FROM functions WHERE id = ?", (func_id,))
    retrieved_note = cur.fetchone()[0]
    assert retrieved_note == note_text

    # Update the note
    updated_note_text = "This is an updated test note."
    cur.execute("UPDATE functions SET my_notes = ? WHERE id = ?", (updated_note_text, func_id))
    test_db.commit()

    # Verify the note was updated
    cur.execute("SELECT my_notes FROM functions WHERE id = ?", (func_id,))
    retrieved_updated_note = cur.fetchone()[0]
    assert retrieved_updated_note == updated_note_text