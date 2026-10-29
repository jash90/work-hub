"""The Polish interface, keyed by the English it replaces.

English is written in place in the code, so it needs no table. Python keys take `%s`/`%d`,
the ones app.js asks for take `{0}`; both read the same dictionary, which a Polish page
embeds for the browser. Where Polish would have to agree an adjective with a number
("1 MR gotowy" / "5 MR-ów gotowych"), the count goes after a colon instead.
"""

# count(n, one) in Polish: the forms for 1, for 2–4 and for 5+, keyed by the English `one`.
NOUNS = {
    "task": ("task", "taski", "tasków"),
    "MR": ("MR", "MR-y", "MR-ów"),
    "comment": ("uwaga", "uwagi", "uwag"),
    "release": ("wydanie", "wydania", "wydań"),
    "thread": ("wątek", "wątki", "wątków"),
    "unresolved thread": ("nierozwiązany wątek", "nierozwiązane wątki", "nierozwiązanych wątków"),
    "ticket": ("ticket", "tickety", "ticketów"),
    "commit": ("commit", "commity", "commitów"),
    "repository": ("repozytorium", "repozytoria", "repozytoriów"),
    "day": ("dzień", "dni", "dni"),
    "week": ("tydzień", "tygodnie", "tygodni"),
    "item": ("pozycja", "pozycje", "pozycji"),
    "minute": ("minuta", "minuty", "minut"),
    "hour": ("godzina", "godziny", "godzin"),
    "link": ("link", "linki", "linków"),
    "setting": ("ustawienie", "ustawienia", "ustawień"),
}

# "… temu" takes the accusative: 1 minutę temu, 3 minuty temu, 5 minut temu.
AGO_NOUNS = {
    "minute": ("minutę", "minuty", "minut"),
    "hour": ("godzinę", "godziny", "godzin"),
    "day": ("dzień", "dni", "dni"),
}

POLISH = {
    # --- shell, navigation, overview -------------------------------------------------------
    "Overview": "Przegląd",
    "Settings": "Ustawienia",
    "Navigation": "Nawigacja",
    "Open navigation": "Otwórz nawigację",
    "Switch to English": "Przełącz na angielski",
    "Change language": "Zmień język",
    "Theme: automatic": "Motyw: automatyczny",
    "Theme: light": "Motyw: jasny",
    "Theme: dark": "Motyw: ciemny",
    "Change theme": "Zmień motyw",
    "Refresh all": "Odśwież wszystko",
    "Refresh": "Odśwież",
    "Refreshing": "Odświeżam",
    "not yet": "jeszcze nie",
    "The last automatic runs — %s": "Ostatnie automatyczne przebiegi — %s",
    "The tokens and addresses used by the skills the hub runs.":
        "Tokeny i adresy, z których korzystają skille uruchamiane przez hub.",
    "Overtime %s": "Nadgodziny %s",
    "Overtime {0}": "Nadgodziny {0}",

    # --- groups and panels (sources.py) ------------------------------------------------------
    "Morning (10:00)": "Poranek (10:00)",
    "After work (16:00)": "Po pracy (16:00)",
    "On demand": "Na żądanie",
    "My work": "Moja praca",
    "Tasks to start, merge requests ready to merge, my comments on other people's MRs, Jira ↔ GitLab drift.":
        "Taski do zrobienia, MR-y gotowe do mergu, moje uwagi w cudzych MR-ach, rozjazd Jira ↔ GitLab.",
    "Release board": "Tablica release'owa",
    "Every release carrying a task of mine, with the whole team and the state of their MRs.":
        "Każde wydanie z moim taskiem, w pełnym składzie zespołu, ze stanem MR-ów.",
    "Release priority": "Priorytet wydania",
    "My unresolved tasks ordered by release date.":
        "Moje nierozwiązane taski uszeregowane po dacie wydania.",
    "Review queue": "Kolejka review",
    "Other people's open MRs in release order — where to start reviewing.":
        "Cudze otwarte MR-y w kolejności wydań — od czego zacząć review.",
    "Review request": "Prośba o review",
    "My MRs short of approvals — a post ready to paste.":
        "Moje MR-y bez kompletu approve — gotowy post do wklejenia.",
    "Mine in testing": "Moje w testach",
    "What I pushed to Internal testing and what moved on from there.":
        "Co wypchnąłem do Internal testing i co z tego przeszło dalej.",
    "Commits": "Commity",
    "The last two days with commits, ticket by ticket: what changed, in plain words, and whether it is on develop yet.":
        "Dwa ostatnie dni z commitami, ticket po tickecie: co się zmieniło, po ludzku, "
        "i czy jest już na develop.",
    "Tempo": "Tempo",
    "Week by week: what Tempo already holds and what to add from commits.":
        "Tydzień po tygodniu: co już jest w Tempo i co dopisać z commitów.",
    "Acceptance report": "Protokół odbioru",
    "This month's tickets with their hours — the basis of the report.":
        "Tickety bieżącego miesiąca z godzinami — podstawa protokołu.",
    "The full team is unavailable — Jira refused the version query (HTTP 400). Only my own tasks are shown.":
        "Pełny skład zespołu jest niedostępny — Jira odrzuciła zapytanie o wersje (HTTP 400). "
        "Widać tylko moje taski.",

    # --- freshness, banners, errors ----------------------------------------------------------
    "never": "nigdy",
    "just now": "przed chwilą",
    "no data": "brak danych",
    "This panel has not been refreshed yet.": "Ten panel nie był jeszcze odświeżany.",
    "Could not fetch the data.": "Nie udało się pobrać danych.",
    "Data from %s": "Dane z %s",
    "the last attempt (%s) failed: %s": "ostatnia próba (%s) się nie powiodła: %s",
    "Could not render the panel: %s": "Nie udało się wyrenderować panelu: %s",
    "This panel has no data yet — click “Refresh”.": "Ten panel nie ma jeszcze danych — kliknij „Odśwież”.",
    "refresh needed": "wymaga odświeżenia",
    "Nothing.": "Nic.",
    "None.": "Brak.",

    # --- table headers -----------------------------------------------------------------------
    "Ticket": "Ticket",
    "Status": "Status",
    "Release": "Wydanie",
    "Summary": "Opis",
    "MR": "MR",
    "Repo": "Repo",
    "Title": "Tytuł",
    "State": "Stan",
    "Blockers": "Blokady",
    "Where": "Gdzie",
    "Comment": "Uwaga",
    "Waiting": "Czeka",
    "What to do": "Co zrobić",
    "Assignee": "Przypisany",
    "Author": "Autor",
    "Reason": "Powód",
    "Open": "Otwarte",
    "Queued": "W kolejce",
    "Mine": "Moje",
    "Skipped": "Pominięte",
    "When": "Kiedy",
    "Transition": "Przejście",
    "What changed": "Co się zmieniło",
    "Product": "Produkt",
    "Platforms": "Platformy",
    "Day": "Dzień",

    # --- release dates (layout.when) ---------------------------------------------------------
    "%s overdue": "%s po terminie",
    "today": "dziś",
    "tomorrow": "jutro",
    "in %s": "za %s",
    "Overdue": "Po terminie",
    "Upcoming": "Nadchodzące",
    "No date": "Bez daty",
    "No version": "Bez wersji",
    "Other": "Inne",

    # --- my work, priority, testing ----------------------------------------------------------
    "To do": "Do zrobienia",
    "Nothing waiting to be started.": "Nic nie czeka na rozpoczęcie.",
    "Ready to merge": "Gotowe do mergu",
    "None of my MRs has a full set of approvals yet.": "Żaden mój MR nie ma jeszcze kompletu approve.",
    "My other MRs": "Pozostałe moje MR-y",
    "No other open MRs.": "Brak innych otwartych MR-ów.",
    "Waiting on me": "Czekają na mnie",
    "Waiting on the author": "Czekają na autora",
    "My comments on other people's MRs": "Moje uwagi w cudzych MR-ach",
    "%d across %s": "%d · %s",
    "Jira ↔ GitLab drift": "Rozjazd Jira ↔ GitLab",
    "%s to do": "do zrobienia: %s",
    "%s ready to merge": "gotowe do mergu: %s",
    "%s on me": "u mnie: %s",
    "No unresolved tasks.": "Brak nierozwiązanych tasków.",
    "%d overdue": "po terminie: %d",
    "Still in “%s”": "Wciąż w „%s”",
    "Nothing waiting.": "Nic nie czeka.",
    "Moved on": "Poszły dalej",
    "%s in testing": "w testach: %s",
    "%d still there": "wciąż tam: %d",
    "%d/%d approve": "%d/%d approve",
    "%d approve": "%d approve",
    "draft": "draft",
    "waiting on my reply": "czeka na moją odpowiedź",
    "no response": "bez odzewu",
    "fresh, no reply yet": "świeże, jeszcze bez odpowiedzi",
    "fixed": "poprawione",
    "answered": "z odpowiedzią",
    "closed by me": "zamknięte przeze mnie",

    # --- review queue, review request --------------------------------------------------------
    "select MR !%s": "zaznacz MR !%s",
    "all": "wszystkie",
    "new": "nowy",
    "re-review": "re-review",
    "nothing selected": "nic nie zaznaczono",
    "Copy links": "Kopiuj linki",
    "The queue is empty — nothing to review.": "Kolejka jest pusta — nie ma czego przeglądać.",
    "Queue": "Kolejka",
    "Repositories scanned": "Przeskanowane repozytoria",
    "%s queued": "w kolejce: %s",
    "%d new": "nowe: %d",
    "The post": "Post",
    "Copy the post": "Kopiuj post",
    "My MRs short of approvals": "Moje MR-y bez kompletu approve",
    "Every MR of mine has a full set of approvals.": "Każdy mój MR ma komplet approve.",
    "%s waiting": "czeka: %s",
    "%d with no approval": "bez approve: %d",

    # --- release board -----------------------------------------------------------------------
    "every task closed": "wszystkie taski zamknięte",
    "my tasks closed · %s still open for the team": "moje taski zamknięte · zespołowi zostało: %s",
    "fold this release": "zwiń to wydanie",
    "%d of %d mine": "moje: %d z %d",
    "%s folded as finished": "zwinięte jako zakończone: %s",
    "Only my tasks": "Tylko moje taski",
    "Fold all": "Zwiń wszystkie",
    "Unfold all": "Rozwiń wszystkie",
    "Status changes": "Zmiany statusów",
    "No tasks in any release.": "Brak tasków w żadnym wydaniu.",

    # --- commits, acceptance report ----------------------------------------------------------
    "on develop": "na develop",
    "merged": "zmergowane",
    "on a release branch only": "tylko na branchu release",
    "draft MR": "MR w drafcie",
    "ready for review": "gotowe do review",
    "follow-up · draft MR": "dociągnięcie · MR w drafcie",
    "follow-up · ready for review": "dociągnięcie · gotowe do review",
    "MR closed": "MR zamknięty",
    "pushed, no MR": "wypchnięte, bez MR",
    "not pushed": "niewypchnięte",
    "This panel's data predates the current report format — click “Refresh”.":
        "Dane tego panelu pochodzą sprzed obecnego formatu raportu — kliknij „Odśwież”.",
    "No commits in the last 30 days.": "Brak commitów w ostatnich 30 dniach.",
    "%d on develop": "na develop: %d",
    "%d waiting": "czeka: %d",
    "Items for %s": "Pozycje za %s",
    "No items.": "Brak pozycji.",
    "Copy the brief for Claude": "Kopiuj brief dla Claude'a",

    # --- tempo -------------------------------------------------------------------------------
    "15 minutes less": "15 minut mniej",
    "15 minutes more": "15 minut więcej",
    "hours for %s": "godziny dla %s",
    "remove entry": "usuń wpis",
    "Clear the day": "Wyczyść dzień",
    "Undo": "Cofnij",
    "Allow a day shorter than 8 h to be written": "Pozwól zapisać dzień krótszy niż 8 h",
    "short day": "krótszy dzień",
    "Allow a day longer than 8 h to be written": "Pozwól zapisać dzień dłuższy niż 8 h",
    "overtime": "nadgodziny",
    "Save changes": "Zapisz zmiany",
    "Log the day": "Zaloguj dzień",
    "ticket key": "klucz ticketu",
    "hours for the new entry": "godziny dla nowego wpisu",
    "Add entry": "Dodaj wpis",
    "%s h — a day off, edit it in Tempo": "%s h — dzień wolny, edytuj go w Tempo",
    "day off": "dzień wolny",
    "Nothing is written to Tempo without a click and a confirmation. The 16:00 run only computes proposals. Hours move in steps of 15 minutes; a day under 8 h needs “short day”, one over it needs “overtime”.":
        "Nic nie trafia do Tempo bez kliknięcia i potwierdzenia. Przebieg o 16:00 tylko liczy "
        "propozycje. Godziny zmieniają się co 15 minut; dzień poniżej 8 h wymaga „krótszy dzień”, "
        "powyżej — „nadgodziny”.",
    "previous week": "poprzedni tydzień",
    "next week": "następny tydzień",
    "Week by week": "Tydzień po tygodniu",
    "Proposals to log": "Propozycje do zalogowania",
    "No day has a complete proposal.": "Żaden dzień nie ma pełnej propozycji.",
    "Days skipped": "Pominięte dni",
    "Gaps in Tempo": "Luki w Tempo",
    "%s to log": "do zalogowania: %s",
    "%s h in Tempo": "%s h w Tempo",

    # --- settings ----------------------------------------------------------------------------
    "Tokens": "Tokeny",
    "Jira and GitLab": "Jira i GitLab",
    "Hub": "Hub",
    "Jira address": "Adres Jiry",
    "Project keys": "Klucze projektów",
    "Tempo username": "Nazwa użytkownika w Tempo",
    "Port": "Port",
    "Morning run": "Przebieg poranny",
    "Afternoon run": "Przebieg popołudniowy",
    "first.last": "imie.nazwisko",
    "Used by most panels. Worklog writing reads it only from the file under ~/.claude/.secrets — tick the mirror below or Tempo will not see it.":
        "Używany przez większość paneli. Zapis worklogów czyta go wyłącznie z pliku "
        "w ~/.claude/.secrets — zaznacz synchronizację poniżej, inaczej Tempo go nie zobaczy.",
    "The review queue, the review request and the shared merge-request index.":
        "Kolejka review, prośba o review i wspólny indeks merge requestów.",
    "No panel uses it yet; kept for skills that reach into Confluence. Jira and Confluence need separate tokens.":
        "Żaden panel jeszcze go nie używa; przechowywany dla skilli sięgających po Confluence. "
        "Jira i Confluence wymagają osobnych tokenów.",
    "Builds the “…/browse/KEY” links in this interface. It does not change which Jira the skills query — that host lives in redge_work, outside this repository.":
        "Buduje linki „…/browse/KEY” w interfejsie. Nie zmienia tego, do której Jiry pytają "
        "skille — ten adres jest zaszyty w redge_work poza tym repozytorium.",
    "Comma-separated. The first one is the placeholder in the Tempo day editor.":
        "Po przecinku. Pierwszy z nich jest podpowiedzią w edytorze dnia Tempo.",
    "Whose worklogs. Tempo has no token of its own — it uses the Jira PAT.":
        "Właściciel worklogów. Tempo nie ma osobnego tokenu — korzysta z PAT-a Jiry.",
    "The server listens on the loopback interface only.": "Serwer słucha wyłącznie na pętli zwrotnej.",
    "Time as HH:MM.": "Godzina HH:MM.",
    "not set": "nie ustawiono",
    "from %s": "źródło: %s",
    "the environment": "środowisko",
    "the Keychain outranks .env": "Keychain ma pierwszeństwo przed .env",
    "unchanged": "bez zmian",
    "paste a token": "wklej token",
    "Remove the stored value from .env": "Usuń zapisaną wartość z .env",
    "clear": "wyczyść",
    "Needs a restart of the hub.": "Wymaga restartu huba.",
    "Settings go into the .env beside the repository — never into git. A saved token takes effect on the next panel refresh, and no token is ever shown back here.":
        "Ustawienia trafiają do .env obok repozytorium — nigdy do gita. Zapisany token działa "
        "od następnego odświeżenia panelu, a żaden token nie jest tu nigdy pokazywany.",
    "Copy the tokens into files under ~/.claude/.secrets": "Skopiuj tokeny do plików w ~/.claude/.secrets",
    "also write to ~/.claude/.secrets": "zapisz też do ~/.claude/.secrets",
    "Required for worklog writing — tempo-fill reads the token only from a file.":
        "Wymagane do zapisu worklogów — tempo-fill czyta token wyłącznie z pliku.",
    "Save": "Zapisz",

    # --- app.js and day-rules.js -------------------------------------------------------------
    "{0}: showing older data, the refresh failed": "{0}: pokazuję starsze dane, odświeżenie się nie powiodło",
    "The hub restarted since this page loaded — reloading…": "Hub zrestartował się od załadowania strony — przeładowuję…",
    "Refreshing every panel…": "Odświeżam wszystkie panele…",
    "Refreshing…": "Odświeżam…",
    "Copied to the clipboard": "Skopiowano do schowka",
    "The browser refused access to the clipboard": "Przeglądarka odmówiła dostępu do schowka",
    "Writes the worklogs to Tempo": "Zapisuje worklogi do Tempo",
    "added by hand": "dodane ręcznie",
    "A ticket key looks like {0}-1234": "Klucz ticketu wygląda jak {0}-1234",
    "Refused: {0}": "Odrzucone: {0}",
    "Write worklogs to Tempo for {0}{1}?\n\n{2}\n\n{3} h in total. This is a real POST to Jira.":
        "Zapisać worklogi do Tempo za {0}{1}?\n\n{2}\n\nRazem {3} h. To prawdziwy POST do Jiry.",
    "Saved {0} — {1} h": "Zapisano {0} — {1} h",
    "Clear {0} in Tempo? This deletes every worklog on that day.":
        "Wyczyścić {0} w Tempo? To usunie wszystkie worklogi z tego dnia.",
    "Cleared {0}": "Wyczyszczono {0}",
    "Undo the worklogs for {0}? They will be deleted from Jira.":
        "Cofnąć worklogi za {0}? Zostaną usunięte z Jiry.",
    "Undone {0}": "Cofnięto {0}",
    "{0} of {1}": "{0} z {1}",
    "Copied {0}": "Skopiowano: {0}",
    "Not saved: {0}": "Nie zapisano: {0}",
    "Saved {0}": "Zapisano: {0}",
    "hours must be a number, e.g. 1.75": "godziny muszą być liczbą, np. 1.75",
    "add at least one entry": "dodaj co najmniej jeden wpis",
    "hours must be a multiple of 15 minutes": "godziny muszą być wielokrotnością 15 minut",
    "{0} h short of {1} h": "brakuje {0} h do {1} h",
    "{0} h over {1} h — tick \"overtime\"": "{0} h ponad {1} h — zaznacz „nadgodziny”",
    "ready to write": "gotowe do zapisu",
    "short day: {0} h": "krótszy dzień: {0} h",
    "overtime: {0} h": "nadgodziny: {0} h",
}
