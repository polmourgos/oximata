# Βήματα για GitHub

## 1. Δημιουργία repository στο GitHub

Στο GitHub φτιάξε νέο repository, π.χ.:

`oximata`

Μπορεί να είναι private, ειδικά αν δεν θέλεις να φαίνεται δημόσια το project.

## 2. Πρώτο ανέβασμα από αυτόν τον φάκελο

Άνοιξε PowerShell μέσα στον φάκελο:

`C:\Users\pol\Downloads\Fleet\oximata`

Μετά τρέξε:

```powershell
git init
git add .
git commit -m "Initial production version"
git branch -M main
git remote add origin https://github.com/USERNAME/oximata.git
git push -u origin main
```

Άλλαξε το `USERNAME` με το δικό σου όνομα χρήστη στο GitHub.

## 3. Κατέβασμα στον υπολογιστή της δουλειάς

Στον υπολογιστή της δουλειάς μπορείς να το κατεβάσεις με:

```powershell
git clone https://github.com/USERNAME/oximata.git
```

ή από το GitHub με `Code` και `Download ZIP`.

Για άνθρωπο που δεν ξέρει από υπολογιστές, προτείνεται να κάνεις εσύ το αρχικό κατέβασμα και build μία φορά. Μετά θα υπάρχει μόνο το εικονίδιο `Οχήματα`.
