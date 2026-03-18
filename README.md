# cs2-inspect-parser

A zero-dependency Python parser for CS2's new inspect link format (`steam://run/730//`).

The new format encodes a XOR-obfuscated protobuf payload directly in the link, no Steam API or Game Coordinator needed. This parser decodes the payload from scratch with a hand-rolled protobuf decoder.

## Usage

```bash
python new_inspect_link_parser.py <inspect_link>
```

```bash
python new_inspect_link_parser.py "steam://run/730//+csgo_econ_action_preview%20213190EEA6B98220392801F923092711251987CDDECC2261EC2043252922310449205139BD1CEC93"
```

Output:

```json
{
  "link": "steam://run/730//+csgo_econ_action_preview 213190EEA6B98220392801F923092711251987CDDECC2261EC2043252922310449205139BD1CEC93",
  "app_id": 730,
  "xor_key": "0x21",
  "item": {
    "itemid": 43805435825,
    "defindex": 9,
    "paintindex": 344,
    "rarity": 6,
    "quality": 4,
    "paintwear": 0.0937312096,
    "paintseed": 205,
    "stickers": [
      {
        "slot": 3,
        "sticker_id": 37
      }
    ],
    "inventory": 1,
    "origin": 24,
    "condition": "Minimal Wear"
  }
}
```

You can also use it as a library:

```python
from new_inspect_link_parser import parse

result = parse("steam://run/730//+csgo_econ_action_preview%20...")
print(result["item"]["paintwear"])
```

## How It Works

1. **Extract** the hex payload from the inspect link URL
2. **XOR decode** first byte is the key, remaining bytes are XOR'd with it
3. **Protobuf decode** the decrypted bytes are a `CEconItemPreviewDataBlock` protobuf message (minus a 4-byte trailing checksum)
4. **Output** structured JSON with all parsed item fields

## Parsed Fields

| Field | Description |
|-------|-------------|
| `defindex` | Item definition index (weapon type) |
| `paintindex` | Paint kit index (skin) |
| `paintwear` | Float wear value |
| `paintseed` | Pattern seed |
| `rarity` | Item rarity tier |
| `quality` | Item quality (normal, stattrak, souvenir, etc.) |
| `killeaterscoretype` | StatTrak counter type |
| `killeatervalue` | StatTrak kill count |
| `customname` | Nametag |
| `stickers` | Array of applied stickers with slot, ID, wear, rotation, offsets |
| `keychains` | Array of applied keychains |
| `condition` | Human-readable wear range (Factory New → Battle-Scarred) |

## Requirements

Python 3.10+ (no external dependencies)
