# Οδηγίες εγκατάστασης σε MX Linux

Αυτός ο οδηγός είναι για υπολογιστή με Linux, συγκεκριμένα MX Linux.

Στο Linux δεν τρέχει το Windows αρχείο `.exe`. Η εφαρμογή τρέχει με Python.

## 1. Κατέβασμα από GitHub

Άνοιξε το repository:

`https://github.com/polmourgos/oximata`

Πάτα:

`Code` -> `Download ZIP`

Μετά κάνε αποσυμπίεση το ZIP σε έναν σταθερό φάκελο, για παράδειγμα:

`/home/username/Oximata`

Όπου `username` είναι το όνομα χρήστη του υπολογιστή.

## 2. Εγκατάσταση βασικών πακέτων

Άνοιξε Terminal και τρέξε:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-tk
```

Το `python3-tk` είναι απαραίτητο γιατί η εφαρμογή έχει γραφικό περιβάλλον Tkinter.

## 3. Εγκατάσταση βιβλιοθηκών της εφαρμογής

Μπες στον φάκελο της εφαρμογής. Παράδειγμα:

```bash
cd /home/username/Oximata
```

Αν ο φάκελος που αποσυμπιέστηκε λέγεται `oximata-main`, τότε μπες εκεί:

```bash
cd /home/username/oximata-main
```

Μετά τρέξε:

```bash
pip3 install -r requirements.txt
```

Αν το MX Linux εμφανίσει μήνυμα ότι δεν επιτρέπει εγκατάσταση με `pip3` στο σύστημα, χρησιμοποίησε virtual environment:

```bash
sudo apt install python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 4. Εκκίνηση της εφαρμογής

Από τον φάκελο της εφαρμογής τρέξε:

```bash
python3 oximata.py
```

Αν χρησιμοποιείς virtual environment, πρώτα ενεργοποίησέ το:

```bash
source .venv/bin/activate
python3 oximata.py
```

## 5. Πού αποθηκεύονται τα δεδομένα

Η εφαρμογή θα δημιουργήσει αυτόματα φάκελο:

`data`

Μέσα εκεί θα αποθηκεύονται:

- η βάση δεδομένων `oximata.db`
- οι οδηγοί
- τα οχήματα
- οι κινήσεις
- τα PDF εντολών κίνησης
- logs και backups

Το πιο σημαντικό αρχείο είναι:

`data/oximata.db`

Για backup, κράτα αντίγραφο ολόκληρου του φακέλου:

`data`

## 6. Δημιουργία εικονιδίου στην επιφάνεια εργασίας

Αν η εφαρμογή ανοίγει σωστά από το Terminal, μπορεί να δημιουργηθεί εικονίδιο.

Δημιούργησε αρχείο στην επιφάνεια εργασίας με όνομα:

`Oximata.desktop`

και περιεχόμενο σαν το παρακάτω. Άλλαξε το `username` και τη διαδρομή του φακέλου αν χρειάζεται:

```ini
[Desktop Entry]
Type=Application
Name=Οχήματα
Comment=Διαχείριση στόλου οχημάτων
Exec=python3 /home/username/Oximata/oximata.py
Path=/home/username/Oximata
Terminal=false
Categories=Office;
```

Μετά κάνε το αρχείο εκτελέσιμο:

```bash
chmod +x /home/username/Desktop/Oximata.desktop
```

Σε ορισμένες εκδόσεις Linux μπορεί να χρειαστεί δεξί κλικ στο εικονίδιο και επιλογή:

`Allow Launching`

ή:

`Trust this launcher`

## 7. Αν χρησιμοποιείται virtual environment στο εικονίδιο

Αν εγκατέστησες τις βιβλιοθήκες σε `.venv`, το `Exec` πρέπει να δείχνει στην Python του virtual environment:

```ini
Exec=/home/username/Oximata/.venv/bin/python /home/username/Oximata/oximata.py
```

Το πλήρες αρχείο τότε είναι:

```ini
[Desktop Entry]
Type=Application
Name=Οχήματα
Comment=Διαχείριση στόλου οχημάτων
Exec=/home/username/Oximata/.venv/bin/python /home/username/Oximata/oximata.py
Path=/home/username/Oximata
Terminal=false
Categories=Office;
```

## 8. Τι να κάνει ο συνάδελφος καθημερινά

Μετά την αρχική εγκατάσταση, ο συνάδελφος δεν χρειάζεται να ανοίγει Terminal.

Θα ανοίγει την εφαρμογή από το εικονίδιο `Οχήματα`.

## 9. Μεταφορά ή επανεγκατάσταση

Αν μεταφερθεί η εφαρμογή σε άλλον υπολογιστή Linux:

1. Κατεβάζεις ξανά το repo από GitHub.
2. Αντιγράφεις τον παλιό φάκελο `data` μέσα στον νέο φάκελο της εφαρμογής.
3. Τρέχεις την εφαρμογή.

Έτσι μεταφέρονται μαζί οχήματα, οδηγοί και ιστορικό κινήσεων.

## 10. Γρήγορη περίληψη εντολών

Χωρίς virtual environment:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-tk
cd /home/username/Oximata
pip3 install -r requirements.txt
python3 oximata.py
```

Με virtual environment:

```bash
sudo apt update
sudo apt install python3 python3-pip python3-tk python3-venv
cd /home/username/Oximata
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 oximata.py
```
