# test/test_intents.py
import sys, os, json, time
sys.path.append(os.path.abspath("."))

print("Importing Intent...")
try:
    from cell_master.intents import Intent
except Exception as e:
    print("ERROR: failed to import Intent:", e)
    raise

def expect(ok, msg):
    if not ok:
        print("[FAIL]", msg)
        raise AssertionError(msg)
    else:
        print("[OK]", msg)

def test_default_fields_and_types():
    print("Testing default fields and types...")
    it = Intent(name="secrete")
    # basic fields
    expect(isinstance(it.intent_id, str) and len(it.intent_id) > 4, "intent_id is a non-empty string")
    expect(it.name == "secrete", "name field preserved")
    expect(isinstance(it.created_ts, float), "created_ts is a float (timestamp)")
    expect(it.payload == {} or isinstance(it.payload, dict), "default payload is dict")
    expect(it.coord is None, "default coord is None")
    expect(it.priority == 0, "default priority == 0")
    expect(it.lifetime is None, "default lifetime is None")
    expect(isinstance(it.flags, dict), "default flags is dict")

def test_to_dict_contents_and_serializable():
    print("Testing to_dict contents and JSON-serializable...")
    payload = {"amount": 3.5, "molecule": "IL2"}
    it = Intent(name="secrete", payload=payload, coord=(1,2), src_cell_id="cell_1", src_cell_type="DC",
                src_genotype={"IL2R":1}, src_activation_state="active", priority=5, lifetime=10,
                flags={"percell_only": True})
    d = it.to_dict()
    # keys present
    expected_keys = {"name","payload","coord","created_ts","intent_id",
                     "src_cell_id","src_cell_type","src_genotype","src_activation_state",
                     "priority","lifetime","flags"}
    expect(expected_keys.issubset(set(d.keys())), "to_dict contains expected keys")
    # values preserved
    expect(d["payload"]["molecule"] == "IL2" and float(d["payload"]["amount"]) == 3.5, "payload values preserved")
    expect(tuple(d["coord"]) == (1,2), "coord preserved in to_dict")
    # JSON serializability check (basic)
    try:
        json.dumps(d)
        ok = True
    except Exception as e:
        ok = False
        print("JSON dump error:", e)
    expect(ok, "to_dict result is JSON-serializable")

def test_repr_and_readability():
    print("Testing __repr__ readability...")
    it = Intent(name="move", coord=(0,0), src_cell_id="c1", src_cell_type="NAIVE_T")
    r = repr(it)
    expect("Intent(" in r and "move" in r and "c1" in r, "__repr__ contains name and src info")

def test_unique_ids_and_timestamp_ordering():
    print("Testing unique ids and timestamp ordering...")
    it1 = Intent(name="a")
    # small sleep to ensure timestamp difference in environments with coarse clock
    time.sleep(0.001)
    it2 = Intent(name="b")
    expect(it1.intent_id != it2.intent_id, "intent_id unique across instances")
    expect(it2.created_ts >= it1.created_ts, "created_ts ordering preserved (it2 >= it1)")

def test_custom_payload_types_are_preserved_but_to_dict_safe():
    print("Testing payload with nested simple types and preserving types...")
    nested = {"list": [1,2,3], "dict": {"x":1}, "num": 7}
    it = Intent(name="test", payload=nested)
    d = it.to_dict()
    expect(d["payload"]["list"] == [1,2,3] and d["payload"]["dict"]["x"] == 1, "nested payload preserved")
    # still JSON-serializable for these basic types
    try:
        json.dumps(d)
        ok = True
    except Exception:
        ok = False
    expect(ok, "nested basic payload is JSON-serializable")

def run_all():
    test_default_fields_and_types()
    test_to_dict_contents_and_serializable()
    test_repr_and_readability()
    test_unique_ids_and_timestamp_ordering()
    test_custom_payload_types_are_preserved_but_to_dict_safe()
    print("\nAll Intent tests passed.")

if __name__ == "__main__":
    run_all()

