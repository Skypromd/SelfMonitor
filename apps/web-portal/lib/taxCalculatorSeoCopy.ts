/**
 * Public tax calculator SEO copy — meaning-led translations; official UK terms stay in English where standard (HMRC, MTD, NI, Student Loan, Plan 1/2, etc.).
 */

export const TAX_CALC_SEO_LANGS = ['pl', 'ro', 'uk', 'ru', 'es', 'it', 'pt', 'tr', 'bn'] as const;
export type TaxCalcSeoLang = (typeof TAX_CALC_SEO_LANGS)[number];

export type TaxCalculatorPublicCopy = {
  htmlLang: string;
  hreflang: string;
  metaTitle: string;
  metaDescription: string;
  navHome: string;
  h1: string;
  intro: string;
  grossLabel: string;
  expensesLabel: string;
  tradingAllowanceLabel: string;
  studentLoanLabel: string;
  studentLoanNone: string;
  calculate: string;
  calculating: string;
  resultsTitle: string;
  resultAdjustedProfit: string;
  resultPersonalAllowance: string;
  resultIncomeTax: string;
  resultNi: string;
  resultStudentLoan: string;
  resultTotalTaxNi: string;
  resultTakeHome: string;
  resultEffectiveRate: string;
  resultPaymentsOnAccount: string;
  ctaRegister: string;
  langSwitcher: string;
  errors: {
    invalidGross: string;
    network: string;
    requestFailed: (status: number) => string;
  };
};

const EN: TaxCalculatorPublicCopy = {
  htmlLang: 'en-GB',
  hreflang: 'en-GB',
  metaTitle: 'UK Self-Employed Tax Calculator (illustrative) | MyNetTax',
  metaDescription:
    'Free illustrative UK self-employment Income Tax and NI estimate for sole traders. Not professional advice.',
  navHome: '← Home',
  h1: 'UK self-employed tax estimate',
  intro:
    'Enter your annual trading income and expenses. We use the same in-engine self-employment model as the signed-in app (2025/26-style bands). No account required. Figures are illustrative only — not HMRC or professional advice; confirm with gov.uk or an accountant.',
  grossLabel: 'Gross trading income (£/year)',
  expensesLabel: 'Allowable expenses (£/year)',
  tradingAllowanceLabel:
    'Use £1,000 trading allowance (instead of listing expenses below £1,000)',
  studentLoanLabel: 'Student Loan (Plan)',
  studentLoanNone: 'None',
  calculate: 'Calculate',
  calculating: 'Calculating…',
  resultsTitle: 'Results',
  resultAdjustedProfit: 'Adjusted profit:',
  resultPersonalAllowance: 'Personal allowance (after taper):',
  resultIncomeTax: 'Income Tax:',
  resultNi: 'National Insurance (Classes 2+4):',
  resultStudentLoan: 'Student Loan repayment:',
  resultTotalTaxNi: 'Total tax + NI (+ SL):',
  resultTakeHome: 'Illustrative take-home (after tax/NI/SL):',
  resultEffectiveRate: 'Effective rate on gross:',
  resultPaymentsOnAccount: 'Payments on account (each) (Jan / Jul — illustrative):',
  ctaRegister: 'Want automatic MTD-ready figures? Sign up free',
  langSwitcher: 'Other languages',
  errors: {
    invalidGross: 'Enter a valid gross income.',
    network: 'Could not reach the tax service. Is the API gateway running?',
    requestFailed: (status) => `Request failed (${status})`,
  },
};

const PL: TaxCalculatorPublicCopy = {
  htmlLang: 'pl',
  hreflang: 'pl',
  metaTitle: 'Kalkulator podatku dla self-employed w UK (orientacyjnie) | MyNetTax',
  metaDescription:
    'Bezpłatny, orientacyjny szacunek Income Tax i NI (National Insurance) dla działalności na własny rachunek w UK. To nie jest porada zawodowa.',
  navHome: '← Strona główna',
  h1: 'Orientacyjny podatek dla self-employed w UK',
  intro:
    'Wpisz roczny przychód z działalności i koszty uzyskania. Używamy tego samego modelu co w aplikacji po zalogowaniu (pasma w stylu roku podatkowego 2025/26). Bez konta. Kwoty są poglądowe — nie zastępują HMRC ani doradcy; sprawdź na gov.uk lub u księgowego. Oficjalne skróty (Income Tax, NI, Student Loan, MTD) zostają po angielsku, bo tak widać je w korespondencji z UK.',
  grossLabel: 'Przychód z działalności (£/rok, gross trading income)',
  expensesLabel: 'Koszty dopuszczalne (£/rok, allowable expenses)',
  tradingAllowanceLabel:
    'Zastosuj trading allowance £1 000 (zamiast wykazu kosztów poniżej £1 000)',
  studentLoanLabel: 'Student Loan (plan spłaty — jak w UK)',
  studentLoanNone: 'Brak',
  calculate: 'Oblicz',
  calculating: 'Liczenie…',
  resultsTitle: 'Wyniki',
  resultAdjustedProfit: 'Zysk po korektach (adjusted profit):',
  resultPersonalAllowance: 'Personal allowance (po taper):',
  resultIncomeTax: 'Income Tax:',
  resultNi: 'National Insurance (klasy 2+4):',
  resultStudentLoan: 'Spłata Student Loan:',
  resultTotalTaxNi: 'Suma podatku + NI (+ SL):',
  resultTakeHome: 'Szacunkowy netto (po podatku/NI/SL):',
  resultEffectiveRate: 'Efektywna stawka od brutto:',
  resultPaymentsOnAccount: 'Payments on account (stycz/lip — orientacyjnie):',
  ctaRegister: 'Chcesz cyfry gotowe pod MTD? Załóż darmowe konto',
  langSwitcher: 'Inne języki',
  errors: {
    invalidGross: 'Podaj poprawny przychód brutto.',
    network: 'Brak połączenia z serwisem podatkowym. Czy działa API gateway?',
    requestFailed: (status) => `Błąd żądania (${status})`,
  },
};

const RO: TaxCalculatorPublicCopy = {
  htmlLang: 'ro',
  hreflang: 'ro',
  metaTitle: 'Calculator taxe self-employed UK (estimativ) | MyNetTax',
  metaDescription:
    'Estimare gratuită și ilustrativă pentru Income Tax și NI (National Insurance) în UK. Nu este consultanță fiscală.',
  navHome: '← Acasă',
  h1: 'Estimare taxe self-employed în UK',
  intro:
    'Introdu venitul anual din activitate și cheltuielile admise. Folosim același motor ca în aplicația autentificată (benzi în stil 2025/26). Fără cont. Cifrele sunt orientative — nu înlocuiesc HMRC sau un consilier; verifică pe gov.uk. Termenii oficiali UK (Income Tax, NI, Student Loan, MTD) rămân în engleză, ca în corespondența reală.',
  grossLabel: 'Venit brut din activitate (£/an, gross trading income)',
  expensesLabel: 'Cheltuieli admise (£/an, allowable expenses)',
  tradingAllowanceLabel: 'Folosește trading allowance £1 000 (în loc să listezi cheltuieli sub £1 000)',
  studentLoanLabel: 'Student Loan (plan UK)',
  studentLoanNone: 'Fără',
  calculate: 'Calculează',
  calculating: 'Se calculează…',
  resultsTitle: 'Rezultate',
  resultAdjustedProfit: 'Profit ajustat (adjusted profit):',
  resultPersonalAllowance: 'Personal allowance (după taper):',
  resultIncomeTax: 'Income Tax:',
  resultNi: 'National Insurance (clasele 2+4):',
  resultStudentLoan: 'Rambursare Student Loan:',
  resultTotalTaxNi: 'Total taxă + NI (+ SL):',
  resultTakeHome: 'Take-home ilustrativ (după tax/NI/SL):',
  resultEffectiveRate: 'Rată efectivă pe brut:',
  resultPaymentsOnAccount: 'Payments on account (ian/iul — ilustrativ):',
  ctaRegister: 'Vrei cifre pregătite pentru MTD? Înregistrare gratuită',
  langSwitcher: 'Alte limbi',
  errors: {
    invalidGross: 'Introdu un venit brut valid.',
    network: 'Nu s-a putut contacta serviciul fiscal. Rulează API gateway?',
    requestFailed: (status) => `Cerere eșuată (${status})`,
  },
};

const UK_UA: TaxCalculatorPublicCopy = {
  htmlLang: 'uk',
  hreflang: 'uk',
  metaTitle: 'Калькулятор податку self-employed у UK (орієнтовно) | MyNetTax',
  metaDescription:
    'Безкоштовна орієнтовна оцінка Income Tax та NI для підприємця у UK. Не є професійною консультацією.',
  navHome: '← Головна',
  h1: 'Орієнтовний податок self-employed у UK',
  intro:
    'Введіть річний торговий дохід і дозволені витрати. Використовуємо той самий рушій, що й у застосунку після входу (смуги у стилі 2025/26). Без акаунта. Суми ілюстративні — не замінюють HMRC чи бухгалтера; перевіряйте на gov.uk. Офіційні терміни UK (Income Tax, NI, Student Loan, MTD) лишаємо англійською, як у листах від податкової.',
  grossLabel: 'Валовий дохід від діяльності (£/рік, gross trading income)',
  expensesLabel: 'Дозволені витрати (£/рік, allowable expenses)',
  tradingAllowanceLabel:
    'Застосувати trading allowance £1 000 (замість переліку витрат нижче £1 000)',
  studentLoanLabel: 'Student Loan (план UK)',
  studentLoanNone: 'Немає',
  calculate: 'Обчислити',
  calculating: 'Обчислення…',
  resultsTitle: 'Результати',
  resultAdjustedProfit: 'Скоригований прибуток (adjusted profit):',
  resultPersonalAllowance: 'Personal allowance (після taper):',
  resultIncomeTax: 'Income Tax:',
  resultNi: 'National Insurance (класи 2+4):',
  resultStudentLoan: 'Платіж Student Loan:',
  resultTotalTaxNi: 'Усього податок + NI (+ SL):',
  resultTakeHome: 'Орієнтовний take-home (після tax/NI/SL):',
  resultEffectiveRate: 'Ефективна ставка до брутто:',
  resultPaymentsOnAccount: 'Payments on account (січ/лип — ілюстративно):',
  ctaRegister: 'Потрібні цифри під MTD? Зареєструйтесь безкоштовно',
  langSwitcher: 'Інші мови',
  errors: {
    invalidGross: 'Введіть коректний валовий дохід.',
    network: 'Не вдалося звернутися до податкового сервісу. Запущено API gateway?',
    requestFailed: (status) => `Помилка запиту (${status})`,
  },
};

const RU: TaxCalculatorPublicCopy = {
  htmlLang: 'ru',
  hreflang: 'ru',
  metaTitle: 'Калькулятор налога self-employed в UK (оценочно) | MyNetTax',
  metaDescription:
    'Бесплатная оценка Income Tax и NI для самозанятого в UK. Не профессиональная налоговая консультация.',
  navHome: '← Главная',
  h1: 'Оценка налога self-employed в UK',
  intro:
    'Введите годовой торговый доход и допустимые расходы. Тот же движок, что в приложении после входа (диапазоны в духе 2025/26). Без аккаунта. Суммы иллюстративны — не заменяют HMRC или бухгалтера; сверяйтесь с gov.uk. Официальные UK-термины (Income Tax, NI, Student Loan, MTD) оставляем на английском, как в реальных письмах.',
  grossLabel: 'Валовый доход от деятельности (£/год, gross trading income)',
  expensesLabel: 'Допустимые расходы (£/год, allowable expenses)',
  tradingAllowanceLabel:
    'Использовать trading allowance £1 000 (вместо перечисления расходов ниже £1 000)',
  studentLoanLabel: 'Student Loan (план UK)',
  studentLoanNone: 'Нет',
  calculate: 'Рассчитать',
  calculating: 'Считаем…',
  resultsTitle: 'Результаты',
  resultAdjustedProfit: 'Скорректированная прибыль (adjusted profit):',
  resultPersonalAllowance: 'Personal allowance (после taper):',
  resultIncomeTax: 'Income Tax:',
  resultNi: 'National Insurance (классы 2+4):',
  resultStudentLoan: 'Платёж Student Loan:',
  resultTotalTaxNi: 'Итого налог + NI (+ SL):',
  resultTakeHome: 'Ориентировочный take-home (после tax/NI/SL):',
  resultEffectiveRate: 'Эффективная ставка к брутто:',
  resultPaymentsOnAccount: 'Payments on account (янв/июл — оценочно):',
  ctaRegister: 'Нужны цифры под MTD? Бесплатная регистрация',
  langSwitcher: 'Другие языки',
  errors: {
    invalidGross: 'Введите корректный валовый доход.',
    network: 'Не удалось связаться с налоговым сервисом. Запущен ли API gateway?',
    requestFailed: (status) => `Ошибка запроса (${status})`,
  },
};

const ES: TaxCalculatorPublicCopy = {
  htmlLang: 'es',
  hreflang: 'es',
  metaTitle: 'Calculadora fiscal self-employed en el Reino Unido (ilustrativa) | MyNetTax',
  metaDescription:
    'Estimación gratuita e ilustrativa de Income Tax y NI para autónomos en el Reino Unido. No es asesoramiento profesional.',
  navHome: '← Inicio',
  h1: 'Estimación fiscal self-employed en UK',
  intro:
    'Introduce tus ingresos anuales por actividad y los gastos deducibles. Usamos el mismo motor que la app con sesión iniciada (bandas al estilo 2025/26). Sin cuenta. Las cifras son ilustrativas: no sustituyen a HMRC ni a un asesor; consulta gov.uk. Los términos oficiales UK (Income Tax, NI, Student Loan, MTD) se mantienen en inglés, como en la correspondencia real.',
  grossLabel: 'Ingreso bruto de la actividad (£/año, gross trading income)',
  expensesLabel: 'Gastos deducibles (£/año, allowable expenses)',
  tradingAllowanceLabel:
    'Usar trading allowance de £1 000 (en lugar de detallar gastos por debajo de £1 000)',
  studentLoanLabel: 'Student Loan (plan UK)',
  studentLoanNone: 'Ninguno',
  calculate: 'Calcular',
  calculating: 'Calculando…',
  resultsTitle: 'Resultados',
  resultAdjustedProfit: 'Beneficio ajustado (adjusted profit):',
  resultPersonalAllowance: 'Personal allowance (tras taper):',
  resultIncomeTax: 'Income Tax:',
  resultNi: 'National Insurance (clases 2+4):',
  resultStudentLoan: 'Pago Student Loan:',
  resultTotalTaxNi: 'Total impuesto + NI (+ SL):',
  resultTakeHome: 'Take-home ilustrativo (tras tax/NI/SL):',
  resultEffectiveRate: 'Tipo efectivo sobre el bruto:',
  resultPaymentsOnAccount: 'Payments on account (ene/jul — ilustrativo):',
  ctaRegister: '¿Quieres cifras listas para MTD? Regístrate gratis',
  langSwitcher: 'Otros idiomas',
  errors: {
    invalidGross: 'Introduce un ingreso bruto válido.',
    network: 'No se pudo contactar con el servicio fiscal. ¿Está el API gateway en marcha?',
    requestFailed: (status) => `Error en la petición (${status})`,
  },
};

const IT: TaxCalculatorPublicCopy = {
  htmlLang: 'it',
  hreflang: 'it',
  metaTitle: 'Calcolo tasse self-employed UK (illustrativo) | MyNetTax',
  metaDescription:
    'Stima gratuita e illustrativa di Income Tax e NI per lavoratori autonomi nel Regno Unito. Non è consulenza professionale.',
  navHome: '← Home',
  h1: 'Stima tasse self-employed nel UK',
  intro:
    'Inserisci il reddito annuale da attività e le spese ammissibili. Usiamo lo stesso motore dell’app con accesso (fasce in stile 2025/26). Senza account. Le cifre sono illustrative — non sostituiscono HMRC o un consulente; verifica su gov.uk. I termini ufficiali UK (Income Tax, NI, Student Loan, MTD) restano in inglese come nella prassi.',
  grossLabel: 'Reddito lordo da attività (£/anno, gross trading income)',
  expensesLabel: 'Spese ammissibili (£/anno, allowable expenses)',
  tradingAllowanceLabel:
    'Usa trading allowance £1 000 (invece di elencare spese sotto £1 000)',
  studentLoanLabel: 'Student Loan (piano UK)',
  studentLoanNone: 'Nessuno',
  calculate: 'Calcola',
  calculating: 'Calcolo…',
  resultsTitle: 'Risultati',
  resultAdjustedProfit: 'Utile rettificato (adjusted profit):',
  resultPersonalAllowance: 'Personal allowance (dopo taper):',
  resultIncomeTax: 'Income Tax:',
  resultNi: 'National Insurance (classi 2+4):',
  resultStudentLoan: 'Rimborso Student Loan:',
  resultTotalTaxNi: 'Totale imposta + NI (+ SL):',
  resultTakeHome: 'Take-home illustrativo (dopo tax/NI/SL):',
  resultEffectiveRate: 'Aliquota effettiva sul lordo:',
  resultPaymentsOnAccount: 'Payments on account (gen/lug — illustrativo):',
  ctaRegister: 'Vuoi cifre pronte per MTD? Registrati gratis',
  langSwitcher: 'Altre lingue',
  errors: {
    invalidGross: 'Inserisci un reddito lordo valido.',
    network: 'Impossibile contattare il servizio fiscale. API gateway attivo?',
    requestFailed: (status) => `Richiesta fallita (${status})`,
  },
};

const PT: TaxCalculatorPublicCopy = {
  htmlLang: 'pt',
  hreflang: 'pt',
  metaTitle: 'Calculadora de impostos self-employed no Reino Unido (ilustrativa) | MyNetTax',
  metaDescription:
    'Estimativa gratuita e ilustrativa de Income Tax e NI para trabalhadores por conta própria no UK. Não é aconselhamento profissional.',
  navHome: '← Início',
  h1: 'Estimativa de impostos self-employed no UK',
  intro:
    'Introduza o rendimento anual da atividade e as despesas admissíveis. Usamos o mesmo motor da app autenticada (faixas ao estilo 2025/26). Sem conta. Os valores são ilustrativos — não substituem a HMRC nem um contabilista; confira em gov.uk. Os termos oficiais UK (Income Tax, NI, Student Loan, MTD) mantêm-se em inglês.',
  grossLabel: 'Rendimento bruto da atividade (£/ano, gross trading income)',
  expensesLabel: 'Despesas admissíveis (£/ano, allowable expenses)',
  tradingAllowanceLabel:
    'Usar trading allowance de £1 000 (em vez de listar despesas abaixo de £1 000)',
  studentLoanLabel: 'Student Loan (plano UK)',
  studentLoanNone: 'Nenhum',
  calculate: 'Calcular',
  calculating: 'A calcular…',
  resultsTitle: 'Resultados',
  resultAdjustedProfit: 'Lucro ajustado (adjusted profit):',
  resultPersonalAllowance: 'Personal allowance (após taper):',
  resultIncomeTax: 'Income Tax:',
  resultNi: 'National Insurance (classes 2+4):',
  resultStudentLoan: 'Pagamento Student Loan:',
  resultTotalTaxNi: 'Total imposto + NI (+ SL):',
  resultTakeHome: 'Take-home ilustrativo (após tax/NI/SL):',
  resultEffectiveRate: 'Taxa efetiva sobre o bruto:',
  resultPaymentsOnAccount: 'Payments on account (jan/jul — ilustrativo):',
  ctaRegister: 'Quer números prontos para MTD? Registe-se grátis',
  langSwitcher: 'Outros idiomas',
  errors: {
    invalidGross: 'Introduza um rendimento bruto válido.',
    network: 'Não foi possível contactar o serviço fiscal. O API gateway está a correr?',
    requestFailed: (status) => `Pedido falhou (${status})`,
  },
};

const TR: TaxCalculatorPublicCopy = {
  htmlLang: 'tr',
  hreflang: 'tr',
  metaTitle: 'UK self-employed vergi hesaplayıcı (özet) | MyNetTax',
  metaDescription:
    'UK’de serbest çalışanlar için ücretsiz, örnek Income Tax ve NI tahmini. Profesyonel tavsiye değildir.',
  navHome: '← Ana sayfa',
  h1: 'UK self-employed vergi tahmini',
  intro:
    'Yıllık ticari brüt gelirinizi ve kabul edilebilir giderlerinizi girin. Oturum açılmış uygulamayla aynı motoru kullanıyoruz (2025/26 tarzı bantlar). Hesap gerekmez. Rakamlar örnektir — HMRC veya mali müşavirin yerini tutmaz; gov.uk üzerinden doğrulayın. Resmi UK terimleri (Income Tax, NI, Student Loan, MTD) İngilizce bırakılmıştır.',
  grossLabel: 'Ticari brüt gelir (£/yıl, gross trading income)',
  expensesLabel: 'Kabul edilebilir giderler (£/yıl, allowable expenses)',
  tradingAllowanceLabel:
    '£1 000 trading allowance kullan (£1 000 altı giderleri listelemek yerine)',
  studentLoanLabel: 'Student Loan (UK planı)',
  studentLoanNone: 'Yok',
  calculate: 'Hesapla',
  calculating: 'Hesaplanıyor…',
  resultsTitle: 'Sonuçlar',
  resultAdjustedProfit: 'Düzeltilmiş kâr (adjusted profit):',
  resultPersonalAllowance: 'Personal allowance (taper sonrası):',
  resultIncomeTax: 'Income Tax:',
  resultNi: 'National Insurance (2+4. sınıflar):',
  resultStudentLoan: 'Student Loan geri ödemesi:',
  resultTotalTaxNi: 'Toplam vergi + NI (+ SL):',
  resultTakeHome: 'Örnek take-home (tax/NI/SL sonrası):',
  resultEffectiveRate: 'Brüte göre efektif oran:',
  resultPaymentsOnAccount: 'Payments on account (Oca/Tem — örnek):',
  ctaRegister: 'MTD için hazır rakamlar mı istiyorsunuz? Ücretsiz kayıt',
  langSwitcher: 'Diğer diller',
  errors: {
    invalidGross: 'Geçerli bir brüt gelir girin.',
    network: 'Vergi hizmetine ulaşılamadı. API gateway çalışıyor mu?',
    requestFailed: (status) => `İstek başarısız (${status})`,
  },
};

const BN: TaxCalculatorPublicCopy = {
  htmlLang: 'bn',
  hreflang: 'bn',
  metaTitle: 'ইউকে সেলফ-এমপ্লয়েড কর ক্যালকুলেটর (নমুনা) | MyNetTax',
  metaDescription:
    'ইউকেতে সেলফ-এমপ্লয়েডদের জন্য বিনামূল্যে নমুনা Income Tax ও NI হিসাব। পেশাদার পরামর্শ নয়।',
  navHome: '← হোম',
  h1: 'ইউকে সেলফ-এমপ্লয়েড করের আনুমানিক হিসাব',
  intro:
    'বার্ষিক ট্রেডিং আয় ও অনুমোদিত ব্যয় লিখুন। লগইন অ্যাপের মতো একই ইঞ্জিন ব্যবহার করি (২০২৫/২৬-স্টাইল ব্যান্ড)। অ্যাকাউন্ট লাগবে না। সংখ্যা নমুনামাত্র — HMRC বা পেশাদার হিসাববিদের বিকল্প নয়; gov.uk দেখুন। офিসিয়াল UK পরিভাষা — Income Tax, NI, Student Loan, MTD — ইংরেজিতে রাখা হয়েছে, যেমন চিঠিতে থাকে।',
  grossLabel: 'মোট ট্রেডিং আয় (£/বছর, gross trading income)',
  expensesLabel: 'অনুমোদিত ব্যয় (£/বছর, allowable expenses)',
  tradingAllowanceLabel:
    '£১,০০০ trading allowance ব্যবহার করুন (£১,০০০-এর নিচে ব্যয়ের তালিকার বদলে)',
  studentLoanLabel: 'Student Loan (UK পরিকল্পনা)',
  studentLoanNone: 'নেই',
  calculate: 'হিসাব করুন',
  calculating: 'হিসাব হচ্ছে…',
  resultsTitle: 'ফলাফল',
  resultAdjustedProfit: 'সংশোধিত মুনাফা (adjusted profit):',
  resultPersonalAllowance: 'Personal allowance (taper-এর পর):',
  resultIncomeTax: 'Income Tax:',
  resultNi: 'National Insurance (ক্লাস ২+৪):',
  resultStudentLoan: 'Student Loan পরিশোধ:',
  resultTotalTaxNi: 'মোট কর + NI (+ SL):',
  resultTakeHome: 'নমুনা take-home (tax/NI/SL-এর পর):',
  resultEffectiveRate: 'মোট উপর কার্যকর হার:',
  resultPaymentsOnAccount: 'Payments on account (জানু/জুল — নমুনা):',
  ctaRegister: 'MTD-র জন্য প্রস্তুত সংখ্যা চান? বিনামূল্যে সাইন আপ',
  langSwitcher: 'অন্যান্য ভাষা',
  errors: {
    invalidGross: 'সঠিক মোট আয় লিখুন।',
    network: 'ট্যাক্স সেবায় যোগাযোগ করা যায়নি। API gateway চালু আছে কি?',
    requestFailed: (status) => `অনুরোধ ব্যর্থ (${status})`,
  },
};

const BY_LANG: Record<TaxCalcSeoLang, TaxCalculatorPublicCopy> = {
  pl: PL,
  ro: RO,
  uk: UK_UA,
  ru: RU,
  es: ES,
  it: IT,
  pt: PT,
  tr: TR,
  bn: BN,
};

export function getTaxCalcSeoLang(param: string): TaxCalcSeoLang | null {
  const p = param.toLowerCase();
  return (TAX_CALC_SEO_LANGS as readonly string[]).includes(p) ? (p as TaxCalcSeoLang) : null;
}

export function getTaxCalculatorCopyForSeoLang(lang: TaxCalcSeoLang): TaxCalculatorPublicCopy {
  return BY_LANG[lang];
}

export { EN as TAX_CALCULATOR_COPY_EN };
