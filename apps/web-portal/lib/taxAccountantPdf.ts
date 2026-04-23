import type { jsPDF } from 'jspdf';

type JsPdfWithAutoTable = jsPDF & { lastAutoTable: { finalY: number } };

export type AccountantPdfMtd = {
  reporting_required: boolean;
  next_deadline: string | null;
  qualifying_income_estimate?: number;
  quarterly_updates: { quarter: string; due_date: string; status: string }[];
};

export type AccountantPdfCalc = {
  total_income: number;
  total_expenses: number;
  taxable_profit: number;
  personal_allowance_used: number;
  pa_taper_reduction: number;
  taxable_amount_after_allowance: number;
  basic_rate_tax: number;
  higher_rate_tax: number;
  additional_rate_tax: number;
  estimated_income_tax_due: number;
  estimated_class2_nic_due: number;
  estimated_class4_nic_due: number;
  estimated_tax_due: number;
  payment_on_account_jan: number;
  payment_on_account_jul: number;
  cis_tax_credit_verified_gbp?: number;
  cis_tax_credit_self_attested_gbp?: number;
  mtd_obligation: AccountantPdfMtd;
  summary_by_category: { category: string; total_amount: number; taxable_amount: number }[];
};

function gbp(n: number): string {
  return n.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export async function downloadAccountantTaxSummaryPdf(params: {
  yearLabel: string;
  periodStart: string;
  periodEnd: string;
  calc: AccountantPdfCalc;
  filename: string;
}): Promise<void> {
  const [{ jsPDF }, { default: autoTable }] = await Promise.all([
    import('jspdf'),
    import('jspdf-autotable'),
  ]);

  const doc = new jsPDF();
  const { yearLabel, periodStart, periodEnd, calc, filename } = params;
  let y = 14;

  doc.setFontSize(16);
  doc.text('Tax summary (accountant pack)', 14, y);
  y += 8;
  doc.setFontSize(10);
  doc.setTextColor(80);
  doc.text(`Tax year ${yearLabel}  ·  ${periodStart} to ${periodEnd}`, 14, y);
  y += 6;
  const disclaimerLines = doc.splitTextToSize(
    'Self-employed / SA103-style figures from SelfMonitor. Not an HMRC submission. Review before use.',
    182,
  );
  doc.text(disclaimerLines, 14, y);
  y += disclaimerLines.length * 5 + 8;
  doc.setTextColor(0);

  const summaryBody: string[][] = [
    ['Total income', gbp(calc.total_income)],
    ['Total expenses', gbp(calc.total_expenses)],
    ['Taxable profit', gbp(calc.taxable_profit)],
    ['Personal allowance used', gbp(calc.personal_allowance_used)],
    ['PA taper reduction', gbp(calc.pa_taper_reduction)],
    ['Taxable after allowance', gbp(calc.taxable_amount_after_allowance)],
    ['Income tax (basic)', gbp(calc.basic_rate_tax)],
    ['Income tax (higher)', gbp(calc.higher_rate_tax)],
    ['Income tax (additional)', gbp(calc.additional_rate_tax)],
    ['Income tax due', gbp(calc.estimated_income_tax_due)],
    ['Class 2 NIC', gbp(calc.estimated_class2_nic_due)],
    ['Class 4 NIC', gbp(calc.estimated_class4_nic_due)],
    ['Total tax + NIC due', gbp(calc.estimated_tax_due)],
    ['Payment on account (Jan)', gbp(calc.payment_on_account_jan)],
    ['Payment on account (Jul)', gbp(calc.payment_on_account_jul)],
    ['CIS credit (verified)', gbp(calc.cis_tax_credit_verified_gbp ?? 0)],
    ['CIS credit (self-attested)', gbp(calc.cis_tax_credit_self_attested_gbp ?? 0)],
    ['MTD reporting required', calc.mtd_obligation.reporting_required ? 'Yes' : 'No'],
    ['MTD qualifying income (est.)', gbp(calc.mtd_obligation.qualifying_income_estimate ?? 0)],
    ['MTD next deadline', calc.mtd_obligation.next_deadline ?? '—'],
  ];

  autoTable(doc, {
    startY: y,
    head: [['Item', 'GBP']],
    body: summaryBody,
    styles: { fontSize: 9 },
    headStyles: { fillColor: [41, 128, 185] },
    margin: { left: 14, right: 14 },
  });

  let after = (doc as JsPdfWithAutoTable).lastAutoTable.finalY + 10;

  const catRows = calc.summary_by_category.map((r) => [
    r.category,
    gbp(r.total_amount),
    gbp(r.taxable_amount),
  ]);

  autoTable(doc, {
    startY: after,
    head: [['Category', 'Total', 'Taxable']],
    body: catRows,
    styles: { fontSize: 8 },
    headStyles: { fillColor: [52, 152, 219] },
    margin: { left: 14, right: 14 },
  });

  after = (doc as JsPdfWithAutoTable).lastAutoTable.finalY + 8;

  if (calc.mtd_obligation.quarterly_updates?.length) {
    const qRows = calc.mtd_obligation.quarterly_updates.map((q) => [q.quarter, q.due_date, q.status]);
    autoTable(doc, {
      startY: after,
      head: [['MTD quarter', 'Due', 'Status']],
      body: qRows,
      styles: { fontSize: 8 },
      headStyles: { fillColor: [39, 174, 96] },
      margin: { left: 14, right: 14 },
    });
  }

  doc.save(filename);
}
