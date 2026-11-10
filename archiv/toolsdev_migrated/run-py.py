"""Interaktives Menü zum Auflisten und Ausführen von Python-Skripten im aktuellen Verzeichnis."""

import os
import subprocess
import sys


def get_python_scripts() -> list[str]:
    """Sucht alle .py-Dateien im aktuellen Verzeichnis (außer dem Skript selbst)."""
    current_script = os.path.basename(__file__)
    scripts = []
    
    for file in sorted(os.listdir(".")):
        if file.endswith(".py") and file != current_script:
            if os.path.isfile(file):
                scripts.append(file)
                
    return scripts


def main() -> int:
    while True:
        scripts = get_python_scripts()
        
        print("\n" + "=" * 50)
        print("  VERFÜGBARE PYTHON-SKRIPTE")
        print("=" * 50)
        
        if not scripts:
            print("Keine weiteren Python-Skripte im aktuellen Verzeichnis gefunden.")
            print("0: Beenden")
        else:
            for index, script in enumerate(scripts, 1):
                print(f"[{index}] {script}")
            print("[0] Beenden")
            print("-" * 50)
            
        choice = input("\nBitte Nummer eingeben und mit Enter bestätigen: ").strip()
        
        if choice == "0":
            print("Programm beendet.")
            return 0
            
        if not choice.isdigit():
            print("Ungültige Eingabe. Bitte gib eine Zahl ein.")
            continue
            
        index = int(choice)
        if 1 <= index <= len(scripts):
            selected_script = scripts[index - 1]
            print(f"\n--- Starte: {selected_script} ---\n")
            
            try:
                # Führt das Skript mit demselben Python-Interpreter aus
                subprocess.run([sys.executable, selected_script])
            except Exception as e:
                print(f"\nFehler beim Ausführen von {selected_script}: {e}", file=sys.stderr)
                
            input("\nDrücke Enter, um zum Menü zurückzukehren...")
        else:
            print("Ungültige Nummer. Bitte wähle eine Option aus der Liste.")


if __name__ == "__main__":
    raise SystemExit(main())