# IPP Print für Home Assistant

PDF, JPG und PNG aus Home Assistant direkt auf einen Netzwerkdrucker schicken –
ohne Treiber, ohne CUPS, ohne Zusatzsoftware. Ein Seitenleisten-Eintrag
**Drucken** bietet Datei-Upload oder URL, Papierauswahl und eine Vorschau, die
genau das zeigt, was aufs Papier geht.

## Warum kein PDF an den Drucker geht

Der Drucker bekommt über IPP (`ipps://…/ipp/print`) nur
`image/jpeg`, `image/pwg-raster` und `image/urf` – kein PDF. Deshalb rendert die
Integration lokal (PDFium für PDF, Pillow für Bilder) jede Seite als JPEG in der
gewählten Papiergröße. Genau dieses JPEG zeigt die Vorschau und genau dieses
JPEG geht als Druckjob raus. Kein Gerätetreiber, keine Fremdsoftware.

## Installation

HACS → Integrationen → Drei-Punkte-Menü → *Benutzerdefinierte Repositories* →
`https://github.com/comdata/ha-ipp-print` als *Integration* hinzufügen, dann
installieren und Home Assistant neu starten.

Manuell: den Ordner `custom_components/ipp_print` nach
`config/custom_components/` kopieren und neu starten.

## Einrichtung

*Einstellungen → Geräte & Dienste → Integration hinzufügen → IPP Print*

| Feld | Beispiel | Hinweis |
|------|----------|---------|
| IP-Adresse | `192.168.114.88` | wird aus der vorhandenen `ipp`-Integration vorgeschlagen, wenn es eine gibt |
| Port | `631` | |
| IPP-Pfad | `/ipp/print` | |
| HTTPS (ipps) | an | viele Drucker antworten auf HTTP mit `426 Upgrade Required` |

Die Einrichtung prüft die Verbindung und liest Modell, Zustand und unterstützte
Papierformate direkt vom Drucker.

## Bedienung

In der Seitenleiste **Drucken** öffnen:

* Datei hineinziehen/auswählen **oder** eine URL eintragen und *Laden*.
* **Papier** (A4 voreingestellt, weitere Formate kommen vom Drucker),
  **Ausrichtung**, **Anpassen** (einpassen oder ausfüllen/beschneiden), **Farbe**.
* Die Vorschau zeigt die gerenderte Seite, Blättern für mehrseitige PDFs.
* *Drucken* schickt eine Seite pro Druckjob an den Drucker.

## Service für Automatisierungen

```yaml
action: ipp_print.print
data:
  url: "https://example.org/rechnung.pdf"
  media: iso_a4_210x297mm
  landscape: false
  mode: fit
  color: true
```

Statt `url` geht auch `file_path` – ein Pfad relativ zum
Home-Assistant-Konfigurationsordner, z. B. `www/rechnung.pdf`.

## Grenzen

* Jede Seite ist ein eigener IPP-Job; bei mehreren Kopien sortiert der Drucker
  daher nicht seitenweise.
* Duplex wird nicht angeboten, wenn der Drucker es nicht meldet (`sides-supported`).
* Uploads liegen nur im Arbeitsspeicher (max. 25 MB, die letzten 8 Dokumente) –
  nach einem Neustart sind sie weg.
* Das Panel ist nur für Administratoren sichtbar; die API-Endpunkte verlangen
  einen angemeldeten Benutzer.
* URL-Laden holt die Datei serverseitig; interne Adressen sind erlaubt, weil die
  Anfrage bereits authentifiziert ist.

## Tests

```bash
pip install pypdfium2 pillow
python tests/test_ipp.py
python tests/test_render.py
```

## Lizenz

MIT
