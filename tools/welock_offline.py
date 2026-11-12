"""Bibliothek fuer die Offline-Unlock-Forschung (devicePassword / Kommunikationsschluessel).

Ziel: Pruefen, ob sich der Cloud-Unlock-Befehl lokal aus dem per Cloud
abrufbaren ``devicePassword`` (24 Zeichen, BLE-Kommunikationsschluessel) und den
Session-Parametern ``randomFactor`` und ``battery`` reproduzieren laesst. Falls
ja, waere ein Offline-BLE-Unlock ohne Cloud grundsaetzlich moeglich.

Dieses Modul rechnet nur lokal und sendet NICHTS ans Schloss. Es enthaelt die
Schluesselanalyse und einen bewusst breiten, exploratorischen Satz lokaler
Hypothesen, die gegen echte Cloud-Befehle verglichen werden. Ein Treffer ist
nicht garantiert; ausbleibende Treffer schliessen weitere Verfahren nicht aus.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import math
import statistics
import string
from dataclasses import dataclass

HEX_DIGITS = set("0123456789abcdefABCDEF")
B64_ALPHABET = set(string.ascii_letters + string.digits + "+/=")


def shannon_entropy_bits(data: bytes) -> float:
    """Schaetzt die Shannon-Entropie in Bit pro Byte (0..8)."""
    if not data:
        return 0.0
    counts = [0] * 256
    for byte in data:
        counts[byte] += 1
    total = len(data)
    entropy = 0.0
    for count in counts:
        if count:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


@dataclass
class KeyInterpretation:
    """Eine moegliche Deutung des devicePassword als Schluesselbytes."""

    name: str
    raw_bytes: bytes
    note: str = ""


def analyze_key(password: str) -> dict:
    """Analysiert das 24-Zeichen-devicePassword und liefert Deutungen/Kennzahlen."""
    interpretations: list[KeyInterpretation] = []
    ascii_bytes = password.encode("ascii", errors="replace")
    interpretations.append(
        KeyInterpretation("ascii", ascii_bytes, f"{len(ascii_bytes)} Byte direkt als ASCII")
    )

    is_hex = len(password) % 2 == 0 and all(c in HEX_DIGITS for c in password)
    if is_hex:
        try:
            hex_bytes = bytes.fromhex(password)
            interpretations.append(
                KeyInterpretation("hex", hex_bytes, f"{len(hex_bytes)} Byte aus Hex dekodiert")
            )
        except ValueError:
            is_hex = False

    is_b64 = len(password) % 4 == 0 and all(c in B64_ALPHABET for c in password)
    if is_b64:
        try:
            b64_bytes = base64.b64decode(password, validate=True)
            interpretations.append(
                KeyInterpretation(
                    "base64", b64_bytes, f"{len(b64_bytes)} Byte aus Base64 dekodiert"
                )
            )
        except (binascii.Error, ValueError):
            is_b64 = False

    return {
        "length": len(password),
        "charset": {
            "all_hex": is_hex,
            "all_base64": is_b64,
            "all_alnum": password.isalnum(),
            "all_printable": password.isprintable(),
        },
        "entropy_bits_per_char": round(
            shannon_entropy_bits(password.encode("ascii", "replace")), 3
        ),
        "interpretations": interpretations,
    }


@dataclass
class Sample:
    """Ein beobachtetes Tupel (randomFactor, battery) -> Cloud-command."""

    random_factor: int
    battery: int
    command: bytes


@dataclass
class HypothesisResult:
    name: str
    matched: bool
    detail: str = ""


def _inputs_variants(
    random_factor: int, battery: int, device_number: str
) -> list[tuple[str, bytes]]:
    """Verschiedene plausible Klartext-/Nachrichten-Kodierungen der Eingaben."""
    dn = device_number.encode("ascii", "replace")
    rf = random_factor
    bat = battery
    return [
        ("rf,bat", bytes([rf, bat])),
        ("rf,bat,dn", bytes([rf, bat]) + dn),
        ("dn,rf,bat", dn + bytes([rf, bat])),
        ("rf,bat,ascii", f"{rf},{bat}".encode()),
        ("dn,rf,bat,ascii", f"{device_number},{rf},{bat}".encode()),
    ]


def candidate_commands(
    key_bytes: bytes, random_factor: int, battery: int, device_number: str
) -> dict[str, bytes]:
    """Berechnet exploratorische lokale Kandidaten fuer den 15-Byte-Befehl.

    Die Zuordnung Hash/HMAC -> 15-Byte-U1-Format ist hypothetisch: Wir bilden
    13 alphanumerische Zeichen aus einem Digest und stellen "U1" voran, da das
    beobachtete Format "U1" + 13 alphanumerische Zeichen ist.
    """
    alnum = (string.digits + string.ascii_uppercase + string.ascii_lowercase).encode()

    def to_u1(digest: bytes) -> bytes:
        body = bytes(alnum[b % len(alnum)] for b in digest[:13])
        return b"U1" + body

    out: dict[str, bytes] = {}
    for label, msg in _inputs_variants(random_factor, battery, device_number):
        out[f"md5({label})"] = to_u1(hashlib.md5(key_bytes + msg).digest())
        out[f"sha1({label})"] = to_u1(hashlib.sha1(key_bytes + msg).digest())
        out[f"sha256({label})"] = to_u1(hashlib.sha256(key_bytes + msg).digest())
        out[f"hmac_md5({label})"] = to_u1(hmac.new(key_bytes, msg, hashlib.md5).digest())
        out[f"hmac_sha256({label})"] = to_u1(hmac.new(key_bytes, msg, hashlib.sha256).digest())
    return out


def evaluate_hypotheses(
    password: str, device_number: str, samples: list[Sample]
) -> list[HypothesisResult]:
    """Vergleicht lokale Kandidaten gegen beobachtete Cloud-Befehle."""
    if not samples:
        return []
    key_info = analyze_key(password)
    results: list[HypothesisResult] = []
    for interp in key_info["interpretations"]:
        all_match = True
        detail = ""
        for sample in samples:
            candidates = candidate_commands(
                interp.raw_bytes, sample.random_factor, sample.battery, device_number
            )
            hit = next((n for n, c in candidates.items() if c == sample.command), None)
            if hit is None:
                all_match = False
            else:
                detail = f"Treffer via {hit} (Key als {interp.name})"
        results.append(
            HypothesisResult(
                name=f"key={interp.name}",
                matched=all_match and bool(detail),
                detail=detail or "kein Kandidat traf alle Samples",
            )
        )
    return results


def determinism_verdict(samples: list[Sample]) -> dict:
    """Bewertet, ob gleiche Eingaben denselben Befehl liefern (Determinismus)."""
    by_input: dict[tuple[int, int], set[bytes]] = {}
    for s in samples:
        by_input.setdefault((s.random_factor, s.battery), set()).add(s.command)
    deterministic = all(len(v) == 1 for k, v in by_input.items())
    tested_repeats = any(
        sum(1 for s in samples if (s.random_factor, s.battery) == k) > 1 for k in by_input
    )
    return {
        "deterministic_for_tested_inputs": deterministic,
        "tested_a_repeat": tested_repeats,
        "distinct_inputs": len(by_input),
    }


def position_sensitivity(samples: list[Sample]) -> dict:
    """Welche der 13 Befehlspositionen aendern sich ueber die Samples?"""
    bodies = [s.command[2:] for s in samples if len(s.command) == 15]
    if len(bodies) < 2:
        return {"analyzable": False}
    varying = [i for i in range(13) if len({b[i] for b in bodies}) > 1]
    return {
        "analyzable": True,
        "varying_positions": varying,
        "constant_positions": [i for i in range(13) if i not in varying],
    }


# --------------------------------------------------------------------------
# Differenzielle Analyse
#
# Ziel: aus gezielten Einzelbit-Variationen der Eingaben (randomFactor,
# battery) herausfinden, (a) welche der 13 Befehlspositionen von welchem
# Eingabefeld abhaengen (Klartext-Layout) und (b) ob ein einzelnes Eingabebit
# nur wenige Ausgabezeichen aendert (lineare/encoding-artige Abbildung, offline
# direkt angreifbar) oder ~die halbe Ausgabe (Diffusion -> echte Blockchiffre,
# Offline-Reproduktion braucht Algorithmus + Schluessel).
# --------------------------------------------------------------------------

COMMAND_BODY_LEN = 13


def command_body(command: bytes) -> bytes:
    """Die 13 Nutzbytes nach dem ``U1``-Praefix (oder die Eingabe unveraendert)."""
    return command[2:] if len(command) == 15 else command


def hamming_distance_bytes(a: bytes, b: bytes) -> int:
    """Anzahl unterschiedlicher Bits ueber die gemeinsame Laenge zweier Bytefolgen."""
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b, strict=False))


def diff_positions(a: bytes, b: bytes) -> list[int]:
    """Positionen, an denen sich zwei (gleich langer) Bytefolgen unterscheiden."""
    return [i for i in range(min(len(a), len(b))) if a[i] != b[i]]


def differential_sweep(baseline: tuple[int, int] = (7, 100)) -> list[tuple[int, int]]:
    """Baseline (doppelt, fuer Determinismus) + je 8 Einzelbit-Flips von rf/battery.

    Liefert 2 + 8 + 8 = 18 (randomFactor, battery)-Eingaben. Jeder Flip aendert
    genau ein Bit gegenueber der Baseline, sodass sich die Ausgabewirkung eines
    einzelnen Eingabebits isolieren laesst.
    """
    rf0, bat0 = baseline
    sweep: list[tuple[int, int]] = [(rf0, bat0), (rf0, bat0)]
    for bit in range(8):
        sweep.append((rf0 ^ (1 << bit), bat0))
    for bit in range(8):
        sweep.append((rf0, bat0 ^ (1 << bit)))
    return sweep


@dataclass
class DiffResult:
    """Wirkung einer einzelnen Eingabe-Variation auf den Befehl (vs. Baseline)."""

    input_field: str  # "randomFactor" | "battery" | "both"
    input_bit: int | None  # gekipptes Bit, falls genau eines
    input_value: int  # neuer Feldwert
    changed_positions: list[int]
    changed_count: int
    body_bit_distance: int
    body_bits_total: int


def differential_analysis(samples: list[Sample], baseline: tuple[int, int]) -> dict:
    """Vergleicht jede Einzelbit-Variation gegen die Baseline und aggregiert.

    Erwartet Samples aus :func:`differential_sweep` (oder kompatibel). Gibt die
    Positions-Landkarte (welche Positionen reagieren auf rf bzw. battery), die
    strukturell konstanten Positionen und eine Diffusions-Einschaetzung zurueck.
    """
    rf0, bat0 = baseline
    base_cmds = [
        bytes(s.command)
        for s in samples
        if (s.random_factor, s.battery) == baseline and len(s.command) == 15
    ]
    if not base_cmds:
        return {"analyzable": False, "reason": "kein gueltiges Baseline-Sample (U1 + 13 Byte)"}
    base_body = base_cmds[0][2:]
    baseline_deterministic = len(set(base_cmds)) == 1

    diffs: list[DiffResult] = []
    for s in samples:
        if len(s.command) != 15 or (s.random_factor, s.battery) == baseline:
            continue
        body = command_body(s.command)
        if s.battery == bat0 and s.random_factor != rf0:
            field, delta, value = "randomFactor", rf0 ^ s.random_factor, s.random_factor
        elif s.random_factor == rf0 and s.battery != bat0:
            field, delta, value = "battery", bat0 ^ s.battery, s.battery
        else:
            field, delta, value = "both", None, 0
        bit = (delta.bit_length() - 1) if (delta and (delta & (delta - 1)) == 0) else None
        positions = diff_positions(base_body, body)
        diffs.append(
            DiffResult(
                input_field=field,
                input_bit=bit,
                input_value=value,
                changed_positions=positions,
                changed_count=len(positions),
                body_bit_distance=hamming_distance_bytes(base_body, body),
                body_bits_total=len(base_body) * 8,
            )
        )

    rf_positions = sorted(
        {p for d in diffs if d.input_field == "randomFactor" for p in d.changed_positions}
    )
    bat_positions = sorted(
        {p for d in diffs if d.input_field == "battery" for p in d.changed_positions}
    )
    reactive = sorted(set(rf_positions) | set(bat_positions))
    constant = [i for i in range(COMMAND_BODY_LEN) if i not in reactive]

    return {
        "analyzable": True,
        "baseline": {"random_factor": rf0, "battery": bat0},
        "baseline_deterministic": baseline_deterministic,
        "n_variations": len(diffs),
        "random_factor_positions": rf_positions,
        "battery_positions": bat_positions,
        "reactive_positions": reactive,
        "structurally_constant_positions": constant,
        "diffusion": diffusion_verdict(diffs),
        "rf_encoding": fit_rf_encoding(samples),
        "per_variation": [
            {
                "field": d.input_field,
                "bit": d.input_bit,
                "value": d.input_value,
                "changed_positions": d.changed_positions,
                "changed_count": d.changed_count,
                "body_bit_distance": d.body_bit_distance,
            }
            for d in diffs
        ],
    }


B64_ALPHABET_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_B64_VALUE = {c: i for i, c in enumerate(B64_ALPHABET_STD)}


def fit_rf_encoding(samples: list[Sample], *, max_coeff: int = 256) -> dict:
    """Prueft, ob jede Befehlsposition eine geschlossene Funktion von ``rf`` ist.

    Deutet jedes der 13 Befehlszeichen als Base64-Ziffer (6 Bit) und sucht pro
    Position das einfachste Modell:

      * ``const``  – Zeichen ist ueber alle Samples konstant,
      * ``mul``    – Zeichen = ``(rf * k) >> 2 & 63`` fuer einen kleinen Faktor
        ``k`` (6-Bit-Feldauszug aus ``rf*k``; so verhalten sich Positionen 0–7),
      * ``residual`` – kein einfaches Modell (z. B. Pruefziffer/Checksumme).

    Nur von ``battery`` unabhaengige Werte sind sinnvoll; die Funktion nutzt
    daher ausschliesslich die rf-Dimension. Trifft fuer alle Positionen ein
    Modell zu, ist der Befehl ohne Cloud allein aus ``rf`` berechenbar.
    """
    by_rf: dict[int, bytes] = {}
    for s in samples:
        if len(s.command) == 15:
            by_rf.setdefault(s.random_factor, s.command[2:])
    rfs = sorted(by_rf)
    if len(rfs) < 2:
        return {"analyzable": False, "reason": "zu wenige verschiedene rf-Werte"}

    try:
        digits = {rf: [_B64_VALUE[chr(b)] for b in by_rf[rf]] for rf in rfs}
    except KeyError:
        return {"analyzable": False, "reason": "Befehl ist nicht vollstaendig Base64"}

    models: dict[int, dict] = {}
    for pos in range(COMMAND_BODY_LEN):
        col = {rf: digits[rf][pos] for rf in rfs}
        values = set(col.values())
        if len(values) == 1:
            models[pos] = {"kind": "const", "value": next(iter(values))}
            continue
        found = None
        for k in range(1, max_coeff + 1):
            if all(((rf * k) >> 2) & 63 == col[rf] for rf in rfs):
                found = k
                break
        models[pos] = {"kind": "mul", "coeff": found} if found else {"kind": "residual"}

    explained = [p for p, m in models.items() if m["kind"] != "residual"]
    residual = [p for p, m in models.items() if m["kind"] == "residual"]
    return {
        "analyzable": True,
        "n_rf": len(rfs),
        "models": models,
        "explained_positions": explained,
        "residual_positions": residual,
        "fully_closed_form": not residual,
    }


def rf_table_from_samples(samples: list[Sample]) -> dict[int, str]:
    """Baut die Tabelle ``rf -> command`` (als ASCII-String) aus Samples.

    Da der Befehl nur von ``randomFactor`` abhaengt, genuegt ein Eintrag je
    ``rf``. Bei widerspruechlichen Befehlen zum selben ``rf`` gewinnt der erste
    (Determinismus ist an anderer Stelle geprueft).
    """
    table: dict[int, str] = {}
    for s in samples:
        if len(s.command) == 15 and s.random_factor not in table:
            table[s.random_factor] = s.command.decode("ascii", "replace")
    return table


def command_for_rf(table: dict[int, str], rf: int) -> str | None:
    """Liefert den Offline-Befehl fuer ein Challenge-Byte ``rf`` aus der Tabelle."""
    return table.get(rf)


def verify_table_consistency(table: dict[int, str]) -> dict:
    """Prueft Vollstaendigkeit (0..255) und Konsistenz mit der rf-Formel.

    Gibt zurueck, wie viele der 256 ``rf``-Werte vorhanden sind und ob die
    geschlossene Form (pos0-7 multiplikativ, pos8-11 konstant) ueber alle
    Eintraege haelt. Nuetzlich, um eine geerntete Tabelle gegen Uebertragungs-
    oder Encodingfehler abzusichern.
    """
    present = sorted(table)
    missing = [rf for rf in range(256) if rf not in table]
    samples = [Sample(rf, 0, table[rf].encode("ascii", "replace")) for rf in present]
    fit = fit_rf_encoding(samples)
    return {
        "count": len(present),
        "complete": not missing,
        "missing": missing,
        "fit": fit,
    }


def diffusion_verdict(diffs: list[DiffResult]) -> dict:
    """Schaetzt aus den Einzelbit-Diffs, ob die Abbildung diffus oder linear ist."""
    single = [d for d in diffs if d.input_bit is not None and d.changed_count > 0]
    if not single:
        changed_any = any(d.changed_count > 0 for d in diffs)
        return {
            "classifiable": False,
            "reason": (
                "kein Einzelbit-Flip veraenderte die Ausgabe"
                if not changed_any
                else "keine eindeutig einbittigen Variationen"
            ),
        }
    mean_positions = statistics.mean(d.changed_count for d in single)
    mean_bits = statistics.mean(d.body_bit_distance for d in single)
    total = single[0].body_bits_total
    if mean_positions >= 4:
        verdict = "diffusion"
        interpretation = (
            "Ein einzelnes Eingabebit aendert im Mittel viele Ausgabezeichen "
            "(Avalanche) -> blockchiffre-artig; Offline-Reproduktion erfordert "
            "Algorithmus + Schluessel (nicht direkt umkehrbar)."
        )
    elif mean_positions <= 1.5:
        verdict = "linear/encoding"
        interpretation = (
            "Ein einzelnes Eingabebit aendert nur sehr wenige Ausgabezeichen "
            "-> lineare/encoding-artige Abbildung; offline wahrscheinlich direkt "
            "rekonstruierbar (Positionszuordnung bestimmen)."
        )
    else:
        verdict = "partiell"
        interpretation = (
            "Teilweise Diffusion -> gemischte Struktur (z. B. kleiner Block oder "
            "Encoding mit lokaler Durchmischung); weitere gezielte Variation noetig."
        )
    return {
        "classifiable": True,
        "verdict": verdict,
        "mean_changed_positions": round(mean_positions, 2),
        "mean_changed_positions_of": COMMAND_BODY_LEN,
        "mean_body_bit_distance": round(mean_bits, 2),
        "body_bits_total": total,
        "interpretation": interpretation,
    }
