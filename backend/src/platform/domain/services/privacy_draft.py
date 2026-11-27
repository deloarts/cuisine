"""
The privacy statement's default draft, written from what this instance
actually does: where files are stored, how long backups and logs keep
data, whether AI agents, webhooks, the USDA lookup and mail are on, and the
deletion rules. The administrator edits it before publishing; the parts in
square brackets are theirs to fill in.

`{{ privacy_mode }}` marks where the privacy mode section goes. The rendered
statement always contains that section, generated from the mode the
version was published under and from whether public recipes were allowed,
so it can never be left out or go stale.
"""

from dataclasses import dataclass

from src.platform.domain.entities.legal import PrivacyMode
from src.platform.domain.entities.legal import PrivacyModeSnapshot

PRIVACY_MODE_MARKER = "{{ privacy_mode }}"


@dataclass(frozen=True)
class PrivacyFacts:
    instance_name: str
    storage_provider: str
    backup_keep_days: int
    backup_hour_utc: int
    security_log_days: int
    agent_calls_days: int
    webhook_deliveries_days: int
    recipe_revisions_days: int
    agents_enabled: bool
    agent_token_max_days: int
    webhooks_enabled: bool
    usda_enabled: bool
    mail_enabled: bool
    households_enabled: bool
    dinner_guests_enabled: bool
    public_recipes_allowed: bool = False
    peering_enabled: bool = False


_VISIBILITY = {
    "en-GB": {
        "private": "private (only the author)",
        "household": "visible to the author's household",
        "shared": "shared with chosen people and groups",
        "instance": "visible to every signed-in member",
        "peers": "visible to every signed-in member and every paired instance",
        "public": "public, readable by anyone without signing in",
    },
    "de-AT": {
        "private": "privat (nur die Person, die es geschrieben hat)",
        "household": "für den eigenen Haushalt sichtbar",
        "shared": "mit ausgewählten Personen und Gruppen geteilt",
        "instance": "für alle angemeldeten Mitglieder sichtbar",
        "peers": "für alle angemeldeten Mitglieder und alle verbundenen Instanzen sichtbar",
        "public": "öffentlich, für alle ohne Anmeldung lesbar",
    },
}


def _days(n: int, locale: str) -> str:
    if locale == "de-AT":
        return "unbegrenzt" if n == 0 else f"{n} Tage"
    return "without a time limit" if n == 0 else f"{n} days"


def _public_recipes_text(allowed: bool, locale: str) -> str:
    """Whether recipes can be public, and what a public recipe shows."""
    if locale == "de-AT":
        if not allowed:
            return (
                "### Öffentliche Rezepte\n\n"
                "Öffentliche Rezepte sind auf dieser Instanz nicht erlaubt. Ohne Anmeldung ist "
                "kein Rezept lesbar."
            )
        return (
            "### Öffentliche Rezepte\n\n"
            "Rezepte können öffentlich sein. Ein öffentliches Rezept kann jede Person im "
            "Internet ohne Anmeldung lesen, aber nicht bearbeiten. Dein Name wird dabei nicht "
            "angezeigt, außer du schaltest das in deinem Konto ein."
        )
    if not allowed:
        return (
            "### Public recipes\n\n"
            "Public recipes are not allowed on this instance. No recipe can be read without "
            "signing in."
        )
    return (
        "### Public recipes\n\n"
        "Recipes can be public. Anyone on the internet can read a public recipe without signing "
        "in, but nobody can change it there. Your name is not shown on it unless you switch "
        "that on in your account."
    )


def privacy_mode_text(snapshot: PrivacyModeSnapshot, locale: str) -> str:
    """The privacy mode in plain words, with the rule that the mode is the
    administrator's decision, and whether recipes can be public."""
    public = _public_recipes_text(snapshot.allow_public_recipes, locale)
    default = _VISIBILITY.get(locale, _VISIBILITY["en-GB"]).get(
        snapshot.default_visibility, snapshot.default_visibility
    )
    if locale == "de-AT":
        mode = {
            PrivacyMode.INSTANCE: (
                "**Gemeinsam**: Jedes Rezept ist für alle angemeldeten Mitglieder sichtbar, "
                "und das lässt sich pro Rezept nicht ändern."
            ),
            PrivacyMode.PUBLIC: (
                "**Öffentlich**: Jedes Rezept ist öffentlich, also für alle ohne Anmeldung "
                "lesbar, und das lässt sich pro Rezept nicht ändern."
            ),
            PrivacyMode.PEERS: (
                "**Verbunden**: Jedes Rezept ist für alle angemeldeten Mitglieder und alle "
                "verbundenen Instanzen sichtbar, und das lässt sich pro Rezept nicht ändern."
            ),
            PrivacyMode.PRIVATE: (
                f"**Privat**: Neue Rezepte sind {default}, und das lässt sich pro Rezept nicht "
                "ändern."
            ),
            PrivacyMode.USER_CHOICE: (
                "**Deine Wahl**: Du bestimmst bei jedem Rezept, wer es sieht. Neue Rezepte "
                f"starten als {default}, solange du nichts anderes einstellst."
            ),
        }[snapshot.mode]
        return (
            "## Sichtbarkeit der Rezepte\n\n"
            f"Diese Instanz läuft im Modus {mode}\n\n"
            "Den Modus legt die Administration fest. Wer ihn nicht akzeptiert, kann Cuisine "
            "nicht nutzen. Ändert sich der Modus, wirst du gebeten, diese Erklärung neu zu "
            f"bestätigen.\n\n{public}"
        )
    mode = {
        PrivacyMode.INSTANCE: (
            "**instance**: every recipe is visible to every signed-in member, and this cannot be "
            "changed per recipe."
        ),
        PrivacyMode.PUBLIC: (
            "**public**: every recipe is public, readable by anyone without signing in, and this "
            "cannot be changed per recipe."
        ),
        PrivacyMode.PEERS: (
            "**paired instances**: every recipe is visible to every signed-in member and every "
            "paired instance, and this cannot be changed per recipe."
        ),
        PrivacyMode.PRIVATE: (
            f"**private**: new recipes are {default}, and this cannot be changed per recipe."
        ),
        PrivacyMode.USER_CHOICE: (
            "**your choice**: you decide for each recipe who sees it. New recipes start as "
            f"{default} unless you choose otherwise."
        ),
    }[snapshot.mode]
    return (
        "## Who sees your recipes\n\n"
        f"This instance runs in the mode {mode}\n\n"
        "The mode is the administrator's decision. Whoever does not accept it cannot use "
        "Cuisine. When the mode changes, you are asked to acknowledge this statement again."
        f"\n\n{public}"
    )


def render_privacy_statement(text: str, snapshot: PrivacyModeSnapshot | None, locale: str) -> str:
    """The statement as users read it: the marker replaced by the privacy
    mode section, or the section appended when the text has no marker."""
    if snapshot is None:
        return text.replace(PRIVACY_MODE_MARKER, "").strip()
    section = privacy_mode_text(snapshot, locale)
    if PRIVACY_MODE_MARKER in text:
        return text.replace(PRIVACY_MODE_MARKER, section)
    return f"{text.rstrip()}\n\n{section}\n"


def _storage(provider: str, locale: str) -> str:
    if locale == "de-AT":
        return {
            "postgres": "in der Datenbank der Instanz, gemeinsam mit allen anderen Daten",
            "local": "als Dateien auf einem Datenträger des Servers, getrennt von der Datenbank",
            "seaweedfs": "in einem Objektspeicher (S3-Schnittstelle), getrennt von der Datenbank",
        }.get(provider, provider)
    return {
        "postgres": "in the instance's database, together with all other data",
        "local": "as files on a disk of the server, apart from the database",
        "seaweedfs": "in an object store (S3 API), apart from the database",
    }.get(provider, provider)


def privacy_draft(facts: PrivacyFacts, locale: str) -> str:
    return _german(facts) if locale == "de-AT" else _english(facts)


def _english(f: PrivacyFacts) -> str:
    def d(n: int) -> str:
        return _days(n, "en-GB")

    parts = [
        f"# Privacy statement of {f.instance_name}",
        "## Who is responsible\n\n[Name and contact of the person who runs this instance.]",
        "## What is stored\n\n"
        "Your account (full name, e-mail address, password hash, language and "
        "theme), your sign-in sessions, passkeys and trusted devices, and what you write: "
        "recipes, ratings, favourites, private notes, what you cooked, meal plans and shopping "
        "lists. Only a session cookie is set; there is no tracking.",
        PRIVACY_MODE_MARKER,
        "## Allergies, intolerances and diets\n\n"
        "These are health data. You enter them only with your separate consent, which you can "
        "withdraw at any time in your account; withdrawing deletes them. Nobody else ever sees "
        "them, administrators included. The app works fully without them.",
    ]
    if f.dinner_guests_enabled:
        parts.append(
            "## Dinner guests\n\nIf you opt in, a host planning a meal learns that a recipe does "
            "not suit their guests, never which guest or why. The opt-in is off by default."
        )
    if f.households_enabled:
        parts.append(
            "## Households\n\nMembers of a household share a meal plan and a shopping list. "
            "You join only by accepting an invitation and can leave at any time."
        )
    parts.append(
        "## Photos and documents\n\nUploaded files are stored "
        f"{_storage(f.storage_provider, 'en-GB')}. "
        "Images are re-encoded, which removes their metadata such as location data."
    )
    parts.append(
        "## Backups\n\n"
        f"The database is backed up every night at {f.backup_hour_utc}:00 UTC. Backups are kept "
        f"for {d(f.backup_keep_days)}; deleted data remains in the existing backups until they "
        f"are rotated out, so it is gone from every backup {d(f.backup_keep_days + 1)} after its "
        "deletion at the latest."
        + (
            ""
            if f.storage_provider == "postgres"
            else " Uploaded files are backed up separately by the administrator."
        )
    )
    parts.append(
        "## Logs\n\n"
        f"The security log (sign-ins and account changes) is kept for {d(f.security_log_days)}, "
        f"recipe revisions for {d(f.recipe_revisions_days)}"
        + (f", the agent call log for {d(f.agent_calls_days)}" if f.agents_enabled else "")
        + (
            f" and the webhook delivery log for {d(f.webhook_deliveries_days)}"
            if f.webhooks_enabled
            else ""
        )
        + "."
    )
    if f.agents_enabled:
        parts.append(
            "## AI agents\n\n"
            "You can connect an AI agent of your choice, only with your separate consent. The "
            "agent acts as you and reads what you can read; whatever it reads goes to the AI "
            "provider you use, under that provider's terms. Agent tokens last at most "
            f"{d(f.agent_token_max_days)}. Allergies and intolerances are never given to an agent. "
            "Withdrawing the consent revokes your agent tokens."
        )
    if f.usda_enabled:
        parts.append(
            "## Nutrition lookup\n\nWhen someone looks up an ingredient's nutrition, the search "
            "term is sent to USDA FoodData Central. No personal data is sent."
        )
    if f.webhooks_enabled:
        parts.append(
            "## Notifications to other systems\n\nThe administrator can send events to other "
            "systems by webhook. An event about a deleted account carries nothing about the "
            "person, and events naming a person are deleted with their account."
        )
    if f.peering_enabled:
        parts.append(
            "## Paired instances\n\nThis instance can be paired with other Cuisine instances "
            "by their administrators. Every paired instance the administrator lets you share "
            "with receives the recipes you explicitly share with it, every recipe you set to "
            '"Paired instances", and every public recipe'
            + ("" if f.public_recipes_allowed else " (none while public recipes are not allowed)")
            + ". It receives the recipe's content, its images and its variations that are as "
            "visible as the recipe, never a private variation. Your display name goes with it "
            'only while "Show my name on paired cookbooks" is on in your account; your e-mail '
            "address never leaves this instance, and nothing personal (ratings, "
            "notes, favourites, cooking history, meal plan, shopping lists, health data) is ever "
            "sent. Recipes paired instances share with this one are shown here, read only, "
            "after an administrator accepted them (at once from an instance whose recipes the "
            "administrator takes in without asking), and disappear when their source withdraws "
            "them or the pairing ends; what you do with them here (favourites, notes, ratings, "
            "cooking history) stays here."
        )
    if f.mail_enabled:
        parts.append(
            "## Mail\n\nThe instance sends mail through the administrator's mail server, for "
            "example operational alerts to the administrators."
        )
    parts.append(
        "## Your data and deleting it\n\n"
        "You can download your data in your account. You can delete your account yourself: "
        "recipes visible to every member"
        + (" or public" if f.public_recipes_allowed else "")
        + " stay online without an owner (as a former member) unless "
        "the instance lets you delete them; household recipes pass to a remaining household "
        "member or are deleted; private and shared recipes and all drafts are deleted; "
        "ingredients you added stay in the catalogue without an owner. Your profile, "
        "credentials, health data, consents, ratings, notes, favourites, cooking history, "
        "meal plan and memberships are deleted, and so are your security log entries except "
        "one anonymous entry that an account was deleted. An administrator deleting an account "
        "follows the same rules. Deleted data remains in backups as described above."
    )
    parts.append("## Your rights\n\n[How to contact the person responsible, and the authority.]")
    return "\n\n".join(parts) + "\n"


def _german(f: PrivacyFacts) -> str:
    def d(n: int) -> str:
        return _days(n, "de-AT")

    parts = [
        f"# Datenschutzerklärung von {f.instance_name}",
        "## Wer verantwortlich ist\n\n[Name und Kontakt der Person, die diese Instanz betreibt.]",
        "## Was gespeichert wird\n\n"
        "Dein Konto (Name, E-Mail-Adresse, Passwort-Hash, Sprache und Design), "
        "deine Anmeldesitzungen, Passkeys und vertrauten Geräte, und was du schreibst: Rezepte, "
        "Bewertungen, Favoriten, private Notizen, was du gekocht hast, Wochenpläne und "
        "Einkaufslisten. Gesetzt wird nur ein Sitzungs-Cookie; es gibt kein Tracking.",
        PRIVACY_MODE_MARKER,
        "## Allergien, Unverträglichkeiten und Ernährungsweisen\n\n"
        "Das sind Gesundheitsdaten. Du trägst sie nur mit deiner eigenen Einwilligung ein, die "
        "du in deinem Konto jederzeit widerrufen kannst; der Widerruf löscht sie. Niemand sonst "
        "sieht sie, auch die Administration nicht. Die App funktioniert ohne sie vollständig.",
    ]
    if f.dinner_guests_enabled:
        parts.append(
            "## Gäste\n\nWenn du zustimmst, erfährt jemand, der ein Essen plant, nur, dass ein "
            "Rezept nicht zu den Gästen passt, nie wem oder warum. Die Zustimmung ist "
            "anfangs aus."
        )
    if f.households_enabled:
        parts.append(
            "## Haushalte\n\nMitglieder eines Haushalts teilen einen Wochenplan und eine "
            "Einkaufsliste. Du trittst nur bei, wenn du eine Einladung annimmst, und kannst "
            "jederzeit austreten."
        )
    parts.append(
        "## Fotos und Dokumente\n\nHochgeladene Dateien liegen "
        f"{_storage(f.storage_provider, 'de-AT')}. "
        "Bilder werden neu codiert, dabei gehen Metadaten wie Ortsangaben verloren."
    )
    parts.append(
        "## Sicherungen\n\n"
        f"Die Datenbank wird jede Nacht um {f.backup_hour_utc}:00 UTC gesichert. Sicherungen "
        f"werden {d(f.backup_keep_days)} aufbewahrt; gelöschte Daten bleiben in den bestehenden "
        "Sicherungen, bis diese aussortiert werden, und sind spätestens "
        f"{d(f.backup_keep_days + 1)} nach dem Löschen aus allen Sicherungen verschwunden."
        + (
            ""
            if f.storage_provider == "postgres"
            else " Hochgeladene Dateien sichert die Administration getrennt."
        )
    )
    parts.append(
        "## Protokolle\n\n"
        f"Das Sicherheitsprotokoll (Anmeldungen und Kontoänderungen) wird {d(f.security_log_days)} "
        f"aufbewahrt, Rezeptversionen {d(f.recipe_revisions_days)}"
        + (f", das Protokoll der KI-Agenten {d(f.agent_calls_days)}" if f.agents_enabled else "")
        + (
            f" und das Webhook-Protokoll {d(f.webhook_deliveries_days)}"
            if f.webhooks_enabled
            else ""
        )
        + "."
    )
    if f.agents_enabled:
        parts.append(
            "## KI-Agenten\n\n"
            "Du kannst einen KI-Agenten deiner Wahl verbinden, nur mit deiner eigenen "
            "Einwilligung. Der Agent handelt als du und liest, was du lesen darfst; was er liest, "
            "geht an den KI-Anbieter, den du nutzt, zu dessen Bedingungen. Agenten-Tokens gelten "
            f"höchstens {d(f.agent_token_max_days)}. Allergien und Unverträglichkeiten bekommt ein "
            "Agent nie. Der Widerruf der Einwilligung entzieht deine Agenten-Tokens."
        )
    if f.usda_enabled:
        parts.append(
            "## Nährwertsuche\n\nWer die Nährwerte einer Zutat nachschlägt, schickt den "
            "Suchbegriff an USDA FoodData Central. Persönliche Daten werden nicht gesendet."
        )
    if f.webhooks_enabled:
        parts.append(
            "## Meldungen an andere Systeme\n\nDie Administration kann Ereignisse per Webhook an "
            "andere Systeme senden. Ein Ereignis über ein gelöschtes Konto enthält nichts über "
            "die Person, und Ereignisse, die eine Person nennen, werden mit ihrem Konto gelöscht."
        )
    if f.peering_enabled:
        parts.append(
            "## Verbundene Instanzen\n\nDie Administration kann diese Instanz mit anderen "
            "Cuisine-Instanzen verbinden. Jede verbundene Instanz, mit der die Administration "
            "das Teilen erlaubt, bekommt die Rezepte, die du ausdrücklich mit ihr teilst, jedes "
            'Rezept, das du auf "Verbundene Instanzen" stellst, und jedes öffentliche Rezept'
            + (
                ""
                if f.public_recipes_allowed
                else " (keine, solange öffentliche Rezepte nicht erlaubt sind)"
            )
            + ". Sie bekommt den Inhalt des Rezepts, seine Bilder und seine Varianten, die so "
            "sichtbar sind wie das Rezept, nie eine private Variante. Dein Anzeigename geht nur "
            'mit, solange "Meinen Namen in verbundenen Kochbüchern zeigen" in deinem Konto '
            "eingeschaltet ist; deine E-Mail-Adresse verlässt diese Instanz nie, und "
            "nichts Persönliches (Bewertungen, Notizen, Favoriten, Kochverlauf, Wochenplan, "
            "Einkaufslisten, Gesundheitsdaten) wird je gesendet. Rezepte, die verbundene "
            "Instanzen mit dieser teilen, erscheinen hier nur lesbar, nachdem die Administration "
            "sie angenommen hat (sofort bei einer Instanz, deren Rezepte die Administration ohne "
            "Nachfrage übernimmt), und verschwinden, wenn ihre Quelle sie zurückzieht oder die "
            "Verbindung endet; was du hier mit ihnen machst (Favoriten, Notizen, Bewertungen, "
            "Kochverlauf), bleibt hier."
        )
    if f.mail_enabled:
        parts.append(
            "## E-Mail\n\nDie Instanz verschickt Mails über den Mailserver der Administration, "
            "zum Beispiel Betriebsmeldungen an die Administration."
        )
    parts.append(
        "## Deine Daten und das Löschen\n\n"
        "Deine Daten kannst du in deinem Konto herunterladen. Dein Konto kannst du selbst "
        "löschen: Rezepte, die alle Mitglieder sehen"
        + (" oder die öffentlich sind" if f.public_recipes_allowed else "")
        + ", bleiben ohne Besitzer online (als ehemaliges "
        "Mitglied), außer die Instanz lässt dich sie löschen; Haushaltsrezepte gehen an ein "
        "verbleibendes Haushaltsmitglied oder werden gelöscht; private und geteilte Rezepte und "
        "alle Entwürfe werden gelöscht; Zutaten, die du angelegt hast, bleiben ohne Besitzer im "
        "Katalog. Profil, Zugangsdaten, Gesundheitsdaten, Einwilligungen, Bewertungen, Notizen, "
        "Favoriten, Kochverlauf, Wochenplan und Mitgliedschaften werden gelöscht, ebenso deine "
        "Einträge im Sicherheitsprotokoll bis auf einen anonymen Eintrag, dass ein Konto "
        "gelöscht wurde. Löscht die Administration ein Konto, gelten dieselben Regeln. Gelöschte "
        "Daten bleiben wie oben beschrieben in den Sicherungen."
    )
    parts.append(
        "## Deine Rechte\n\n[Wie du die verantwortliche Person erreichst, und die "
        "Aufsichtsbehörde.]"
    )
    return "\n\n".join(parts) + "\n"
