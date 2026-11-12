"""Gemeinsame Konsolen-Helfer fuer die WeLock-Werkzeuge.

Buendelt wiederkehrende Interaktionen: Einwilligung einholen, verdeckte oder
aus der Umgebung gelesene Passworteingabe, Auswahl aus einer Liste und das
Maskieren personenbezogener Werte fuer die Ausgabe.
"""

from __future__ import annotations

import getpass
import os
import warnings
from collections.abc import Callable, Sequence
from typing import TypeVar

T = TypeVar("T")

PASSWORD_ENV = "WELOCK_PASSWORD"


def mask(value: object) -> str:
    """Maskiert einen Wert fuer die Ausgabe; behaelt die E-Mail-Domain."""
    if value is None:
        return "-"
    text = str(value)
    if not text:
        return "-"
    if "@" in text:
        local, _, domain = text.partition("@")
        return f"{(local[0] if local else '')}***@{domain}"
    if len(text) <= 2:
        return "*" * len(text)
    return text[0] + "*" * (len(text) - 2) + text[-1]


def confirm(prompt: str, *, expected: str = "JA", auto_yes: bool = False) -> bool:
    """Fragt eine ausdrueckliche Bestaetigung ab (Gross-/Kleinschreibung genau)."""
    if auto_yes:
        return True
    return input(prompt).strip() == expected


def read_password(*, env_var: str | None = PASSWORD_ENV, prompt: str = "WeLock-Passwort: ") -> str:
    """Liest das Passwort aus der Umgebung oder verdeckt vom Terminal.

    Wirft ``RuntimeError``, wenn keine verdeckte Eingabe moeglich ist.
    """
    if env_var:
        from_env = os.environ.get(env_var)
        if from_env:
            return from_env
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            return getpass.getpass(prompt)
    except getpass.GetPassWarning as exc:
        raise RuntimeError(
            "Verdeckte Passworteingabe wird im aktuellen Terminal nicht unterstuetzt."
        ) from exc


def select_index(
    items: Sequence[T],
    *,
    render: Callable[[T], str],
    prompt: str = "Nummer auswaehlen: ",
    header: str | None = None,
) -> T | None:
    """Zeigt eine nummerierte Liste und gibt den gewaehlten Eintrag zurueck.

    Gibt ``None`` bei leerer Liste oder unguetiger Auswahl zurueck.
    """
    if not items:
        return None
    if header:
        print(header)
    for index, item in enumerate(items, 1):
        print(f"  [{index}] {render(item)}")
    selection = input(prompt).strip()
    if not selection.isdecimal() or not 1 <= int(selection) <= len(items):
        return None
    return items[int(selection) - 1]
