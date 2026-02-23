export const toCsv = (headers: string[], rows: Array<Array<string | number>>) => {
  const escapeValue = (value: string | number) => {
    const text = String(value ?? '');
    if (text.includes(',') || text.includes('"') || text.includes('\n')) {
      return `"${text.replace(/"/g, '""')}"`;
    }
    return text;
  };

  const headerRow = headers.map(escapeValue).join(',');
  const body = rows.map((row) => row.map(escapeValue).join(',')).join('\n');
  return `${headerRow}\n${body}`;
};
