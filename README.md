# Oximata

Νέο project βασισμένο στο `fleet_manager_improved.py` από το GitHub repo `polmourgos/fleet_manager`.

## Σημείο αναφοράς

Το αρχικό repo παραμένει ανέγγιχτο στον φάκελο:

`C:\Users\pol\Downloads\Fleet\github_fleet_manager`

Το αρχικό κύριο αρχείο αναφοράς είναι:

`C:\Users\pol\Downloads\Fleet\github_fleet_manager\fleet_manager_improved.py`

## Νέο project

Το νέο κύριο αρχείο είναι:

`C:\Users\pol\Downloads\Fleet\oximata\oximata.py`

Οι ελάχιστες αρχικές αλλαγές σε σχέση με το αρχικό project είναι:

- Το κύριο αρχείο μετονομάστηκε σε `oximata.py`.
- Η βάση δεδομένων ονομάζεται `oximata.db`.
- Το log αρχείο ονομάζεται `oximata.log`.
- Τα backups προτείνονται ως `oximata_backup_*.db`.
- Ο τίτλος της εφαρμογής άλλαξε σε `Οχήματα - Διαχείριση Στόλου`.

## Δεδομένα εφαρμογής

Τα καθημερινά δεδομένα αποθηκεύονται στον φάκελο:

`C:\Users\pol\Downloads\Fleet\oximata\data`

Εκεί μπαίνουν η βάση `oximata.db`, τα logs, οι φωτογραφίες, τα backups και τα έγγραφα κινήσεων. Ο φάκελος `data` είναι στο `.gitignore`, ώστε όταν το project ανέβει στο Git να ανέβει ο κώδικας χωρίς τα τοπικά δεδομένα του υπολογιστή.

## Εντολές κίνησης

Κάθε νέα κίνηση παίρνει αύξοντα αριθμό. Η εντολή κίνησης δημιουργείται ως PDF στον φάκελο:

`data\kiniseis`

Η εφαρμογή μπορεί να επανεκτυπώσει εντολή κίνησης από το κουμπί `Επανεκτύπωση`, δίνοντας τον αριθμό της κίνησης.

## Επόμενη φάση

Οι επόμενες βελτιώσεις θα γίνουν μόνο μέσα σε αυτόν τον φάκελο, ώστε το αρχικό `fleet_manager_improved.py` να μείνει καθαρό σημείο επιστροφής.
