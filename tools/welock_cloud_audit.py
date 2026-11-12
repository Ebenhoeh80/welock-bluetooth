"""Read-only WeLock Cloud-Audit: Zutrittsprotokoll und Berechtigungen abfragen.

Fragt ausschliesslich LESENDE Cloud-Endpunkte ab (ueber die strikte Whitelist
in ``welock_cloud_login``) und sendet weder einen Unlock- noch einen anderen
Geraetebefehl. Es speichert keine Zugangsdaten, Tokens oder Antwortdaten.
E-Mail/Konto und BLE-MAC werden im Klartext gezeigt (sie werden ohnehin
uebertragen und sind auslesbar). Nur die Telefonnummer und das
Kommunikationspasswort (BLE-Schluessel) werden standardmaessig maskiert;
``--show-pii`` zeigt auch diese im Klartext. Das Passwort kommt aus
``getpass`` oder der Umgebungsvariable WELOCK_PASSWORD.

Hinweis: Jeder Cloud-Login meldet andere Sitzungen des Kontos ab (App, HA).
"""

from __future__ import annotations

import argparse
import json
import sys

try:
    from welock_cloud_login import CloudError, CloudSession
    from welock_ui import confirm, mask, read_password, select_index
except ImportError:
    from tools.welock_cloud_login import CloudError, CloudSession
    from tools.welock_ui import confirm, mask, read_password, select_index

# Beobachtete, NICHT abschliessend bewiesene Bedeutungen (App 4.5.8, SECBREBL01).
OPERATING_STATE = {1: "lokal/Knauf o. Taste", 6: "BLE/App (cloud-gestuetzt)"}
UNLOCK_RESULT = {1: "Erfolg"}
ROLE_ID = {1: "Eigentuemer/Admin"}


def _label(mapping: dict[int, str], value: object) -> str:
    return (
        f"{value} ({mapping[value]})" if isinstance(value, int) and value in mapping else str(value)
    )


def fetch_audit(
    session: CloudSession, device_number: str, *, page_size: int = 30, pages: int = 1
) -> dict[str, object]:
    """Holt Zutrittsprotokoll, Berechtigungen und Geraeteinfo (nur lesend)."""
    records: list[dict] = []
    for page_no in range(1, pages + 1):
        page = session.get_unlock_record(device_number, page_no=page_no, page_size=page_size)
        records.extend(page)
        if len(page) < page_size:
            break
    return {
        "records": records,
        "permissions": session.permission_list(device_number),
        "device_info": session.get_device_info(device_number),
    }


def print_report(audit: dict[str, object], *, show_pii: bool) -> None:
    def clear(v: object) -> str:  # E-Mail/MAC: nicht schuetzenswert
        return str(v) if v is not None else "-"

    show = clear if show_pii else mask  # Telefon/Schluessel: maskiert, ausser --show-pii
    records = audit["records"]
    permissions = audit["permissions"]
    info = audit["device_info"]

    print("\n" + "=" * 72)
    print("  ZUTRITTSPROTOKOLL (wer hat geoeffnet, wann, wie)")
    print("=" * 72)
    if not records:
        print("  (keine Eintraege)")
    for e in records:  # type: ignore[union-attr]
        name = e.get("nickName") or e.get("userName") or ""
        print(
            f"  {e.get('unlockingTime')} | {name!r:18} konto={clear(e.get('userName'))} "
            f"tel={show(e.get('mobile'))} methode={_label(OPERATING_STATE, e.get('operatingState'))} "
            f"ergebnis={_label(UNLOCK_RESULT, e.get('unlockResult'))} pos={e.get('position')}"
        )

    print("\n" + "=" * 72)
    print("  BERECHTIGTE NUTZER (wer ist administriert)")
    print("=" * 72)
    if not permissions:
        print("  (keine Eintraege)")
    for p in permissions:  # type: ignore[union-attr]
        print(
            f"  {p.get('nickName')!r:18} konto={clear(p.get('account'))} "
            f"rolle={_label(ROLE_ID, p.get('roleID'))} gueltig={p.get('beginTime') or '-'}.."
            f"{p.get('endTime') or '-'} erstellt={p.get('creationTime')} remark={p.get('remark')!r}"
        )

    if info:
        print("\n" + "=" * 72)
        print("  GERAETEINFO")
        print("=" * 72)
        print(
            f"  Modell={info.get('model')} eigene Rolle={_label(ROLE_ID, info.get('roleLevel'))} "
            f"Schloss={info.get('deviceNumber')}"
        )
        for b in info.get("ble", []) or []:
            if not isinstance(b, dict):
                continue
            ver = b.get("version") or {}
            pwd = b.get("devicePassword")
            pwd_disp = (
                (str(pwd) if show_pii else f"<{len(str(pwd))} Zeichen, maskiert>") if pwd else "-"
            )
            print(
                f"  BLE pos={b.get('position')} name={b.get('deviceName')} mac={clear(b.get('deviceMac'))} "
                f"power={b.get('power')}% fw={ver.get('firmware')} hw={ver.get('hardware')} "
                f"komm.passwort={pwd_disp}"
            )


def _resolve_number(session: CloudSession, number: str | None, as_json: bool) -> str:
    if number:
        return number
    devices = session.list_devices()
    unique: list[tuple[str, str]] = []
    for num, name, _ble in devices:
        if num not in {u[0] for u in unique}:
            unique.append((num, name))
    if len(unique) == 1:
        return unique[0][0]
    if as_json or not unique:
        raise CloudError("Schlossnummer nicht eindeutig; bitte --number angeben.")
    chosen = select_index(
        unique, render=lambda it: f"{it[0]} ({it[1]})", header="\nRegistrierte Schloesser:"
    )
    if chosen is None:
        raise CloudError("Keine gueltige Auswahl.")
    return chosen[0]


def run(
    *,
    account: str | None,
    number: str | None,
    pages: int,
    page_size: int,
    show_pii: bool,
    as_json: bool,
    auto_yes: bool,
) -> int:
    if not as_json:
        print("Read-only WeLock Cloud-Audit: kein Unlock, keine Mutation, keine Speicherung.")
        print("Hinweis: Eine Anmeldung kann bestehende WeLock-Sitzungen (App/HA) abmelden.")
    if not confirm("Fortfahren? JA eingeben: ", auto_yes=auto_yes or as_json):
        print("Abgebrochen.")
        return 1

    if not account:
        account = input("WeLock-Konto (E-Mail): ").strip()
    if not account:
        print("Fehler: E-Mail darf nicht leer sein.", file=sys.stderr)
        return 1

    try:
        password = read_password(prompt="WeLock-Passwort (verdeckt; oder ENV WELOCK_PASSWORD): ")
    except RuntimeError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1

    session = CloudSession()
    try:
        session.authenticate(account, password)
        del password
        number = _resolve_number(session, number, as_json)
        audit = fetch_audit(session, number, page_size=page_size, pages=pages)
    except CloudError as exc:
        if as_json:
            print(json.dumps({"success": False, "error": str(exc)}))
        else:
            print(f"Fehler: {exc}", file=sys.stderr)
        return 1

    if as_json:
        print(
            json.dumps(
                {"success": True, "device_number": number, **audit}, ensure_ascii=False, indent=2
            )
        )
        return 0
    print_report(audit, show_pii=show_pii)
    print("\nKein Token gespeichert, kein Befehl gesendet.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only WeLock Cloud-Audit: Zutrittsprotokoll und Berechtigungen."
    )
    parser.add_argument(
        "positional_account", nargs="?", default=None, help="WeLock-Konto (E-Mail)."
    )
    parser.add_argument("--account", "-u", default=None, help="WeLock-Konto (E-Mail).")
    parser.add_argument("--number", "-n", default=None, help="Schlossnummer (deviceNumber).")
    parser.add_argument("--pages", type=int, default=1, help="Protokollseiten (Standard 1).")
    parser.add_argument(
        "--page-size", type=int, default=30, help="Eintraege pro Seite (Standard 30)."
    )
    parser.add_argument(
        "--show-pii",
        action="store_true",
        help="Auch Tel/Kommunikationspasswort im Klartext (Konto/MAC ohnehin Klartext).",
    )
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Bestaetigung automatisch akzeptieren."
    )
    parser.add_argument(
        "--json", action="store_true", help="Ausgabe als JSON (impliziert Klartext)."
    )
    args = parser.parse_args(argv)

    if args.pages < 1 or not 1 <= args.page_size <= 100:
        parser.error("--pages >= 1 und 1 <= --page-size <= 100 erforderlich.")

    try:
        return run(
            account=args.account or args.positional_account,
            number=args.number,
            pages=args.pages,
            page_size=args.page_size,
            show_pii=args.show_pii,
            as_json=args.json,
            auto_yes=args.yes,
        )
    except (EOFError, KeyboardInterrupt):
        print("\nAbbruch durch Benutzer.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
