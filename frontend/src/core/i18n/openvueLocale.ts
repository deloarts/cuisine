/**
 * The texts OpenVue's own components show or announce to screen readers
 * (empty lists, result counts, dialog close buttons), per UI language.
 * OpenVue only knows English, so the German set is ours; `applyOpenVueLocale`
 * swaps them whenever the UI language changes. The date format and the
 * week start are not here; `main.ts` sets them when it installs OpenVue.
 */
import type { AppLocale } from '@/core/i18n'

interface OpenVueTexts {
  [key: string]: string | string[] | Record<string, string>
  aria: Record<string, string>
}

const enGB: OpenVueTexts = {
  accept: 'Yes',
  reject: 'No',
  choose: 'Choose',
  upload: 'Upload',
  cancel: 'Cancel',
  clear: 'Clear',
  apply: 'Apply',
  today: 'Today',
  weekHeader: 'Wk',
  dayNames: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
  dayNamesShort: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
  dayNamesMin: ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'],
  monthNames: [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ],
  monthNamesShort: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  chooseYear: 'Choose Year',
  chooseMonth: 'Choose Month',
  chooseDate: 'Choose Date',
  prevYear: 'Previous Year',
  nextYear: 'Next Year',
  prevMonth: 'Previous Month',
  nextMonth: 'Next Month',
  weak: 'Weak',
  medium: 'Medium',
  strong: 'Strong',
  passwordPrompt: 'Enter a password',
  emptyFilterMessage: 'No results found',
  searchMessage: '{0} results are available',
  selectionMessage: '{0} items selected',
  emptySelectionMessage: 'No selected item',
  emptySearchMessage: 'No results found',
  fileChosenMessage: '{0} files',
  noFileChosenMessage: 'No file chosen',
  emptyMessage: 'No available options',
  aria: {
    close: 'Close',
    showPassword: 'Show Password',
    hidePassword: 'Hide Password',
    previous: 'Previous',
    next: 'Next',
    navigation: 'Navigation',
    selectAll: 'All items selected',
    unselectAll: 'All items unselected',
    star: '1 star',
    stars: '{star} stars',
    pageLabel: 'Page {page}',
    firstPageLabel: 'First Page',
    lastPageLabel: 'Last Page',
    nextPageLabel: 'Next Page',
    prevPageLabel: 'Previous Page',
    rowsPerPageLabel: 'Rows per page',
    zoomIn: 'Zoom In',
    zoomOut: 'Zoom Out',
    listLabel: 'Option List',
  },
}

const deAT: OpenVueTexts = {
  accept: 'Ja',
  reject: 'Nein',
  choose: 'Auswählen',
  upload: 'Hochladen',
  cancel: 'Abbrechen',
  clear: 'Leeren',
  apply: 'Übernehmen',
  today: 'Heute',
  weekHeader: 'KW',
  dayNames: ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'],
  dayNamesShort: ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'],
  dayNamesMin: ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'],
  monthNames: [
    'Jänner', 'Februar', 'März', 'April', 'Mai', 'Juni',
    'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
  ],
  monthNamesShort: ['Jän', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'],
  chooseYear: 'Jahr wählen',
  chooseMonth: 'Monat wählen',
  chooseDate: 'Datum wählen',
  prevYear: 'Voriges Jahr',
  nextYear: 'Nächstes Jahr',
  prevMonth: 'Voriger Monat',
  nextMonth: 'Nächster Monat',
  weak: 'Schwach',
  medium: 'Mittel',
  strong: 'Stark',
  passwordPrompt: 'Gib ein Passwort ein',
  emptyFilterMessage: 'Nichts gefunden',
  searchMessage: '{0} Ergebnisse verfügbar',
  selectionMessage: '{0} ausgewählt',
  emptySelectionMessage: 'Nichts ausgewählt',
  emptySearchMessage: 'Nichts gefunden',
  fileChosenMessage: '{0} Dateien',
  noFileChosenMessage: 'Keine Datei gewählt',
  emptyMessage: 'Keine Optionen verfügbar',
  aria: {
    close: 'Schließen',
    showPassword: 'Passwort zeigen',
    hidePassword: 'Passwort verbergen',
    previous: 'Zurück',
    next: 'Weiter',
    navigation: 'Navigation',
    selectAll: 'Alle ausgewählt',
    unselectAll: 'Keine ausgewählt',
    star: '1 Stern',
    stars: '{star} Sterne',
    pageLabel: 'Seite {page}',
    firstPageLabel: 'Erste Seite',
    lastPageLabel: 'Letzte Seite',
    nextPageLabel: 'Nächste Seite',
    prevPageLabel: 'Vorige Seite',
    rowsPerPageLabel: 'Zeilen pro Seite',
    zoomIn: 'Vergrößern',
    zoomOut: 'Verkleinern',
    listLabel: 'Auswahlliste',
  },
}

const TEXTS: Record<AppLocale, OpenVueTexts> = { enGB, deAT }

interface OpenVueConfig {
  locale?: object
}

/** Merges the texts of `locale` into OpenVue's live locale, keeping what
 * the texts do not name (date format, week start, filter labels). */
export function applyOpenVueLocale(config: OpenVueConfig, locale: AppLocale): void {
  const texts = TEXTS[locale]
  const current = (config.locale ?? {}) as { aria?: Record<string, string> }
  config.locale = { ...current, ...texts, aria: { ...current.aria, ...texts.aria } }
}
