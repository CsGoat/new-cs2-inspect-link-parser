"""
CS2 New Inspect Link Parser

Parses the new steam://run/730// inspect link format.
The payload is XOR-obfuscated: first byte is the key, remaining bytes
are XOR'd with it. Decrypted data is protobuf (CEconItemPreviewDataBlock)
followed by a 4-byte checksum.

Usage:
    python new_inspect_link_parser.py <inspect_link>
    python new_inspect_link_parser.py  # reads from stdin
"""

import json
import re
import struct
import sys
from dataclasses import asdict, dataclass, field
from urllib.parse import unquote


# ---------------------------------------------------------------------------
# Protobuf wire format (manual implementation)
# ---------------------------------------------------------------------------

_VARINT = 0
_64BIT = 1
_LENGTH_DELIMITED = 2
_32BIT = 5


def _decode_varint(data: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        if offset >= len(data):
            raise ValueError("Truncated varint")
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result, offset


def _decode_raw_fields(data: bytes) -> list[tuple[int, int, bytes | int]]:
    fields = []
    offset = 0
    while offset < len(data):
        tag, offset = _decode_varint(data, offset)
        field_number = tag >> 3
        wire_type = tag & 0x07

        if wire_type == _VARINT:
            value, offset = _decode_varint(data, offset)
            fields.append((field_number, wire_type, value))
        elif wire_type == _64BIT:
            fields.append((field_number, wire_type, data[offset:offset + 8]))
            offset += 8
        elif wire_type == _LENGTH_DELIMITED:
            length, offset = _decode_varint(data, offset)
            fields.append((field_number, wire_type, data[offset:offset + length]))
            offset += length
        elif wire_type == _32BIT:
            fields.append((field_number, wire_type, data[offset:offset + 4]))
            offset += 4
        else:
            raise ValueError(f"Unknown wire type {wire_type} at field {field_number}")

    return fields


def _uint32_to_float(value: int) -> float:
    return struct.unpack('<f', struct.pack('<I', value))[0]


def _parse_float_field(wire_type: int, value) -> float:
    if isinstance(value, bytes):
        return struct.unpack('<f', value)[0]
    return _uint32_to_float(value)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Sticker:
    slot: int = 0
    sticker_id: int = 0
    wear: float = 0.0
    scale: float = 0.0
    rotation: float = 0.0
    tint_id: int = 0
    offset_x: float = 0.0
    offset_y: float = 0.0
    offset_z: float = 0.0
    pattern: int = 0
    highlight_reel: int = 0
    wrapped_sticker: int = 0

    @classmethod
    def from_protobuf(cls, data: bytes) -> "Sticker":
        s = cls()
        for fnum, wtype, val in _decode_raw_fields(data):
            if fnum == 1: s.slot = val
            elif fnum == 2: s.sticker_id = val
            elif fnum == 3: s.wear = _parse_float_field(wtype, val)
            elif fnum == 4: s.scale = _parse_float_field(wtype, val)
            elif fnum == 5: s.rotation = _parse_float_field(wtype, val)
            elif fnum == 6: s.tint_id = val
            elif fnum == 7: s.offset_x = _parse_float_field(wtype, val)
            elif fnum == 8: s.offset_y = _parse_float_field(wtype, val)
            elif fnum == 9: s.offset_z = _parse_float_field(wtype, val)
            elif fnum == 10: s.pattern = val
            elif fnum == 11: s.highlight_reel = val
            elif fnum == 12: s.wrapped_sticker = val
        return s

    def to_dict(self) -> dict:
        d = {}
        if self.slot: d["slot"] = self.slot
        if self.sticker_id: d["sticker_id"] = self.sticker_id
        if self.wear: d["wear"] = round(self.wear, 10)
        if self.scale: d["scale"] = round(self.scale, 10)
        if self.rotation: d["rotation"] = round(self.rotation, 6)
        if self.tint_id: d["tint_id"] = self.tint_id
        if self.offset_x: d["offset_x"] = round(self.offset_x, 10)
        if self.offset_y: d["offset_y"] = round(self.offset_y, 10)
        if self.offset_z: d["offset_z"] = round(self.offset_z, 10)
        if self.pattern: d["pattern"] = self.pattern
        if self.highlight_reel: d["highlight_reel"] = self.highlight_reel
        if self.wrapped_sticker: d["wrapped_sticker"] = self.wrapped_sticker
        return d


@dataclass
class ItemData:
    accountid: int = 0
    itemid: int = 0
    defindex: int = 0
    paintindex: int = 0
    rarity: int = 0
    quality: int = 0
    paintwear: float = 0.0
    paintseed: int = 0
    killeaterscoretype: int = 0
    killeatervalue: int = 0
    customname: str = ""
    stickers: list[Sticker] = field(default_factory=list)
    inventory: int = 0
    origin: int = 0
    questid: int = 0
    dropreason: int = 0
    musicindex: int = 0
    entindex: int = 0
    petindex: int = 0
    keychains: list[Sticker] = field(default_factory=list)
    style: int = 0
    variations: list[Sticker] = field(default_factory=list)
    upgrade_level: int = 0

    @classmethod
    def from_protobuf(cls, data: bytes) -> "ItemData":
        item = cls()
        for fnum, wtype, val in _decode_raw_fields(data):
            if fnum == 1: item.accountid = val
            elif fnum == 2: item.itemid = val
            elif fnum == 3: item.defindex = val
            elif fnum == 4: item.paintindex = val
            elif fnum == 5: item.rarity = val
            elif fnum == 6: item.quality = val
            elif fnum == 7: item.paintwear = _uint32_to_float(val)
            elif fnum == 8: item.paintseed = val
            elif fnum == 9: item.killeaterscoretype = val
            elif fnum == 10: item.killeatervalue = val
            elif fnum == 11: item.customname = val.decode("utf-8") if isinstance(val, bytes) else str(val)
            elif fnum == 12: item.stickers.append(Sticker.from_protobuf(val))
            elif fnum == 13: item.inventory = val
            elif fnum == 14: item.origin = val
            elif fnum == 15: item.questid = val
            elif fnum == 16: item.dropreason = val
            elif fnum == 17: item.musicindex = val
            elif fnum == 18: item.entindex = val
            elif fnum == 19: item.petindex = val
            elif fnum == 20: item.keychains.append(Sticker.from_protobuf(val))
            elif fnum == 21: item.style = val
            elif fnum == 22: item.variations.append(Sticker.from_protobuf(val))
            elif fnum == 23: item.upgrade_level = val
        return item

    def to_dict(self) -> dict:
        d = {}
        if self.accountid: d["accountid"] = self.accountid
        if self.itemid: d["itemid"] = self.itemid
        if self.defindex: d["defindex"] = self.defindex
        if self.paintindex: d["paintindex"] = self.paintindex
        if self.rarity: d["rarity"] = self.rarity
        if self.quality: d["quality"] = self.quality
        if self.paintwear: d["paintwear"] = round(self.paintwear, 10)
        if self.paintseed: d["paintseed"] = self.paintseed
        if self.killeaterscoretype: d["killeaterscoretype"] = self.killeaterscoretype
        if self.killeatervalue: d["killeatervalue"] = self.killeatervalue
        if self.customname: d["customname"] = self.customname
        if self.stickers: d["stickers"] = [s.to_dict() for s in self.stickers]
        if self.inventory: d["inventory"] = self.inventory
        if self.origin: d["origin"] = self.origin
        if self.questid: d["questid"] = self.questid
        if self.dropreason: d["dropreason"] = self.dropreason
        if self.musicindex: d["musicindex"] = self.musicindex
        if self.entindex: d["entindex"] = self.entindex
        if self.petindex: d["petindex"] = self.petindex
        if self.keychains: d["keychains"] = [k.to_dict() for k in self.keychains]
        if self.style: d["style"] = self.style
        if self.variations: d["variations"] = [v.to_dict() for v in self.variations]
        if self.upgrade_level: d["upgrade_level"] = self.upgrade_level
        return d


# ---------------------------------------------------------------------------
# XOR payload decode
# ---------------------------------------------------------------------------

def _xor_bytes(data: bytes, key: int) -> bytes:
    return bytes(b ^ key for b in data)


def decode_payload(hex_string: str) -> tuple[int, ItemData]:
    """Decode a new-format hex payload. Returns (xor_key, ItemData)."""
    raw = bytes.fromhex(hex_string)
    if len(raw) < 6:
        raise ValueError("Payload too short")

    xor_key = raw[0]
    decrypted = _xor_bytes(raw[1:], xor_key)
    proto_bytes = decrypted[:-4]

    return xor_key, ItemData.from_protobuf(proto_bytes)


# ---------------------------------------------------------------------------
# Link parsing
# ---------------------------------------------------------------------------

_LINK_PATTERN = re.compile(
    r"steam://run/(?P<app_id>\d+)/[^/]*"
    r"/\+(?P<command>[a-z_]+)(?:%20|\s)"
    r"(?P<payload>[0-9A-Fa-f]+)",
    re.IGNORECASE,
)


def parse(link: str) -> dict:
    """Parse a new-format CS2 inspect link and return a JSON-serializable dict."""
    link = unquote(link.strip())

    match = _LINK_PATTERN.match(link)
    if not match:
        raise ValueError(f"Invalid inspect link format: {link}")

    payload_hex = match.group("payload")
    xor_key, item_data = decode_payload(payload_hex)

    wear = item_data.paintwear
    if wear < 0.07:
        condition = "Factory New"
    elif wear < 0.15:
        condition = "Minimal Wear"
    elif wear < 0.38:
        condition = "Field-Tested"
    elif wear < 0.45:
        condition = "Well-Worn"
    else:
        condition = "Battle-Scarred"

    result = {
        "link": link,
        "app_id": int(match.group("app_id")),
        "xor_key": f"0x{xor_key:02X}",
        "item": item_data.to_dict(),
    }

    if wear:
        result["item"]["condition"] = condition

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        link = sys.argv[1]
    else:
        link = sys.stdin.readline().strip()

    if not link:
        print("Usage: python new_inspect_link_parser.py <inspect_link>", file=sys.stderr)
        sys.exit(1)

    try:
        result = parse(link)
        print(json.dumps(result, indent=2))
    except ValueError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
